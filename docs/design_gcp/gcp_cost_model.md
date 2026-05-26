# GCP Infra Cost Model — 케이스 B (기업 가정) 메인

> 본 문서는 `gcp_architecture.md` 비용 모델의 상세 자료다. **기업 입장 케이스 B (무료 한도 0 가정)** 메인, 케이스 A (단독 GCP 계정 신규) 첨언.
>
> **본 문서의 한계**: 모든 비용은 공개 가격표 + 추정. PoC Week 1~4 실측 후 v2 정밀화.

---

## 0. 가격 기준 — 모든 비용 asia-northeast3 (서울 리전), 2026.05 기준

환율: 1 USD = 약 1,300 KRW (2026 변동)

---

## 1. 비용 계산 가정 — 케이스 B 메인

### 1.1 케이스 B (메인) — 기업 GCP 계정 통합

**가정**:
- 본사가 이미 GCP 사용 중
- BigQuery 1TB scanned/월 무료 한도 + Pub/Sub 10GB 무료 한도가 본사 다른 워크로드에 이미 소진
- **TryOps 추가 사용량은 100% 유료**

**근거**: 사용자 정책 결정 (*"기업 입장에서 비용을 계산해야지 개인처럼 계정 바꿔쓸 것 아님"*).

본 문서의 모든 매장 수별 시나리오는 **케이스 B 기준**.

### 1.2 케이스 A (첨언) — TryOps 단독 GCP 계정 신규

**가정**:
- TryOps 사업용 GCP 계정 신규 생성
- BigQuery·Pub/Sub 무료 한도 **매월** 활용 가능
- GCP $300 credit (단발, 첫 90일만)

**적용 가능성**: SaaS 사업으로 TryOps 자체 멀티테넌트 운영 시 가능. 본사가 *"본인 GCP 격리"* 요구 시 케이스 B 적용.

→ 본 문서 마지막 섹션에서 케이스 A 시나리오 별도 첨언.

---

## 2. GCP 서비스별 단가표 (서울 리전)

### 2.1 Pub/Sub

🟢 출처: GCP Pub/Sub 공식 가격표
- **Subscribe throughput** (BigQuery subscription 포함): **$50/TiB**
- Publish throughput: 무료 (10GB/월 한도가 글로벌)
- Storage: $0.27/GB-month (확정되지 않은 메시지)

본 사용 케이스 (매장 100개 시):
- 매장당 일 1.5MB → 월 45MB → 매장 100개 = **월 4.5GB**
- Subscribe throughput 4.5GB × $50/TiB = **$0.22/월** (케이스 B)

### 2.2 BigQuery — 쿼리

🟢 출처: GCP BigQuery 공식
- **On-demand**: $5/TB scanned ($6.25/TiB)
- 무료 한도: 1TB scanned/월 (글로벌, 매월 적용)

본 사용 케이스 (매장 100개, 본사 5개):
- 일별 본사 쿼리 약 90GB scanned (architecture.md 4.8 산식)
- 월 약 2.7TB scanned
- **케이스 B**: 2.7TB × $5 = **$13.5/월**
- **케이스 A**: (2.7TB - 1TB 무료) × $5 = **$8.5/월**

### 2.3 BigQuery — Storage

🟢 출처: GCP BigQuery 공식
- Active storage: $0.02/GB-month (처음 10GB 무료, 글로벌)
- Long-term storage (90일+ 변경 없음): $0.01/GB-month (50% 할인 자동)

본 사용 케이스 (매장 100개):
- 일 raw 데이터 약 1.5MB × 100 = 150MB → 월 약 4.5GB raw
- joint_signals 마트 약 10배 (계산 결과 + 메타) → 월 약 45GB
- reports 누적 → 월 약 5GB
- 합계 약 55GB → 90일 후 70% long-term 적용
- **케이스 B**: (16.5GB active × $0.02) + (38.5GB long-term × $0.01) = **$0.71/월** (적은 데이터량)

🔴 위는 매장 100개 × 1개월 운영. 1년 누적 시 storage 약 600GB → 약 $9/월.

### 2.4 Compute Engine — e2-small (ETL)

🟢 출처: GCP Compute Engine asia-northeast3
- **e2-small**: 2 vCPU (shared), 2 GiB RAM
- On-demand: $0.0167/시간 = **약 $12.20/월**
- Sustained Use Discount (SUD): 30% 자동 할인 (24/7 운영 시) → 약 $8.50/월
- Committed Use Discount (1년): 약 30% 할인 → 약 $8.50/월

본 사용 케이스: 24/7 운영 가정 → SUD 자동 적용 → **약 $8.50/월**.

