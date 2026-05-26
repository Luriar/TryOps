# Data Pipeline — 데이터 흐름 5단계 상세

> 본 문서는 `architecture.md` 섹션 3 데이터 흐름의 상세 자료다. 각 단계의 스키마·처리 로직·에러 핸들링·재처리 전략 정밀 정의.

---

## 0. 본 파이프라인의 설계 원칙

1. **데이터 90% 줄이기를 가장 일찍** — 매장 게이트웨이에서 raw → 1분 집계로 줄임
2. **모든 단계 idempotent** — 재처리 시 중복 없음
3. **단계별 격리** — 한 단계 장애가 다른 단계로 전파 안 됨
4. **장애 시 7일 복구 가능** — 매장 게이트웨이 + S3 raw 보존 정책
5. **법적 준수 우선** — 개인 식별 데이터는 매장에서 제거, AWS 전송 안 함

---

## 1. Stage 1: 매장 측 수집 (실시간)

### 1.1 데이터 소스 3종

**소스 A: ESP32-S3 CSI 노드**

```python
# ESP32-S3 펌웨어 (C++/Arduino)
# 매장 게이트웨이로 MQTT 송신
{
  "node_id": "node_fitting_3_a",
  "fitting_room_id": 3,
  "timestamp_ms": 1747900800123,
  "csi_data": [
    {"subcarrier": 0, "amplitude": 0.732, "phase": 1.23},
    ...
    {"subcarrier": 63, "amplitude": 0.451, "phase": -0.87}
  ],
  "rssi": -42,
  "channel": 6
}
```

데이터량: 노드당 초당 약 100 패킷 × 1KB = **100KB/초**.

**소스 B: RFID 솔루션사 Webhook**

```python
# 셀메이트·idro 등에서 webhook 수신
POST /api/v1/rfid_event
{
  "event_type": "enter" | "exit",
  "fitting_room_id": 3,
  "sku_id": "SKU_LEGGINGS_M_BLACK",
  "timestamp": "2026-05-22T15:23:45.123+09:00",
  "metadata": {
    "category": "leggings",
    "size": "M",
    "color": "black",
    "season": "2026SS"
  }
}
```

**소스 C: POS API 폴링**

```python
# 매장 POS (토스플레이스 등)에 1분 간격 폴링
GET /api/v1/transactions?since=<timestamp>
[
  {
    "transaction_id": "TXN_20260522_1834",
    "timestamp": "2026-05-22T15:42:18+09:00",
    "items": [
      {"sku_id": "SKU_LEGGINGS_L_BLACK", "quantity": 1, "price": 89000}
    ],
    "payment_method": "card"
    // 카드번호·전화번호 등 개인정보 제거 후 수신
  }
]
```

### 1.2 매장 게이트웨이 SW 스택

```yaml
OS: Ubuntu 22.04 ARM64 (Raspberry Pi 4B 8GB)
Runtime: Python 3.11
주요 라이브러리:
  - paho-mqtt (MQTT broker 통신)
  - polars (집계 처리)
  - sqlite3 (로컬 버퍼)
  - aiohttp (POS API 폴링)
  - apscheduler (cron-like)
Database: SQLite (로컬), 30일 보존
서비스 관리: systemd
모니터링: Prometheus node_exporter (선택)
```

### 1.3 매장 게이트웨이 데이터 흐름

```
ESP32-S3 노드 6개 → Mosquitto MQTT (매장 게이트웨이 내부)
  ↓
Python collector (asyncio)
  - MQTT subscribe: csi/+
  - 5초 윈도우 임시 버퍼 (메모리)
  ↓
SQLite "raw_csi" 테이블 적재 (1초 단위 배치)
  - 7일 후 자동 삭제 (cron)
```

```
RFID webhook → Flask 엔드포인트 → SQLite "rfid_events"
POS API 폴링 (1분) → SQLite "pos_events"
```

### 1.4 SQLite 스키마

