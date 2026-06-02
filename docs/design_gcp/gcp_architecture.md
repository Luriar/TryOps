# TryOps GCP Architecture v1 — Stage 1·2 매장 MVP·확장 설계

> 본 문서는 TryOps 시스템의 **GCP 기반 Stage 1·2 아키텍처 설계**다. AWS 설계 v2-fix (`/tryops_design/architecture.md`) 의 GCP 동등 매핑.
>
> **Stage 0 (개념 검증)** 은 GCP 무관 (본인 환경 + ESP32-S3 + 노트북). `concept_validation_spec.md` 참조.
>
> **본 v1의 한계**: 실제 GCP 계정·매장 환경 미실측. 비용은 공개 가격표 + 추정. Stage 0 완료 후 PoC Week 1~4에 실측 후 v2 정밀화.
>
> 신뢰도 표기:
> - 🟢 GCP 공식 가격표 + 한국 법규 직접 인용
> - 🟡 합리적 추정 (검증 데이터 기반)
> - 🔴 가설 (PoC 단계 검증 필요)

---

## 0. Executive Summary — 30초

TryOps의 GCP 시스템은 **매장 측 ESP32-S3 + Raspberry Pi → Cloud Endpoints → Pub/Sub → BigQuery 직접 적재** 의 단순 구조다. **서울 리전 (asia-northeast3)** 으로 한국 본사 신뢰·법규 준수 + latency 최적.

핵심 설계 결정 5가지:
1. **Pub/Sub → BigQuery 직접 subscription** — Dataflow 불필요, AWS Firehose 대비 더 단순
2. **BigQuery 통합 데이터 마트** — S3 + Athena 대체. 무료 한도 활용 가능
3. **Compute Engine e2-small + Polars + DuckDB** — EC2 t4g.small 대체 (x86, ARM 없음)
4. **Cloud Run + Identity Platform** — Lambda + Cognito 대체. 컨테이너 기반 유연성
5. **모든 리소스에 비용 추적 Label 부착** — 실시간 비용 모니터링

**비용 (매장 100개, 케이스 B 보수 가정)**:
- 월 약 $47~52 (AWS $51 와 동등 수준)
- BigQuery·Pub/Sub 무료 한도 0 가정 (기업 계정 통합 시 이미 사용 중)

---

## 1. AWS → GCP 서비스 매핑

| AWS 서비스 | GCP 매핑 | 정합성 | 비고 |
|---|---|---|---|
| Kinesis Firehose | **Pub/Sub + BigQuery subscription** | 🟢 더 단순 | Dataflow 불필요 |
| S3 + Athena | **Cloud Storage + BigQuery** | 🟢 동등 이상 | BigQuery가 Athena보다 빠름 |
| EC2 t4g.small | **Compute Engine e2-small** | 🟡 x86, ARM 없음 | 비용 비슷 |
| Lambda | **Cloud Run** (선호) 또는 Cloud Functions | 🟢 더 유연 | 컨테이너 기반 |
| API Gateway | **Cloud Endpoints** 또는 **API Gateway** | 🟢 동등 | gRPC 지원 |
| Cognito | **Identity Platform** + Firebase Auth | 🟡 유사 | 마이그레이션 약간 작업 필요 |
| DynamoDB | **Firestore** 또는 **Bigtable** | 🟢 동등 | Firestore가 단순 |
| RDS Postgres | **Cloud SQL Postgres** | 🟢 동등 | 마이그레이션 호환 |
| CloudWatch | **Cloud Monitoring + Cloud Logging** | 🟢 동등 | 통합 |
| KMS | **Cloud KMS** | 🟢 동등 | |
| GuardDuty | **Security Command Center** | 🟢 동등 | |
| WAF | **Cloud Armor** | 🟢 동등 | |
| Cloudflare Pages | 유지 (외부) | - | 변경 없음 |

---

## 2. 시스템 전체 구성도