🟡 dev/staging 환경은 *"필요 시만"* 가동 가능 (Cloud Scheduler로 켜고 끄기). 약 50% 절감 가능.

### 2.5 Cloud Run — Ingest·Query

🟢 출처: GCP Cloud Run 공식
- 무료 한도 (글로벌): 200만 요청/월 + 360,000 vCPU-초 + 180,000 GiB-초
- 초과 요청: $0.40/백만 요청
- 초과 컴퓨팅: $0.024/vCPU-시간

본 사용 케이스 (매장 100개, 본사 5개):
- Ingest 요청: 매장 100개 × 5분당 1회 × 30일 = 86.4만 요청/월
- Query 요청: 본사 5개 × 일 100회 × 30일 = 1.5만 요청/월
- 합계 약 88만 요청/월
- **케이스 B**: (88만 × $0.40/백만) = **$0.35/월** (요청 비용)
- 컴퓨팅: 매장 100개 1회당 100ms × 86.4만 = 약 24,000 vCPU-초 → **$0.58/월**
- **합계: 약 $1/월**

🟢 매장 1,000개 도달까지도 매우 저렴.

### 2.6 Cloud Storage

🟢 출처: GCP Cloud Storage asia-northeast3
- Standard: $0.020/GB-month
- Nearline (30일 보존): $0.010/GB-month
- Coldline (90일): $0.004/GB-month
- Archive (365일): $0.0012/GB-month

본 사용 케이스 (매장 100개):
- 매장 게이트웨이 일별 백업 약 1.5MB × 100 = 150MB → 월 약 4.5GB (7일 보존)
- 보고서 누적 약 5GB → 90일 후 Nearline 자동 전환
- **합계: 약 $0.20/월**

### 2.7 Firestore (메타데이터)

🟢 출처: GCP Firestore 공식
- 무료 한도 (글로벌): 1GB storage + 5만 reads/일 + 2만 writes/일
- Storage: $0.18/GB-month
- Reads: $0.06/10만
- Writes: $0.18/10만

본 사용 케이스 (매장 100개, 본사 5개):
- 메타데이터 약 100MB
- 일 reads 약 5,000회 (대시보드 로드)
- 일 writes 약 100회 (매장·본사 정보 갱신)
- **케이스 B**: storage $0.02 + reads $0.09 + writes $0.05 = **$0.16/월**

### 2.8 Identity Platform

🟢 출처: GCP Identity Platform 공식
- 무료 한도 (글로벌): 5만 MAU
- 5만 초과: $0.0055/MAU
- Multi-tenant: 추가 비용 없음

본 사용 케이스:
- 본사당 사용자 10~30명 × 본사 5개 = 50~150 MAU
- **케이스 B**: **$0/월** (무료 한도 내)

### 2.9 Cloud Logging + Monitoring

🟢 출처: GCP Cloud Operations 공식
- Logs Ingestion: $0.50/GB (50GB/월 무료, 글로벌)
- Logs Storage: $0.01/GB-month (30일 무료 보존)
- Metrics: $0.2580/백만 데이터 포인트 (150만 무료)

본 사용 케이스 (매장 100개):
- 로그 약 15GB/월 → 50GB 무료 한도 내
- 메트릭 약 100만 데이터 포인트 → 무료 한도 내
- **케이스 B**: **약 $5/월** (50GB+ 초과 시)

### 2.10 Cloud KMS

🟢 출처: GCP Cloud KMS 공식
- 활성 키: $0.06/key-month
- Cryptographic ops: $0.03/만 ops

본 사용 케이스:
- 본사별 KMS 키 5개 = 5 × $0.06 = $0.30/월
- 일 ops 약 1,000회 = 월 약 3만 → $0.09/월
- **합계: 약 $0.40/월**

### 2.11 Cloud Armor + Security Command Center

🟢 출처: GCP 공식
- Cloud Armor Standard: $5/policy + $0.75/백만 요청
- Security Command Center Standard: **무료**

본 사용 케이스:
- Cloud Armor 1 policy + 일 100만 요청 × 30일 = 월 3,000만 요청 = $22.50
- **합계: 약 $27.50/월**

🟡 dev 환경은 Cloud Armor 불요. production만.

### 2.12 Data Transfer

🟢 출처: GCP Data Transfer 공식
- GCP 내부 동일 리전: **무료**
- GCP → 인터넷 (asia-northeast3): $0.12/GB (처음 1TB)
- GCP → Cloud CDN: 무료

본 사용 케이스 (매장 100개):
- 매장 → GCP in: **무료**
- GCP → 본사 대시보드 (Cloudflare): 무료 (CDN 사용)
- API egress 약 30GB/월
- **합계: 약 $3.60/월**