```sql
-- raw CSI (7일 보존)
CREATE TABLE raw_csi (
  id INTEGER PRIMARY KEY,
  node_id TEXT,
  fitting_room_id INTEGER,
  timestamp_ms INTEGER,
  rssi INTEGER,
  csi_blob BLOB,  -- 64 subcarrier × (amp + phase) 압축
  INDEX(timestamp_ms)
);

-- RFID 이벤트 (30일 보존)
CREATE TABLE rfid_events (
  id INTEGER PRIMARY KEY,
  event_type TEXT,
  fitting_room_id INTEGER,
  sku_id TEXT,
  timestamp_ms INTEGER,
  metadata JSON,
  INDEX(timestamp_ms, fitting_room_id)
);

-- POS 이벤트 (30일 보존)
CREATE TABLE pos_events (
  id INTEGER PRIMARY KEY,
  transaction_id TEXT UNIQUE,
  timestamp_ms INTEGER,
  items JSON,
  payment_method TEXT,
  INDEX(timestamp_ms)
);

-- 1분 집계 (30일 보존)
CREATE TABLE csi_aggregates (
  id INTEGER PRIMARY KEY,
  fitting_room_id INTEGER,
  window_start_ms INTEGER,
  window_end_ms INTEGER,
  activity_score REAL,
  occupancy_estimate INTEGER,
  movement_pattern TEXT,
  INDEX(window_start_ms, fitting_room_id)
);

-- AWS 전송 큐 (성공 시 삭제)
CREATE TABLE aws_send_queue (
  id INTEGER PRIMARY KEY,
  batch_data JSON,
  created_at_ms INTEGER,
  attempts INTEGER DEFAULT 0,
  last_error TEXT
);
```

### 1.5 에러 핸들링

| 장애 | 대응 |
|---|---|
| ESP32-S3 노드 1개 다운 | 다른 노드 데이터로 매장 운영 지속, 노드 24시간+ 다운 시 알람 |
| RFID webhook 미수신 | 매장 게이트웨이가 RFID 솔루션사 API 폴링 (5분 간격) 백업 |
| POS API 다운 | SQLite에 빈 데이터, Joint Signal 5종 중 hesitation·assistance·companion 계산 |
| 매장 인터넷 다운 | SQLite 7일 버퍼, 복구 시 순서대로 AWS 전송 |
| Mosquitto MQTT 다운 | systemd 자동 재시작, 30초 이상 다운 시 알람 |
| 매장 게이트웨이 다운 | UPS 30분 (정전), 30분+ 시 매장 매니저 알람 |

### 1.6 ESP32-S3 CSI의 실측 한계 (비판 3 해소)

ESP32-S3 CSI 기반 인체 감지의 실제 한계 명시. 본 설계가 검증되지 않은 가정 위에 있다는 솔직한 인식.

**🟢 검증된 사실** (espressif/esp-csi GitHub):
- ESP32-S3가 CSI 추출 지원 (공식 라이브러리)
- 인체 동작 감지 사례 다수 (espressif esp-radar 컴포넌트)
- 채널 6 (2.4GHz) 신호 강도 변동으로 점유 추정 가능

**🟡 글로벌 사례**:
- Hackster.io 2026.01: *"$5 마이크로컨트롤러로 인체 감지 시도, 알고리즘은 작동하지만 finicky & power-hungry. 라디오 모듈 대체 어려움"*
- ESP32-CSI Tool (steven mhernandez): 학술 연구 도구, 매장 실측 사례 0건

**🔴 매장 환경 한계 (검증 0건)**:
- 매장 WiFi 환경의 노이즈 (다른 손님 폰·매장 라우터·블루투스)
- 6개 노드 동시 운영 시 매장 WiFi 부하 → ESP32 자체 패킷 손실
- 매장 환경 30°C+ 시 ESP32 throttling
- CSI 정확도가 *"실제 매장에서 50~70%"* 수준 가능성

**대응**:
- PoC Week 1에 매장 1개 실설치 후 7일 데이터 수집
- ESP32-S3 노드 위치 캘리브레이션 (피팅룸당 1~2개 시작 → 필요 시 증설)
- 정확도 70% 미만 시 추가 노드 또는 다른 센서 (mmWave 등) 검토

🔴 **시스템 도입 결정 시 PoC 결과 의존도 매우 큼**. 본 설계는 ESP32-CSI가 *"매장 환경에서 80%+ 정확도"* 라는 가정 위에 있고, 그 가정이 흔들리면 매장당 노드 수·하드웨어 선택 전체 재설계 필요.

### 1.7 매장 게이트웨이 HW 선택 — Raspberry Pi vs Industrial-grade (새 비판 1 해소)

