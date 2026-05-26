# Infra Cost Model — AWS 서비스별 비용 정밀 분해

> 본 문서는 `architecture.md` 섹션 4 비용 모델의 상세 자료다. AWS 서비스별 가격표 (2026.04 기준), 매장 수별 시나리오, 비용 최적화 옵션을 정밀 정리.
>
> **본 문서의 한계**: 모든 비용은 공개 가격표 + 추정 기반. PoC Week 1~4 실측 후 v2 정밀화 필수.

---

## 0. 가격 기준 — 모든 비용 ap-northeast-2 (서울 리전), 2026.04 기준

환율: 1 USD = 약 1,300 KRW (2026 변동)

---

## 1. AWS 서비스별 단가표 (검증)

### 1.1 Kinesis Firehose (선택된 서비스)

🟢 출처: AWS 공식 가격표
- **Direct PUT $0.029/GB**
- 첫 500TB/월부터 $0.024/GB (대량 할인)
- VPC delivery: $0.01/GB 추가
- Format conversion (Parquet 변환): $0.018/GB 추가 → **자동 Parquet 적재 비용 포함**

본 사용 케이스 (매장당 일 1.5MB → 월 45MB):
- 매장 1개: 월 $0.0013 (사실상 무료)
- 매장 100개: 월 $0.13
- 매장 1,000개: 월 $1.5

### 1.2 Kinesis Data Streams (대체 옵션, 비추천)

🟢 출처: AWS 공식
- **On-demand 모드**: $0.04/GB + **per-stream $0.04/시간** (월 약 $29/스트림)
- Provisioned 모드: $0.015/shard-hour + $0.014/백만 PUT units

본 사용 케이스 비교:
- 매장 100개 시 Firehose: $0.13 vs Data Streams on-demand: **$29+** (스트림 비용)
- → Firehose가 **약 220배 저렴** (확장 시에도 유리)

### 1.3 S3 Standard

🟢 출처: AWS 공식 ap-northeast-2
- **Storage: $0.023/GB-month**
- PUT 요청: $0.0045/1000 요청
- GET 요청: $0.00037/1000 요청
- Data Transfer Out (인터넷): $0.126/GB (첫 10TB)

본 사용 케이스:
- 매장 100개 × 월 3GB = 300GB → **월 $7**
- PUT 요청: 매장당 일 288회 (5분 간격) × 100 매장 × 30일 = 86.4만 요청 → 월 $4
- GET 요청: Athena가 scanned 데이터마다 GET → 약 $1~3
- 합계: 약 **$12/월**

### 1.4 Athena

🟢 출처: AWS 공식, Cloud Burn 2026.04
- **$5.00/TB scanned**
- 10MB 최소 (작은 쿼리도 10MB로 청구)
- DDL 무료 (CREATE TABLE, SHOW PARTITIONS)
- Provisioned Capacity: $0.40/DPU-hour (최소 24 DPU = 시간당 $9.60 = 월 $6,912)

**비용 최적화**:
- Parquet + 파티셔닝으로 scanned 85~95% 절감
- 매장당 1일 데이터 약 1.5MB → 본사 대시보드 일 쿼리 약 30MB scanned

본 사용 케이스 (매장 100개):
- 일별 본사 쿼리 약 30회 × 매장 100개 시 평균 100MB scanned/쿼리 = 일 약 3GB scanned
- 월 약 90GB scanned = **월 $0.45**
- 단, 본사 N개 가정 시 N배 증가
- 본사 5개 가정: 월 약 $2

🔴 **주의**: 위 추정은 *"잘 작성된 쿼리"* 기준. 실제로는 잘못된 쿼리(SELECT *, 파티션 미적용 등)로 10배 이상 가능.

### 1.5 EC2 t4g.small

🟢 출처: AWS 공식 ap-northeast-2
- **On-demand**: $0.0208/시간 = **월 약 $15**
- Spot: 약 $0.005/시간 = 월 약 $4 (불안정성 감수)
- Reserved 1년: 약 30% 할인 = 월 약 $10.5

본 사용 케이스: Phase 1·2 단일 인스턴스로 충분.

### 1.6 Lambda