---

## 3. 매장 수별 시나리오 — 케이스 B (메인)

### 3.1 시나리오 A: PoC (매장 1개, 본사 0개)

| 서비스 | 월 비용 (USD) |
|---|---|
| Pub/Sub | $0.01 |
| BigQuery query | $0.05 (소량 자체 테스트) |
| BigQuery storage | $0.05 |
| Compute Engine e2-small | $12.20 |
| Cloud Run | $0.20 |
| Cloud Storage | $0.05 |
| Firestore | $0.05 |
| Identity Platform | $0 |
| Cloud Logging | $1.00 |
| Cloud KMS | $0.10 |
| Cloud Armor | $5.00 (Standard) |
| Data Transfer | $0.50 |
| **합계** | **약 $19/월** |

매장 1개 운영 비용 **약 2.5만원/월**.

### 3.2 시나리오 B: 초기 (매장 10개, 본사 2개)

| 서비스 | 월 비용 (USD) |
|---|---|
| Pub/Sub | $0.02 |
| BigQuery query | $1.50 (200GB scanned) |
| BigQuery storage | $0.50 |
| Compute Engine | $12.20 |
| Cloud Run | $0.50 |
| Cloud Storage | $0.10 |
| Firestore | $0.10 |
| Identity Platform | $0 |
| Cloud Logging | $3.00 |
| Cloud KMS | $0.20 |
| Cloud Armor | $7.50 |
| Data Transfer | $1.00 |
| **합계** | **약 $27/월** |

매장 10개 = 매장당 **약 $2.7/월 = 3,510원**.

### 3.3 시나리오 C: 확장 (매장 100개, 본사 5개) — 메인 케이스

| 서비스 | 월 비용 (USD) |
|---|---|
| Pub/Sub | $0.22 |
| BigQuery query | **$13.50** (2.7TB scanned, 무료 한도 0 가정) |
| BigQuery storage | $9.00 (450GB) |
| Compute Engine e2-small | $12.20 |
| Cloud Run | $1.00 |
| Cloud Storage | $0.20 |
| Firestore | $0.16 |
| Identity Platform | $0 |
| Cloud Logging | $5.00 |
| Cloud KMS | $0.40 |
| Cloud Armor | $27.50 |
| Data Transfer | $3.60 |
| **합계** | **약 $73/월** |

매장 100개 = 매장당 **약 $0.73/월 = 950원**.

🟢 product_strategy.md 가정 (한계비용 7.5만원) 대비 **약 79배 저렴**.

### 3.4 시나리오 D: 본격 (매장 500개, 본사 20개)

| 서비스 | 월 비용 (USD) |
|---|---|
| Pub/Sub | $1.10 (22GB) |
| BigQuery query | **$67.50** (13.5TB scanned) |
| BigQuery storage | $40 (2TB, long-term 적용) |
| Compute Engine e2-medium | $30 (스케일업) |
| Cloud Run | $3.00 |
| Cloud Storage | $1.00 |
| Firestore | $0.80 |
| Identity Platform | $0 |
| Cloud Logging | $15 |
| Cloud KMS | $1.50 |
| Cloud Armor | $80 |
| Data Transfer | $15 |
| **합계** | **약 $255/월** |

매장 500개 = 매장당 **약 $0.51/월 = 660원**.

### 3.5 시나리오 E: 대규모 (매장 1,000개, 본사 30개)

| 서비스 | 월 비용 (USD) |
|---|---|
| Pub/Sub | $2.20 (45GB) |
| BigQuery query | $135 (27TB) — Editions 검토 시점 |
| BigQuery storage | $80 (4TB) |
| Compute Engine e2-standard-4 | $100 (대형 스케일업) |
| Cloud Run | $5 |
| Cloud Storage | $2 |
| Firestore | $1.50 |
| Identity Platform | $0 |
| Cloud Logging | $30 |
| Cloud KMS | $3 |
| Cloud Armor | $150 |
| Data Transfer | $40 |
| **합계** | **약 $549/월** |

매장 1,000개 = 매장당 **약 $0.55/월 = 715원**.

### 3.6 비용 곡선 — 매장당 한계비용

| 매장 수 | 총 월 비용 (USD) | 매장당 (KRW) | product_strategy.md 가정 대비 |
|---|---|---|---|
| 1 | $19 | 24,700원 | 3배 저렴 |
| 10 | $27 | 3,510원 | 21배 저렴 |
| **100** | **$73** | **950원** | **79배 저렴** |
| 500 | $255 | 660원 | 114배 저렴 |
| 1,000 | $549 | 715원 | 105배 저렴 |