본 v1이 Raspberry Pi 4B 8GB 선택. 그러나 매장 24/7 운영의 신뢰성 측면에서 industrial-grade 게이트웨이와 비교 필요.

| 항목 | Raspberry Pi 4B 8GB | Advantech ARK-1124H | Cisco IR1101 |
|---|---|---|---|
| 가격 | 약 16만원 | 약 150~200만원 | 약 200~300만원 |
| SD 카드 수명 | 2~3년 (잦은 쓰기) | eMMC 또는 SSD (10년+) | eMMC (5년+) |
| 발열 한계 | 60°C+ 시 throttling | -20~60°C 동작 | -25~60°C 동작 |
| 신뢰성 (MTBF) | 약 5만 시간 | 약 25만 시간 | 약 50만 시간 |
| 매장 매니저 인식 | *"이거 라즈베리파이?"* 불안 | 산업용 외관 신뢰 | 산업용 외관 신뢰 |
| 유지보수 | 매년 SD 카드 교체 | 5년+ 무관리 | 5년+ 무관리 |
| 펌웨어 업데이트 | OTA (자체 구현) | OTA (자체 구현) | Cisco IOS 표준 |

**Phase별 선택 권장**:

```yaml
Phase 1 (PoC 매장 1~3개):
  선택: Raspberry Pi 4B
  이유: 비용 절감 + 빠른 실험 + 실패 비용 낮음
  대응: SD 카드 → SSD 변환 (수명 5~10년)
  
Phase 2 (매장 10~30개):
  선택: Raspberry Pi 4B + 매장 매니저 안내 강화
  이유: 비용 효율 우선
  대응: SSD 부착 + 케이스 강화 + 매장 매니저 *"산업용 IoT 기기"* 라벨링
  
Phase 3 (매장 30개+):
  선택: Advantech ARK 또는 동급 industrial-grade
  이유: 신뢰성 + 본사 신뢰도 + 매장당 추가 비용 분산 가능
  비용 영향: 매장당 도입비 +130~180만원
```

🔴 *"PoC 매장 3개에 산업용 IoT 게이트웨이"* 는 과잉. 라즈베리파이로 시작하되 *"내일 매장 50개 도달 시 산업용 마이그레이션"* 의 진화 경로 사전 설계.

---

## 2. Stage 2: 매장 측 집계 (1분 단위)

### 2.1 집계 로직 (Polars)

```python
import polars as pl
from datetime import datetime, timedelta

def aggregate_csi_minute(window_start: datetime, window_end: datetime):
    """1분 단위 CSI 집계."""
    
    # raw CSI 로드
    df = pl.read_database(
        "SELECT * FROM raw_csi WHERE timestamp_ms BETWEEN ? AND ?",
        connection=sqlite_conn,
        execute_options={"parameters": [
            int(window_start.timestamp() * 1000),
            int(window_end.timestamp() * 1000)
        ]}
    )
    
    # 피팅룸별 집계
    agg = (
        df.group_by("fitting_room_id")
        .agg([
            # 활동 강도 점수 (0~1 정규화)
            (pl.col("rssi").std() / 10.0).clip(0, 1).alias("activity_score"),
            # 점유 추정 (RSSI 변동 임계값)
            pl.col("rssi").std().gt(5.0).cast(pl.Int32).alias("occupancy_estimate"),
            # 움직임 패턴 분류
            pl.when(pl.col("rssi").std() < 2.0).then(pl.lit("idle"))
              .when(pl.col("rssi").std() < 7.0).then(pl.lit("moderate"))
              .otherwise(pl.lit("active")).alias("movement_pattern")
        ])
    )
    
    return agg
```

### 2.2 RFID-CSI 시간축 결합 (집계 단계에서 미리)

```python
def link_rfid_csi(window_start, window_end):
    """RFID 이벤트와 CSI 1분 집계 매칭."""
    
    rfid = pl.read_database("SELECT * FROM rfid_events WHERE ...", ...)
    csi = pl.read_database("SELECT * FROM csi_aggregates WHERE ...", ...)
    
    # 피팅룸별 + 시간 윈도우 매칭
    linked = csi.join_asof(
        rfid,
        left_on="window_start_ms",
        right_on="timestamp_ms",
        by="fitting_room_id",
        strategy="nearest",
        tolerance=60_000  # 1분 이내
    )
    
    return linked
```