🟢 출처: AWS 공식
- 첫 100만 요청 무료, 이후 $0.20/백만 요청
- 컴퓨팅: $0.0000166667/GB-초 (메모리 1024MB 기준 $0.0000166667/초)
- 무료 한도: 월 100만 요청 + 40만 GB-초

본 사용 케이스 (매장 100개):
- Ingest Lambda: 매장당 일 288회 × 100 매장 × 30일 = 86.4만 요청 → **무료 한도 내**
- Query Lambda: 본사당 일 100회 × 5 본사 × 30일 = 1.5만 요청 → 무료
- 합계: **월 $0** (무료 한도 내)

### 1.7 API Gateway

🟢 출처: AWS 공식
- REST API: **$3.50/백만 요청**
- HTTP API: $1.00/백만 요청 (REST 보다 70% 저렴)
- 첫 100만 요청까지 무료 (12개월 free tier)

본 사용 케이스 (매장 100개):
- 매장 → AWS Ingest: 매장당 일 288회 × 100 × 30 = 86.4만 요청 → **무료**
- 본사 대시보드: 1.5만 요청 → 무료
- HTTP API 사용 시 추가 절감 (이미 무료지만 확장 시 유리)

### 1.8 Cognito User Pools

🟢 출처: AWS 공식
- 월 5만 MAU까지 **무료**
- 5만 초과: $0.0055/MAU
- Advanced Security: 추가 $0.05/MAU

본 사용 케이스:
- 본사당 사용자 10~30명 × 본사 100개 = 1,000~3,000명
- **월 무료 한도 내** (본사 1,000개까지 무료)

### 1.9 CloudWatch Logs

🟢 출처: AWS 공식
- Ingestion: $0.50/GB
- Storage: $0.03/GB-month
- 무료 한도: 5GB/월

본 사용 케이스:
- 매장 100개 × Lambda 로그 약 100MB/월 = 10GB → **약 $5/월** (무료 한도 5GB 초과)
- 최적화: 로그 보존 기간 30일로 단축

### 1.10 Data Transfer

🟢 출처: AWS 공식
- AWS 내부 동일 리전: **무료**
- AWS → 인터넷: $0.126/GB (첫 10TB)
- AWS → CloudFront: 무료

본 사용 케이스 (매장 100개):
- 매장 → AWS in: **무료**
- AWS → 본사 대시보드 (CloudFront 경유): 무료
- 합계: **약 $0**

### 1.11 RDS Postgres (메타데이터)

🟢 출처: AWS 공식
- **db.t4g.micro**: $0.018/시간 = 월 약 $13
- Storage gp3: $0.115/GB-month
- 백업: 무료 (DB 크기 100% 까지)

본 사용 케이스: 매장·본사·SKU 메타데이터 약 1GB → **월 약 $13~15**.

### 1.12 DynamoDB (대체 옵션)

🟢 출처: AWS 공식
- On-demand: $1.25/백만 쓰기 요청, $0.25/백만 읽기 요청
- Storage: $0.25/GB-month
- 무료 한도: 25GB 저장 + 2,500만 요청

본 사용 케이스: 메타데이터 1GB → **월 $0** (무료 한도 내)

→ 본 설계는 **DynamoDB 권장** (PoC 단계 비용 절감).

---

## 2. 매장 수별 시나리오 — 정밀 모델

### 2.1 시나리오 A: PoC 단계 (매장 1개, 본사 0개)

| 서비스 | 월 비용 (USD) |
|---|---|
| EC2 t4g.small | $15.00 |
| Firehose | $0.00 (45MB/매장 → 사실상 무료) |
| S3 Standard | $0.10 |
| Athena | $0.05 |
| Lambda | $0.00 (무료 한도) |
| API Gateway | $0.00 (무료 12개월) |
| Cognito | $0.00 |
| CloudWatch | $0.50 |
| DynamoDB | $0.00 (무료 한도) |
| Data Transfer | $0.50 |
| **합계** | **약 $16** |

매장 1개 운영 비용 **약 2만원/월**.

### 2.2 시나리오 B: 초기 단계 (매장 10개, 본사 2개)