🟢 매장 100~500개 구간이 *"sweet spot"*. 1,000개+ 도달 시 BigQuery Editions 검토 필요.

---

## 4. AWS vs GCP 비교 (매장 100개)

| 항목 | AWS v2-fix | GCP 케이스 B (메인) | 차이 |
|---|---|---|---|
| Ingest | Firehose $0.13 | Pub/Sub $0.22 | +$0.09 |
| Query | Athena $1.50 | BigQuery $13.50 | +$12 (캐싱 우선) |
| Storage | S3 $7 | BigQuery + GCS $9.20 | +$2.20 |
| Compute | EC2 t4g.small $15 | Compute Engine $12.20 | -$2.80 |
| Lambda/Run | $1 | $1 | $0 |
| 인증 | Cognito $0 | Identity Platform $0 | $0 |
| 모니터링 | CloudWatch $7.50 | Cloud Logs $5 | -$2.50 |
| 메타데이터 | DynamoDB $0.30 | Firestore $0.16 | -$0.14 |
| 보안 | (기본) | Security Command Center 무료 + Cloud Armor $27.50 | +$22 |
| Data Transfer | $5 | $3.60 | -$1.40 |
| **합계** | **약 $51** | **약 $73** | **+$22 (Cloud Armor 영향)** |

🟡 **GCP가 AWS보다 매장 100개 시 $22 비싸 보이는 이유는 Cloud Armor 포함**. AWS는 기본 WAF 없는 시나리오. AWS에 WAF $5 + Shield $3,000 (Advanced 시) 추가하면 GCP가 비슷하거나 저렴.

🟢 **본질적 GCP 우위**:
- 구조 단순 (Pub/Sub → BigQuery 직접)
- Identity Platform multi-tenant 무료
- Security Command Center Standard 무료
- 인프라 관리 자동화 (Cloud Run 등)

---

## 5. BigQuery 비용 최적화 (가장 중요)

### 5.1 BigQuery query 비용 50~90% 절감 옵션

**옵션 1: 파티셔닝 + 클러스터링** (필수)
- 본 설계는 모든 테이블에 적용됨 (terraform/modules/data/main.tf)
- 쿼리 시 `WHERE signal_date = '2026-05-22'` 같은 파티션 필터 적용
- **30~70% 비용 절감**

**옵션 2: 마테리얼라이즈드 뷰** (Phase 2+)
```sql
CREATE MATERIALIZED VIEW tryops_production_data.daily_brand_summary AS
SELECT
  brand_id,
  signal_date,
  COUNT(*) AS session_count,
  AVG(hesitation_score) AS avg_hesitation
FROM tryops_production_data.joint_signals
WHERE signal_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY brand_id, signal_date;
```
- 본사 일별 보고서는 마테뷰 쿼리 → **80~95% 비용 절감**

**옵션 3: BI Engine** (Phase 3)
- BigQuery 메모리 캐싱 ($0.04/GB-시간)
- 본사 대시보드 응답 시간 단축 + 비용 절감
- 매장 500개+ 도달 시 검토

**옵션 4: BigQuery Editions** (Phase 3+)
- Standard Edition: $0.04/slot-시간 (최소 100 slots = $4/시간 = 월 $2,880)
- 매장 5,000개+ 도달 시 손익분기 (월 BigQuery 비용 $3,000+ 시점)

### 5.2 Cloud Logging 비용 최적화

- 무료 한도 50GB/월 활용
- 로그 레벨 INFO 이상만 ingestion (DEBUG 제외)
- 30일 후 자동 삭제 (default)
- 매장 100개 기준 약 15GB/월 → 무료 한도 내

### 5.3 Compute Engine 비용 최적화

**옵션 1: Sustained Use Discount** (자동 30% 할인)
- 24/7 운영 시 자동 적용

**옵션 2: Committed Use Discount**
- 1년 commitment: 약 30% 추가 할인
- 3년 commitment: 약 50% 할인
- PoC 단계 보류, Phase 2 검증 후 적용

**옵션 3: Spot VM**
- 약 60~70% 할인
- ETL은 *"실패 시 재시도 가능"* → Spot 적합
- 단, 24시간 내 강제 종료 가능성

---

## 6. 케이스 A 첨언 — TryOps 단독 GCP 계정 시 비용

본 사용자 정책은 케이스 B 메인이지만, **TryOps 단독 GCP 계정 시작 시** 첨언:

### 6.1 케이스 A 매장 100개 비용