### 2.3 AWS 전송용 페이로드 구성

```python
def build_aws_payload(batch_start, batch_end):
    """5분 배치 AWS 페이로드 (약 5KB)."""
    
    csi_aggs = pl.read_database("SELECT * FROM csi_aggregates WHERE ...", ...)
    rfid_summary = pl.read_database("SELECT ... FROM rfid_events WHERE ...", ...)
    pos_summary = pl.read_database("SELECT ... FROM pos_events WHERE ...", ...)
    
    payload = {
        "store_id": STORE_ID,
        "batch_start": batch_start.isoformat(),
        "batch_end": batch_end.isoformat(),
        "csi_aggregates": csi_aggs.to_dicts(),  # 5개 1분 집계
        "rfid_events": rfid_summary.to_dicts(),  # 5분 RFID 이벤트
        "pos_events": pos_summary.to_dicts()    # 5분 POS 이벤트
    }
    
    return payload  # 약 5KB
```

---

## 3. Stage 3: 매장 → AWS (5분 배치)

### 3.1 전송 로직

```python
import aiohttp
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=60))
async def send_to_aws(payload, send_queue_id):
    """AWS Ingest API에 5분 배치 전송."""
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.put(
                AWS_INGEST_URL,
                json=payload,
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                resp.raise_for_status()
                # 성공 시 큐에서 제거
                await delete_from_queue(send_queue_id)
                
        except aiohttp.ClientResponseError as e:
            if e.status in (429, 503):
                # AWS 일시 장애, 재시도
                raise
            elif e.status >= 500:
                # AWS 서버 장애, 재시도
                raise
            else:
                # 4xx 클라이언트 에러, 즉시 실패
                await mark_queue_failed(send_queue_id, str(e))
                raise
```

### 3.2 큐 기반 신뢰성

매장 게이트웨이의 `aws_send_queue` 테이블이 핵심.

```sql
-- 큐 폴링 (1분 cron)
SELECT * FROM aws_send_queue 
WHERE attempts < 5 
ORDER BY created_at_ms ASC 
LIMIT 10;
```

7일 후 자동 정리:
```sql
DELETE FROM aws_send_queue WHERE created_at_ms < (strftime('%s','now') - 7*86400) * 1000;
```

### 3.3 AWS 측 멱등성 보장

```python
# AWS Lambda Ingest
def lambda_handler(event, context):
    body = json.loads(event['body'])
    
    # 멱등 키 = store_id + batch_start
    idempotency_key = f"{body['store_id']}:{body['batch_start']}"
    
    # DynamoDB로 멱등성 체크
    if check_already_processed(idempotency_key):
        return {"statusCode": 200, "body": "Already processed"}
    
    # Firehose에 적재
    firehose_client.put_record(
        DeliveryStreamName="tryops-ingest",
        Record={"Data": json.dumps(body) + "\n"}
    )
    
    # 멱등성 기록 (TTL 7일)
    mark_processed(idempotency_key, ttl=7*86400)
    
    return {"statusCode": 200}
```

---

## 4. Stage 4: Firehose → S3 (자동)

### 4.1 Firehose 설정

```yaml
DeliveryStream: tryops-ingest
BufferingHints:
  IntervalInSeconds: 60   # 60초 또는
  SizeInMBs: 1            # 1MB 도달 시 적재
S3DestinationConfiguration:
  Bucket: tryops-data
  Prefix: "raw/store_id=!{partitionKeyFromQuery:store_id}/date=!{timestamp:yyyy-MM-dd}/hour=!{timestamp:HH}/"
  ErrorOutputPrefix: "error/!{firehose:error-output-type}/year=!{timestamp:yyyy}/"
  CompressionFormat: SNAPPY
  DataFormatConversionConfiguration:
    Enabled: true
    OutputFormatConfiguration:
      Serializer: ParquetSerDe
    SchemaConfiguration:
      DatabaseName: tryops_glue_db
      TableName: raw_events
```

### 4.2 동적 파티셔닝

Firehose 동적 파티셔닝으로 `store_id` 추출:

```yaml
ProcessingConfiguration:
  Enabled: true
  Processors:
    - Type: MetadataExtraction
      Parameters:
        - JsonParsingEngine: JQ-1.6
        - MetadataExtractionQuery: |
            {store_id: .store_id}
```

### 4.3 S3 파티션 구조

```
s3://tryops-data/
├── raw/
│   └── store_id=store_001/
│       └── date=2026-05-22/
│           ├── hour=15/
│           │   ├── tryops-1-2026-05-22-15-00-XXX.parquet
│           │   └── tryops-1-2026-05-22-15-01-YYY.parquet
│           └── hour=16/
│               └── ...
├── mart/
│   ├── sessions/store_id=store_001/date=2026-05-22/data.parquet
│   ├── joint_signals/store_id=store_001/date=2026-05-22/data.parquet
│   └── flow_signals/store_id=store_001/date=2026-05-22/data.parquet
├── reports/
│   └── brand_id=brand_001/month=2026-05/data.parquet
└── error/
    └── ... (Firehose 에러 격리)
```

---

## 5. Stage 5: ETL → Mart (배치)

### 5.1 Airflow DAG 구조

```python
# tryops_etl.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'tryops',
    'depends_on_past': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# 10분 단위 DAG (실시간 알람)
with DAG('tryops_realtime_alerts', schedule_interval='*/10 * * * *', ...):
    detect_assistance_need = PythonOperator(...)
    detect_phantom = PythonOperator(...)

# 1시간 단위 DAG (Joint Signal 계산)
with DAG('tryops_hourly', schedule_interval='@hourly', ...):
    reconstruct_sessions = PythonOperator(...)
    calculate_hesitation = PythonOperator(...)
    calculate_companion = PythonOperator(...)
    calculate_friction = PythonOperator(...)

# 1일 단위 DAG (본사 일별 마트)
with DAG('tryops_daily', schedule_interval='0 1 * * *', ...):
    build_store_daily_mart = PythonOperator(...)
    build_sku_daily_mart = PythonOperator(...)
    quality_check = PythonOperator(...)

# 1월 단위 DAG (본사 월간 보고)
with DAG('tryops_monthly', schedule_interval='0 2 1 * *', ...):
    build_monthly_report = PythonOperator(...)
    send_report_email = PythonOperator(...)
```

### 5.2 Polars + DuckDB 처리 로직

```python
import polars as pl
import duckdb

def calculate_hesitation_for_date(store_id, date):
    """일별 Hesitation Score 계산."""
    
    # S3 raw 로드 (Polars 직접)
    raw_uri = f"s3://tryops-data/raw/store_id={store_id}/date={date}/**/*.parquet"
    df = pl.scan_parquet(raw_uri).collect()  # lazy → eager
    
    # Session reconstruction (joint_signals_spec.md 알고리즘)
    sessions = reconstruct_sessions(df)
    
    # Hesitation Score 계산
    hesitation_df = (
        sessions.with_columns([
            calculate_hesitation_score_expr().alias("hesitation_score")
        ])
    )
    
    # DuckDB로 분석 마트 적재
    duckdb.sql(f"""
        CREATE OR REPLACE TABLE temp_sessions AS 
        SELECT * FROM hesitation_df
    """)
    
    # S3 적재
    duckdb.sql(f"""
        COPY (SELECT * FROM temp_sessions)
        TO 's3://tryops-data/mart/sessions/store_id={store_id}/date={date}/data.parquet'
        (FORMAT PARQUET, COMPRESSION SNAPPY)
    """)
```

### 5.3 데이터 품질 체크

각 DAG에 quality_check 태스크:

```python
def quality_check(store_id, date):
    """데이터 품질 검증."""
    
    mart_uri = f"s3://tryops-data/mart/sessions/store_id={store_id}/date={date}/data.parquet"
    df = pl.read_parquet(mart_uri)
    
    checks = {
        "row_count": len(df) > 0,
        "session_count_reasonable": 50 < len(df) < 10000,
        "hesitation_score_range": (df["hesitation_score"] >= 0).all() and (df["hesitation_score"] <= 1).all(),
        "no_null_essential": df.select(["store_id", "fitting_room_id", "session_start"]).null_count().sum().item() == 0
    }
    
    if not all(checks.values()):
        alert_sns({
            "store_id": store_id,
            "date": date,
            "failed_checks": [k for k, v in checks.items() if not v]
        })
```