```
┌──────────────────────────────────────────────────────────────┐
│ 매장 측 (On-Premise) — AWS와 동일                              │
│                                                                │
│   [피팅룸 #1]   [피팅룸 #2]   [피팅룸 #3]   ...               │
│       │            │            │                              │
│   ESP32-S3      ESP32-S3      ESP32-S3                        │
│       │            │            │                              │
│       └────────────┼────────────┘                             │
│                    ↓                                            │
│         ┌──────────────────┐                                   │
│         │ 매장 게이트웨이      │                                 │
│         │ (Raspberry Pi 4B) │  ← RFID 솔루션사 webhook         │
│         │                   │  ← POS API                       │
│         │ - 데이터 통합       │                                 │
│         │ - 익명 집계         │                                 │
│         │ - 7일 로컬 버퍼     │                                 │
│         └────────┬──────────┘                                  │
└──────────────────┼─────────────────────────────────────────────┘
                   │ HTTPS (5분 배치)
                   ↓
┌──────────────────────────────────────────────────────────────┐
│ GCP 클라우드 (asia-northeast3 서울)                            │
│                                                                │
│   ┌─────────────────────┐                                     │
│   │ Cloud Endpoints      │  ← REST 엔드포인트                  │
│   │ + Cloud Run (Ingest) │  ← 인증 + Pub/Sub publish          │
│   └──────────┬──────────┘                                    │
│              ↓                                                │
│   ┌─────────────────────┐                                     │
│   │ Pub/Sub 토픽          │  ← tryops-store-events             │
│   │ (BigQuery subscription)│  ← 직접 적재, Dataflow 불필요    │
│   └──────────┬──────────┘                                    │
│              ↓                                                │
│   ┌─────────────────────────────────────┐                    │
│   │ BigQuery (파티셔닝 + 클러스터링)        │                    │
│   │ tryops_data 데이터셋                  │                    │
│   │   raw_events 테이블 (날짜 파티션)       │                    │
│   │   joint_signals (날짜·매장 파티션)      │                    │
│   │   reports (월별 파티션)                │                    │
│   └──────────┬──────────────────────────┘                    │
│              ↓                                                │
│   ┌─────────────────────┐   ┌──────────────────────┐         │
│   │ Cloud Scheduler      │ → │ Compute Engine       │         │
│   │ (cron: 1시간/24시간)  │   │ e2-small             │         │
│   └─────────────────────┘   │ (Polars + DuckDB +   │         │
│                              │  Cloud Composer or   │         │
│                              │  self-hosted Airflow)│         │
│                              └──────────┬───────────┘         │
│                                          ↓                     │
│   ┌─────────────────────┐                                     │
│   │ BigQuery 마트         │  ← 본사 대시보드 쿼리                │
│   │ joint_signals, reports│                                    │
│   └──────────┬──────────┘                                    │
│              ↓                                                │
│   ┌─────────────────────┐                                     │
│   │ Cloud Endpoints      │  ← 본사 대시보드 (Next.js on       │
│   │ + Cloud Run (Query)  │     Cloudflare Pages)              │
│   │ + Identity Platform  │                                    │
│   └──────────┬──────────┘                                    │
│              ↓                                                │
│   ┌─────────────────────┐                                     │
│   │ 본사 대시보드 (웹)     │                                    │
│   │ 매장 대시보드 (웹)     │                                    │
│   └─────────────────────┘                                     │
│                                                                │
│   ┌─────────────────────┐                                     │
│   │ Firestore               │  ← 매장·본사·SKU 메타데이터       │
│   │ (또는 Cloud SQL)         │                                  │
│   └─────────────────────┘                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 핵심 설계 결정 5가지 (AWS 대비 변경점)

### 결정 1: Pub/Sub → BigQuery 직접 subscription

**AWS 원본**: Kinesis Firehose → S3 (Parquet)
**GCP 매핑**: Pub/Sub → BigQuery 직접 (BigQuery subscription)

**근거**:
- 🟢 Pub/Sub BigQuery subscription은 **Dataflow 불필요**. 메시지가 자동으로 BigQuery 테이블에 적재
- 🟢 Pub/Sub: $50/TiB (subscribe throughput) — 매장 100개 월 4.5GB = **약 $0.22**
- 🟢 BigQuery 적재 비용 무료 (subscription 비용에 포함)
- 매장 → AWS Firehose → S3 Parquet 의 3단계가 매장 → Pub/Sub → BigQuery 2단계로 단순화

**손실**:
- Pub/Sub 메시지 보존 7일 한도 (Firehose는 무관)
- → BigQuery 적재 후 raw_events 테이블이 진짜 보존소

### 결정 2: BigQuery 통합 (S3 + Athena 통합 대체)

**AWS 원본**: S3 (raw 저장) + Athena (쿼리)
**GCP 매핑**: BigQuery (저장 + 쿼리 통합)

**근거**:
- 🟢 BigQuery는 *"데이터 웨어하우스 + 쿼리 엔진"* 통합
- 🟢 컬럼나 스토리지 자동 (Parquet 변환 불필요)
- 🟢 파티셔닝 + 클러스터링이 native (Athena Parquet 파티셔닝 대비 자동)
- 🟢 storage 비용 동등 ($0.02/GB active, $0.01/GB long-term 90일+)

**테이블 설계**:

```sql
-- raw_events: 매장 → 5분 배치 데이터
CREATE TABLE tryops_data.raw_events (
  brand_id STRING,
  store_id STRING,
  batch_start TIMESTAMP,
  batch_end TIMESTAMP,
  csi_aggregates JSON,
  rfid_events JSON,
  pos_events JSON,
  ingested_at TIMESTAMP
)
PARTITION BY DATE(batch_start)
CLUSTER BY brand_id, store_id;