| 서비스 | 월 비용 (USD) |
|---|---|
| EC2 t4g.small | $15.00 |
| Firehose (450MB) | $0.01 |
| S3 Standard (30GB) | $0.70 |
| Athena (10GB scanned) | $0.05 |
| Lambda | $0.00 |
| API Gateway | $0.00 |
| Cognito | $0.00 |
| CloudWatch (10GB) | $5.00 |
| DynamoDB | $0.00 |
| Data Transfer | $1.00 |
| **합계** | **약 $22** |

매장 10개 = 매장당 **약 $2.2/월 = 2,860원/월**.

### 2.3 시나리오 C: 확장 단계 (매장 100개, 본사 5개)

| 서비스 | 월 비용 (USD) |
|---|---|
| EC2 t4g.small | $15.00 |
| Firehose (4.5GB) | $0.13 |
| S3 Standard (300GB) | $7.00 |
| Athena (300GB scanned) | $1.50 |
| Lambda | $0.50 (요청 증가) |
| API Gateway | $1.00 |
| Cognito | $0.00 |
| CloudWatch (15GB) | $7.50 |
| DynamoDB | $0.30 |
| Data Transfer | $5.00 |
| RDS Postgres (전환 시) | $13.00 |
| **합계** | **약 $51** (DynamoDB 사용) 또는 **$64** (RDS 사용) |

매장 100개 = 매장당 **약 $0.51/월 = 660원/월**.

🟢 **결정적**: product_strategy.md 가정의 한계비용 **7.5만원/월** 대비 **약 110배 저렴**.

### 2.4 시나리오 D: 진화 단계 (매장 500개, 본사 20개)

| 서비스 | 월 비용 (USD) |
|---|---|
| EC2 m6g.large (스케일업) | $50.00 |
| Firehose (22GB) | $0.65 |
| S3 Standard (1.5TB) | $35.00 |
| Athena (1.5TB scanned) | $7.50 |
| Lambda | $5.00 |
| API Gateway | $5.00 |
| Cognito | $0.00 |
| CloudWatch (50GB) | $25.00 |
| DynamoDB | $1.50 |
| Data Transfer | $20.00 |
| RDS Postgres (확정 전환) | $13.00 |
| **합계** | **약 $163** |

매장 500개 = 매장당 **약 $0.33/월 = 430원/월**.

### 2.5 시나리오 E: 대규모 단계 (매장 1,000개, 본사 30개)

| 서비스 | 월 비용 (USD) |
|---|---|
| EC2 m6g.large | $50.00 |
| Firehose (45GB) | $1.30 |
| S3 Standard (3TB) | $69.00 |
| Athena (3TB scanned) | $15.00 |
| Lambda | $10.00 |
| API Gateway | $10.00 |
| Cognito | $0.00 |
| CloudWatch (100GB) | $50.00 |
| DynamoDB | $3.00 |
| Data Transfer | $40.00 |
| RDS Postgres | $13.00 |
| **합계** | **약 $261** |

매장 1,000개 = 매장당 **약 $0.26/월 = 340원/월**.

### 2.6 비용 곡선 — 매장당 한계비용

| 매장 수 | 총 월 비용 (USD) | 매장당 (KRW) | product_strategy.md 가정 대비 |
|---|---|---|---|
| 1 | $16 | 21,000원 | 3.6배 저렴 |
| 10 | $22 | 2,860원 | **26배 저렴** |
| 100 | $51 | 660원 | **114배 저렴** |
| 500 | $163 | 430원 | **174배 저렴** |
| 1,000 | $261 | 340원 | **221배 저렴** |

**핵심 발견**: 매장 수 증가 시 단가 급격히 감소 (규모의 경제). 매장 100개 도달 시 product_strategy.md 가정 7.5만원/월 대비 **약 114배 저렴**.

---

## 3. 비용 최적화 옵션

### 3.1 즉시 적용 가능 (PoC 단계)

**옵션 1: Reserved Instance 1년 약정**
- EC2 t4g.small Reserved 1년: 약 30% 할인 → 월 $10.5
- 확신 있을 때 적용 (PoC 6개월 검증 후)

**옵션 2: DynamoDB 대신 RDS 회피**
- 메타데이터 1GB는 DynamoDB 무료 한도 내
- RDS Postgres 월 $13 절감

**옵션 3: HTTP API 사용 (REST API 대신)**
- 70% 저렴, 본 사용 케이스에 충분
- 단, REST API 미세 기능 (사용량 측정 등) 필요 시 REST 유지