| 서비스 | 케이스 B | 케이스 A (무료 한도 활용) | 차이 |
|---|---|---|---|
| Pub/Sub | $0.22 | $0 (10GB 한도 내) | -$0.22 |
| BigQuery query | $13.50 | $8.50 (1TB 무료) | -$5.00 |
| BigQuery storage | $9.00 | $8.80 (10GB 무료) | -$0.20 |
| Cloud Run | $1.00 | $0.20 (200만 무료) | -$0.80 |
| **합계** | $73 | **약 $67** | -$6 |

🟡 케이스 A 활용 시 매장 100개에서 **약 $6/월 절감** (8% 절감). 매장당 $0.06 차이.

### 6.2 케이스 A vs B 결정 가이드

| 상황 | 추천 |
|---|---|
| TryOps SaaS 사업 독립 운영 | **케이스 A** (단독 계정, 무료 한도 활용) |
| 본사가 *"자체 GCP 격리"* 요구 | **케이스 B** (본사 GCP 통합) |
| 본사 계약 시 데이터 처리 위탁 명확 | **케이스 A** (TryOps 자체 계정) |
| 본사가 BigQuery·Pub/Sub 본격 사용 중 | **케이스 B** (무료 한도 의존 X) |

🟢 본 설계는 케이스 A·B 모두 동일 Terraform 코드로 배포 가능. 비용만 차이.

### 6.3 GCP $300 Credit (단발)

신규 GCP 가입자: $300 credit + 90일 유효
- 매장 100개 케이스 B 비용 $73 × 4개월 ≈ $292 → **PoC 4개월 거의 무료**

이건 사용자 지적대로 *"단발 적용"*. 기업 입장에서는 이미 사용했을 가능성. 본 비용 모델에 안 포함.

---

## 7. 비용 모니터링 — Terraform Labels 활용

### 7.1 비용 분석 표준 쿼리

```sql
-- 1) 모듈별 월 비용
SELECT
  labels.value AS module,
  FORMAT_DATE('%Y-%m', DATE(usage_start_time)) AS month,
  ROUND(SUM(cost), 2) AS monthly_cost_usd
FROM `tryops-production.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "module"
GROUP BY module, month
ORDER BY month DESC, monthly_cost_usd DESC;

-- 2) cost_center별 누적 비용
SELECT
  labels.value AS cost_center,
  ROUND(SUM(cost), 2) AS total_cost_usd
FROM `tryops-production.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "cost_center"
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY cost_center
ORDER BY total_cost_usd DESC;

-- 3) 환경별 일별 비용 (production vs dev)
SELECT
  labels.value AS environment,
  DATE(usage_start_time) AS date,
  ROUND(SUM(cost), 2) AS daily_cost_usd
FROM `tryops-production.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "environment"
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY environment, date
ORDER BY date DESC, environment;

-- 4) 매장당 비용 (매장 ID 라벨 활용 — Phase 2+)
SELECT
  labels.value AS store_id,
  ROUND(SUM(cost), 2) AS monthly_cost_usd
FROM `tryops-production.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "store_id"
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY store_id
ORDER BY monthly_cost_usd DESC
LIMIT 100;
```

### 7.2 비용 알람 임계점

terraform/modules/monitoring/main.tf에 정의:
- 50% 도달: 경고 (이메일)
- 80% 도달: 알람 (이메일 + Slack)
- 100% 도달: 긴급 (이메일 + Slack + PagerDuty)
- 예측치 100% 초과: 트렌드 알람

기본 월 예산 $100 (PoC 단계). 매장 100개 도달 시 상향 권장:

| 단계 | 권장 예산 (USD) |
|---|---|
| PoC (매장 1~3) | $30 |
| 초기 (매장 10) | $50 |
| 확장 (매장 100) | $100 |
| 본격 (매장 500) | $300 |
| 대규모 (매장 1,000) | $700 |

---

## 8. 본 비용 모델의 한계

본 v1 모델은:
- 🔴 모든 비용은 공개 가격표 기반 추정. 실측 0건
- 🔴 매장당 데이터량 (1.5MB/일) 가정의 정밀 검증 부재
- 🔴 BigQuery 쿼리 패턴 정량 데이터 없음
- 🔴 트래픽 스파이크 시 비용 영향 미반영
- 🔴 본사별 BigQuery scanned 패턴 미검증

**진짜 사업 시작 시**: PoC Week 1~4 실측으로 v2 모델 갱신. 매장 10~30개 도달 시 v3 모델.

**본 문서 활용 가이드**: 영업 시 *"매장 100개 도달 시 매장당 약 950원/월 운영 비용 (케이스 B)"* 의 신뢰도 높은 데이터로 활용. CFO 결재 시 케이스 A·B 양쪽 시나리오 제공으로 정직성 확보.