-- joint_signals: ETL 결과
CREATE TABLE tryops_data.joint_signals (
  brand_id STRING,
  store_id STRING,
  sku_id STRING,
  session_id STRING,
  date DATE,
  hesitation_score FLOAT64,
  companion_probability FLOAT64,
  fitting_friction FLOAT64,
  -- ...
  computed_at TIMESTAMP
)
PARTITION BY date
CLUSTER BY brand_id, store_id, sku_id;

-- reports: 본사 월간 보고
CREATE TABLE tryops_data.reports (
  brand_id STRING,
  report_month DATE,
  metrics JSON,
  generated_at TIMESTAMP
)
PARTITION BY report_month
CLUSTER BY brand_id;
```

### 결정 3: Compute Engine e2-small (EC2 t4g.small 대체)

**AWS 원본**: EC2 t4g.small (ARM, Graviton2)
**GCP 매핑**: Compute Engine e2-small (x86, AMD/Intel)

**근거**:
- 🟡 GCP는 ARM 인스턴스 미제공 (T2A 시리즈는 limited availability)
- 🟢 e2-small: 2 vCPU, 2GB RAM, **$0.0167/시간** = 월 약 $12.2
- 🟡 AWS EC2 t4g.small ($15/월) 보다 약간 저렴
- Polars + DuckDB는 x86에서도 동일 성능

**SW 스택**:
- Container-Optimized OS (COS) 또는 Ubuntu 22.04
- Python 3.11 + Polars + DuckDB
- Airflow self-hosted (Cloud Composer는 비싸므로 Phase 3+ 검토)
- Cloud Logging Agent

### 결정 4: Cloud Run + Identity Platform (Lambda + Cognito 대체)

**Cloud Run** (vs Cloud Functions 선택):
- Cloud Run: 컨테이너 기반, **무료 한도 매월 200만 요청**
- Cloud Functions Gen 2: 동일하게 200만 요청 무료
- → **Cloud Run 선호**: 동일 Docker 이미지를 매장 게이트웨이·로컬 개발·GCP 통합 사용 가능

**Identity Platform**:
- Firebase Auth 기반 + 엔터프라이즈 기능
- Cognito User Pools 대체
- 멀티테넌트 (브랜드별 격리) 지원
- MAU 5만까지 무료 (Cognito와 동일)

### 결정 5: 비용 추적 Label 표준 (GCP의 핵심 차별점)

**AWS 원본**: 모든 리소스에 Tags (`store_id`, `brand_id`, `module`, `phase`)
**GCP 매핑**: 모든 리소스에 Labels — Terraform `labels = {...}` 자동 부착

**표준 라벨 5종**:

```hcl
labels = {
  project     = "tryops"
  environment = "production"  # or "dev", "staging"
  module      = "data"        # or "compute", "storage", "api", "security", "monitoring"
  cost_center = "core"        # or "ingest", "etl", "dashboard"
  managed_by  = "terraform"
}
```

**활용**:
- GCP Billing Export → BigQuery `gcp_billing_export_v1_xxx` 테이블
- 라벨별 비용 집계 쿼리 (예: cost_center='ingest' 월 비용)
- Cloud Monitoring 비용 대시보드 자동 생성

상세는 섹션 6 참조.

---

## 4. 데이터 흐름 5단계 (AWS와 동일 구조)

AWS 설계 `data_pipeline.md` 와 거의 동일. 변경점만 명시:

### Stage 1·2: 매장 측 수집·집계 (동일)
- ESP32-S3 → Raspberry Pi → SQLite
- Polars 1분 집계
- AWS·GCP 무관

### Stage 3: 매장 → GCP (5분 배치, 변경)

```python
# 매장 게이트웨이 → GCP Cloud Run Ingest API
import aiohttp
import google.auth.transport.requests
import google.oauth2.id_token