**옵션 4: CloudWatch 로그 보존 단축**
- 기본 보존 → 30일 단축
- 매장 100개 시 약 $5 절감

### 3.2 확장 단계 적용 (매장 100+)

**옵션 5: S3 Intelligent-Tiering**
- 90일+ 데이터 자동 IA·Glacier 이동
- 매장 1,000개 S3 비용 $69 → 약 $40 절감 (40%)

**옵션 6: Athena Provisioned Capacity 검토**
- 일 1.92TB+ scanned 시 손익분기
- 매장 5,000개+ 도달 시 검토

**옵션 7: EC2 Spot 인스턴스**
- ETL이 *"실패 시 재시도 가능"* 이므로 Spot 적합
- t4g.small Spot 약 $4/월 (vs On-demand $15)
- 단, Spot 중단 시 ETL 지연 가능성

### 3.3 진화 단계 (매장 1,000+)

**옵션 8: EMR Serverless (Phase 3 진화)**
- 매장 300개+ 도달 시 검토
- 데이터량이 EC2 단일 인스턴스 처리 한계 초과 시

**옵션 9: Multi-region 확장 (글로벌)**
- K-패션 글로벌 진출 시 (안다르 미국·싱가포르 등)
- ap-northeast-2 외 us-east-1 / ap-southeast-1 추가
- Data Transfer 비용 발생

---

## 4. 비용 모니터링 설계

### 4.1 비용 알람 (CloudWatch Billing)

```yaml
알람 임계점:
  - 매장 1개당 월 $30 초과: 경고
  - 매장 1개당 월 $50 초과: 중단 검토
  - 본사 1개당 월 ARPU 대비 비용 30% 초과: 가격 정책 재검토
  - 전체 월 청구 $200 초과 (매장 200개 이하): 비효율 의심
```

### 4.2 비용 추적 태그

모든 AWS 리소스에 태그 부착:
- `store_id`: 매장 식별
- `brand_id`: 본사 식별
- `module`: funnel / flow
- `phase`: 1 / 2 / 3

태그 기반 Cost Explorer 분석으로 매장·본사별 비용 분리 가능.

### 4.3 비용 리포트 자동화

월간 자동 리포트:
- 매장별 비용 + ARPU 대비 마진
- 본사별 비용 + ARPU 대비 마진
- 비효율 매장 식별 (한계비용 평균 초과)

---

## 5. 비용 가정의 검증 우선순위 (PoC Week 1~4)

본 모델의 가정 중 가장 흔들릴 수 있는 5가지:

| 가정 | 위험도 | 검증 방법 |
|---|---|---|
| 매장당 일 1.5MB 데이터 | 🔴 높음 | PoC Week 1 실측 |
| Athena 쿼리 평균 100MB scanned | 🔴 높음 | PoC Week 2 본사 쿼리 패턴 측정 |
| EC2 t4g.small 매장 100개 처리 한계 | 🔴 높음 | PoC Week 3 부하 테스트 |
| Lambda 무료 한도 내 운영 | 🟡 중간 | 매장 50개+ 도달 시 검증 |
| CloudWatch 로그 10~15GB/월 | 🟡 중간 | 매장 30개+ 도달 시 검증 |

위 5개 중 1개라도 가정 2배 초과 시 매장당 한계비용 재계산 필요.

---

## 6. 본 비용 모델의 한계

본 v1 모델은:

- 🔴 모든 비용은 공개 가격표 기반 추정. 실측 0건
- 🔴 매장당 데이터량 (1.5MB/일) 가정의 정밀 검증 부재
- 🔴 Athena 쿼리 패턴 정량 데이터 없음
- 🔴 트래픽 스파이크 시 비용 영향 미반영
- 🔴 글로벌 확장 시 cross-region 비용 미포함

**진짜 사업 시작 시**: PoC Week 1~4 실측으로 v2 모델 갱신. 매장 10~30개 도달 시 v3 모델.

**본 문서 활용 가이드**: 영업 시 *"매장 100개 도달 시 매장당 약 660원/월 운영 비용"* 의 신뢰도 높은 데이터로 활용. CFO 결재 시 비용 시나리오 5종 + 알람 임계점 활용.