---

## 6. 멀티 테넌트 격리

### 6.1 매장 → 본사 → 사용자 계층

```
brand_001 (본사)
├── stores
│   ├── store_001 (강남점)
│   ├── store_002 (홍대점)
│   └── ...
├── users
│   ├── user_001@brand_001.com (데이터팀장)
│   ├── user_002@brand_001.com (머천다이저)
│   └── ...
└── permissions
    ├── user_001: ["all_stores"]
    └── user_002: ["sku_analysis"]
```

### 6.2 권한 모델

```python
# Cognito Custom Attributes
{
  "custom:brand_id": "brand_001",
  "custom:role": "data_lead",  # data_lead | merchandiser | store_manager | viewer
  "custom:store_ids": "store_001,store_002"  # store_manager의 경우
}
```

### 6.3 데이터 접근 격리

API Gateway Lambda에서 권한 검증:

```python
def lambda_handler(event, context):
    user = parse_cognito_user(event)
    brand_id = user["custom:brand_id"]
    role = user["custom:role"]
    
    # Athena 쿼리 시 brand_id 강제 주입
    query = f"""
        SELECT * FROM mart.joint_signals 
        WHERE brand_id = '{brand_id}'
          AND date BETWEEN ? AND ?
    """
    
    # store_manager는 본인 매장만
    if role == "store_manager":
        store_ids = user["custom:store_ids"].split(",")
        query += f" AND store_id IN ({','.join(repr(s) for s in store_ids)})"
    
    return execute_athena_query(query)
```

---

## 7. 재처리 전략

### 7.1 매장 데이터 재전송

- 매장 게이트웨이 SQLite 7일 보존
- AWS 측 멱등성 보장 (idempotency_key)
- 재전송 안전

### 7.2 ETL 재실행

- Airflow DAG `clear` 명령으로 특정 날짜 재실행
- S3 마트 데이터는 멱등 (덮어쓰기 가능)
- 본사 대시보드 사용자에게 *"데이터 재계산 중"* 알림

### 7.3 스키마 변경

- Parquet 스키마 진화: 새 컬럼 추가는 호환
- 컬럼 삭제·타입 변경: 매장 게이트웨이 SW 동시 배포 필요
- Glue Data Catalog 자동 업데이트

---

## 8. 모니터링 설계

### 8.1 핵심 메트릭

| 메트릭 | 임계점 | 알람 |
|---|---|---|
| 매장 게이트웨이 → AWS 전송 성공률 | <99% | 매장 운영팀 알람 |
| Firehose 적재 latency | >60초 | 인프라팀 알람 |
| Athena 쿼리 평균 latency | >10초 | 본사 대시보드 UX 영향 |
| 매장 게이트웨이 큐 적체 | >100건 | 매장 인터넷 문제 의심 |
| ESP32-S3 노드 다운 | >24시간 | 매장 매니저 알람 |
| 일 ETL 성공률 | <99% | 데이터 품질 의심 |

### 8.2 로깅 표준

모든 Lambda·EC2 로그에 구조화 JSON:

```json
{
  "timestamp": "2026-05-22T15:30:45+09:00",
  "level": "INFO",
  "service": "ingest_lambda",
  "store_id": "store_001",
  "brand_id": "brand_001",
  "event_type": "batch_received",
  "batch_size_bytes": 5124,
  "trace_id": "abc-123"
}
```

---

## 9. 본 파이프라인 v1의 한계

본 v1 설계는:

- 🔴 실제 매장 환경 검증 0건
- 🔴 ESP32-S3 6개 동시 운영의 WiFi 부하 미측정
- 🔴 매장 인터넷 장애 시 7일 버퍼 실효성 미검증
- 🔴 Polars 집계의 1분 윈도우 처리 시간 미실측
- 🔴 RFID·POS 다양한 솔루션사 webhook 통합 어려움 미평가

**진짜 사업 시작 시**: PoC Week 1~4 매장 1개 실설치 후 v2 정밀화.

**본 문서 활용 가이드**: 데이터 엔지니어 채용 시 본 파이프라인을 *"전체 시스템 이해"* 자료로 활용. 면접 시 *"단계별 격리 + 멱등성 + 7일 복구"* 설계 원칙 강조.