async def send_to_gcp(payload, send_queue_id):
    """GCP Cloud Run에 5분 배치 전송."""
    
    # Service Account JWT 발급 (Cloud Run IAM)
    auth_req = google.auth.transport.requests.Request()
    id_token_credentials = google.oauth2.id_token.fetch_id_token(
        auth_req, GCP_INGEST_URL
    )
    
    async with aiohttp.ClientSession() as session:
        async with session.put(
            GCP_INGEST_URL,
            json=payload,
            headers={"Authorization": f"Bearer {id_token_credentials}"},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            resp.raise_for_status()
            await delete_from_queue(send_queue_id)
```

### Stage 4: Ingest Lambda → BigQuery (대체)

```python
# Cloud Run Ingest 함수 (Python 3.11 + Flask)
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1
import json
import hashlib

app = Flask(__name__)
publisher = pubsub_v1.PublisherClient()
TOPIC_PATH = "projects/tryops-prod/topics/store-events"

@app.route("/ingest", methods=["POST"])
def ingest():
    payload = request.get_json()
    
    # 멱등 키 = brand_id + store_id + batch_start
    idempotency_key = f"{payload['brand_id']}:{payload['store_id']}:{payload['batch_start']}"
    idempotency_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
    
    # Firestore로 멱등성 체크 (TTL 7일)
    if check_already_processed(idempotency_hash):
        return jsonify({"status": "duplicate"}), 200
    
    # Pub/Sub publish (BigQuery subscription이 자동 적재)
    future = publisher.publish(
        TOPIC_PATH,
        json.dumps(payload).encode("utf-8"),
        brand_id=payload["brand_id"],
        store_id=payload["store_id"]
    )
    future.result()
    
    mark_processed(idempotency_hash, ttl=7*86400)
    return jsonify({"status": "ok"}), 200
```

### Stage 5: ETL → BigQuery 마트 (동일 구조)

- Compute Engine에서 Polars + DuckDB 실행
- BigQuery `raw_events` → Polars로 로드
- ETL 후 BigQuery `joint_signals` 적재
- AWS 설계 동일

---

## 5. 보안 설계 (AWS 매핑)

### 5.1 위협 모델 (security_design.md STRIDE 동일)

GCP 매핑된 대응:

| 위협 | AWS 대응 | GCP 매핑 |
|---|---|---|
| 매장 게이트웨이 도난 (T-1) | SQLCipher + API 키 회전 | 동일 (게이트웨이 SW) + **Secret Manager** |
| ESP32-S3 펌웨어 위조 (T-2) | TLS Mutual Auth + 화이트리스트 | 동일 |
| 본사 권한 우회 (T-3) | Cognito JWT + IAM | **Identity Platform JWT + IAM Conditions** |
| AWS S3 격리 (T-4) | bucket policy + KMS | **Cloud Storage IAM + Cloud KMS** |

### 5.2 GCP 보안 서비스

| AWS | GCP | 비용 (월) |
|---|---|---|
| GuardDuty | **Security Command Center Standard** | 무료 (Premium $추가) |
| AWS Shield Standard | **Cloud Armor** (기본 무료) | 무료 (Standard 규칙) |
| AWS Shield Advanced | Cloud Armor Managed Protection Plus | $3,000+ (대규모만) |
| CloudTrail | **Cloud Audit Logs** | 무료 (Admin Activity), $0.50/GB (Data Access) |
| WAF | **Cloud Armor** | $5/policy + $0.75/백만 요청 |
| KMS | **Cloud KMS** | $0.06/key/월 + $0.03/만 ops |

**Phase 1·2 GCP 보안 추가 비용 (매장 100개)**: 약 $25~35 (AWS $40 보다 저렴)

### 5.3 멀티테넌트 격리 5레이어 (동일 구조)

| 레이어 | AWS | GCP |
|---|---|---|
| Identity | Cognito Custom Attribute | Identity Platform Custom Claims |
| IAM | 본사별 IAM Role | 본사별 GCP Service Account + IAM Conditions |
| Backend | Lambda + brand_id 강제 주입 | Cloud Run + brand_id 강제 주입 |
| Analytics | Athena Workgroup | **BigQuery Reservation per brand** (Phase 3+) |
| Storage | S3 Prefix + KMS per brand | **Cloud Storage Bucket per brand + Cloud KMS** |

---

## 6. 비용 추적 Label 표준 (사용자 요구사항)

### 6.1 표준 라벨 5종

```hcl
# infra/terraform/shared/locals.tf
locals {
  common_labels = {
    project     = "tryops"
    environment = var.environment  # production | staging | dev
    managed_by  = "terraform"
  }
}

# 모듈별 추가 라벨 (반드시 5종 라벨 완성)
# - modules/data/main.tf: module = "data", cost_center = "ingest"
# - modules/compute/main.tf: module = "compute", cost_center = "etl"
# 등
```

### 6.2 라벨이 적용되는 리소스

- ✅ Compute Engine 인스턴스
- ✅ Cloud Storage 버킷
- ✅ BigQuery 데이터셋·테이블
- ✅ Pub/Sub 토픽·subscription
- ✅ Cloud Run 서비스
- ✅ Cloud SQL 인스턴스
- ✅ Cloud KMS 키
- ✅ Firestore (project 단위)
- ✅ Cloud Functions

### 6.3 GCP Billing Export → BigQuery

```hcl
# infra/terraform/modules/monitoring/billing_export.tf
resource "google_bigquery_dataset" "billing_export" {
  dataset_id    = "billing_export"
  friendly_name = "GCP Billing Export"
  location      = "asia-northeast3"
  
  labels = merge(local.common_labels, {
    module      = "monitoring"
    cost_center = "core"
  })
}

# Billing Export는 GCP 콘솔에서 설정 필수
# (Terraform으로 직접 Billing Export 생성 불가)
# 대신 Billing Account ID를 변수로 받아 안내문 출력
output "billing_export_setup_instructions" {
  value = <<-EOT
  Billing Export 활성화:
  1. GCP Console → Billing → Billing Export → BigQuery Export
  2. 데이터셋 선택: ${google_bigquery_dataset.billing_export.dataset_id}
  3. 활성화 후 24시간 내 첫 데이터 적재
  EOT
}
```

### 6.4 비용 분석 쿼리 (BigQuery)

```sql
-- 모듈별 일별 비용 (terraform labels 활용)
SELECT
  labels.value AS module,
  DATE(usage_start_time) AS date,
  SUM(cost) AS daily_cost_usd
FROM `tryops-prod.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "module"
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY module, date
ORDER BY date DESC, daily_cost_usd DESC;

-- cost_center별 월 비용
SELECT
  labels.value AS cost_center,
  FORMAT_DATE('%Y-%m', DATE(usage_start_time)) AS month,
  SUM(cost) AS monthly_cost_usd
FROM `tryops-prod.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "cost_center"
GROUP BY cost_center, month
ORDER BY month DESC, monthly_cost_usd DESC;

-- 매장별 한계비용 (store_id 라벨 활용)
SELECT
  labels.value AS store_id,
  SUM(cost) AS monthly_cost_usd
FROM `tryops-prod.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "store_id"
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY store_id
ORDER BY monthly_cost_usd DESC
LIMIT 100;
```

### 6.5 Cloud Monitoring 비용 대시보드

```hcl
# infra/terraform/modules/monitoring/dashboard.tf
resource "google_monitoring_dashboard" "cost_dashboard" {
  dashboard_json = jsonencode({
    displayName = "TryOps Cost Dashboard"
    gridLayout = {
      widgets = [
        {
          title = "Daily Cost by Module"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesQueryLanguage = <<-EOT
                  fetch billing/cost
                  | filter labels.module = ANY ['data','compute','storage','api']
                  | group_by [labels.module], sum(value.cost)
                EOT
              }
            }]
          }
        },
        # ... 추가 차트
      ]
    }
  })
}
```

### 6.6 비용 알람

```hcl
# infra/terraform/modules/monitoring/billing_alert.tf
resource "google_billing_budget" "monthly_budget" {
  billing_account = var.billing_account_id
  display_name    = "TryOps Monthly Budget"
  
  budget_filter {
    projects = ["projects/${var.project_id}"]
    labels = {
      project = "tryops"
    }
  }
  
  amount {
    specified_amount {
      currency_code = "USD"
      units         = "100"  # $100/월 예산
    }
  }
  
  threshold_rules {
    threshold_percent = 0.5  # 50% 도달 시 경고
    spend_basis       = "CURRENT_SPEND"
  }
  threshold_rules {
    threshold_percent = 0.8  # 80% 도달 시 알람
  }
  threshold_rules {
    threshold_percent = 1.0  # 100% 도달 시 긴급
  }
  
  all_updates_rule {
    pubsub_topic = google_pubsub_topic.budget_alerts.id
    monitoring_notification_channels = [
      google_monitoring_notification_channel.email.id
    ]
  }
}
```

---

## 7. 단계별 비용 모델 (케이스 B 메인)

### 7.1 비용 계산 가정

**케이스 B (메인)**: 기업이 이미 GCP 사용 중이고 무료 한도 (BigQuery 1TB, Pub/Sub 10GB) 가 본사 다른 워크로드에 이미 소진됨. **TryOps 추가 사용량은 100% 유료**.

**케이스 A (첨언)**: TryOps 단독 GCP 계정 신규 생성. 무료 한도 매월 활용 가능.

상세 비용은 `gcp_cost_model.md` 참조.

### 7.2 매장 100개 비용 비교 (월 USD)

| 항목 | AWS v2-fix | GCP 케이스 B (무료 한도 0) | GCP 케이스 A (무료 한도 활용) |
|---|---|---|---|
| Ingest 처리 | Firehose $0.13 | Pub/Sub $0.22 | Pub/Sub $0 (10GB 한도 내) |
| 데이터 저장 | S3 $7 | BigQuery storage $9 | BigQuery storage $8.8 |
| 쿼리 | Athena $1.50 | BigQuery query $13.5 | BigQuery query $8.5 |
| 컴퓨팅 | EC2 $15 | Compute Engine e2-small $12.2 | Compute Engine $12.2 |
| API | API GW + Lambda $1 | Cloud Endpoints + Cloud Run $5 | Cloud Run $0 (200만 무료) |
| 인증 | Cognito $0 | Identity Platform $0 | Identity Platform $0 |
| 모니터링 | CloudWatch $7.5 | Cloud Monitoring + Logging $7 | Cloud Monitoring $5 |
| 메타데이터 | DynamoDB $0.30 | Firestore $0.50 | Firestore $0.50 |
| Data Transfer | $5 | $3 | $3 |
| 보안 | (기본) | Security Command Center 무료 | Security Command Center 무료 |
| **합계** | **약 $51** | **약 $50** | **약 $38** |

🟢 **GCP 케이스 B (기업 가정) 가 AWS와 거의 동일**. 케이스 A는 무료 한도 덕에 $13 저렴하지만 사용자 지적대로 *"기업 입장"* 에서는 케이스 B 메인.

🟢 **GCP의 결정적 우위는 비용보다 *"구조 단순"***: Pub/Sub → BigQuery 직접 적재가 Firehose → S3 → Athena 3단계를 2단계로 단축.

---

## 8. SLA · 가용성 (AWS와 동일)

GCP 서비스 가용성 SLA:
- **BigQuery**: 99.99% (multi-region) / 99.9% (single region)
- **Pub/Sub**: 99.95%
- **Cloud Run**: 99.95%
- **Cloud Storage**: 99.9% (regional)
- **Compute Engine**: 99.5% (single instance) / 99.99% (multi-region)

본 설계 SLA (서비스 통합):
- 본사 대시보드: **99.5%** (Cloud Run 한도)
- 매장 → GCP 전송: **99%** (매장 인터넷 부담)
- 일별 ETL: **99%**

AWS와 동등.

---

## 9. Phase 진화 트리거 (AWS와 동일)

매장 200~300개 도달 시 Phase 3 진화 검토:

| 트리거 | AWS 대응 | GCP 대응 |
|---|---|---|
| Compute CPU 80%+ | EC2 m6g.large 스케일업 | Compute Engine e2-medium → e2-standard-4 |
| 일 쿼리 50TB+ | Athena Provisioned | **BigQuery Editions (Standard/Enterprise)** |
| 실시간 알람 < 60초 | Kinesis Data Streams | **Pub/Sub Pull Subscription + Cloud Run trigger** |
| 본사 1,000개+ | Cognito Identity Pools | **Identity Platform multi-project** |

---

## 10. Stage 0 → Stage 1 → GCP 진입 흐름

```
[Stage 0] 본인 환경 검증 (4주, 3만원)
  └ GCP 무관, ESP32-S3 + 노트북
  ↓ 통과
[Stage 1] 매장 MVP (6개월, 1.5~2.5억원)
  └ GCP 진입 — 본 문서 설계 따라 Terraform 배포
  └ 매장 1개 PoC
  ↓ 통과
[Stage 2] 확장 (1~3년, 5~30억/년)
  └ 매장 10~500개
  └ Phase 진화 트리거 도달 시 GCP 서비스 업그레이드
```

---

## 11. 향후 검증 과제 (PoC 단계)

본 v1 설계도 다음은 검증 못 함:

- 🔴 Pub/Sub BigQuery subscription 실측 latency
- 🔴 BigQuery 쿼리 패턴의 실제 scanned 데이터량
- 🔴 Compute Engine e2-small의 매장 100개 처리 한계
- 🔴 Identity Platform multi-tenant 격리 실제 검증
- 🔴 Cloud Run 콜드 스타트 영향

위 5개는 Stage 1 PoC Week 1~4에 측정 → v2 정밀화.

---

## 12. 보조 문서

- `gcp_cost_model.md` — GCP 서비스별 비용 정밀 분해 + 매장 수별 시나리오
- `infra/terraform/` — Terraform 모듈 코드 (실제 배포 가능)
- `concept_validation_spec.md` — Stage 0 (GCP 무관)
- AWS 원본: `/tryops_design/architecture.md`

---

## 13. 본 GCP 설계 v1 활용 가이드

**진짜 사업 시작 시**:
1. GCP 계정 생성 + asia-northeast3 리전 선택
2. Stage 1 매장 1개 PoC 인프라 배포:
   ```bash
   cd infra/terraform/environments/dev
   terraform init
   terraform plan
   terraform apply
   ```
3. 매장 게이트웨이 SW → Cloud Run Ingest 호출 변경 (AWS Lambda 대신)
4. PoC Week 1~4 측정 → v2 갱신

**Terraform 모듈 진입점**: `infra/terraform/environments/dev/main.tf`

**비용 모니터링**: GCP Console → Billing → Budgets and alerts → BigQuery query (섹션 6.4)

**본 설계의 진짜 가치**: AWS 대비 *"비용 비슷, 구조 단순, BigQuery 통합 우수, 무료 한도는 보너스"* 의 GCP 매핑.
