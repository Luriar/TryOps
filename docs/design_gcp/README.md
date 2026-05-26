# TryOps GCP Design — README

> 본 README는 TryOps의 **GCP + Terraform** 설계 진입점이다.
>
> AWS 설계 (`/tryops_design/`) 와 동일한 시스템을 GCP에 매핑 + 실제 배포 가능한 Terraform 코드.

---

## 0. 본 GCP 설계가 무엇인가

본 설계는 AWS 설계 v2-fix를 **GCP + Terraform IaC** 로 재구성한 것이다.

**설계 변경 이유** (사용자 결정):
- AWS → GCP로 변경
- Terraform으로 실제 배포 가능한 코드 작성
- 모든 리소스에 비용 추적 라벨 부착 → 실시간 비용 모니터링

**비용 가정**:
- **케이스 B (메인)**: 기업 GCP 계정 통합, 무료 한도 0 가정
- 케이스 A (첨언): TryOps 단독 GCP 계정, 무료 한도 활용

---

## 1. 파일 구조

```
tryops_gcp/
├── docs/
│   ├── gcp_architecture.md  ← GCP 아키텍처 메인 (AWS 매핑)
│   └── gcp_cost_model.md    ← 비용 정밀 모델 (케이스 B 메인)
├── terraform/
│   ├── shared/
│   │   └── locals.tf         ← 공통 라벨·리전·명명 규칙
│   ├── modules/
│   │   ├── networking/       ← VPC + Subnet + Firewall
│   │   ├── storage/          ← Cloud Storage + KMS
│   │   ├── data/             ← Pub/Sub + BigQuery (핵심)
│   │   ├── compute/          ← Compute Engine + Cloud Run
│   │   ├── api/              ← Identity Platform + Artifact Registry
│   │   ├── monitoring/       ← 비용 대시보드 + 알람
│   │   └── security/         ← Secret Manager + Cloud Armor + Audit
│   └── environments/
│       ├── dev/
│       │   └── main.tf       ← 개발 환경 (작은 리소스, 약한 보호)
│       └── production/
│           ├── main.tf       ← 운영 환경 (모듈 통합)
│           └── terraform.tfvars.example
└── README.md (본 파일)
```

---

## 2. 5분 빠른 이해

### 핵심 변경 5가지 (AWS → GCP)

1. **Kinesis Firehose → Pub/Sub + BigQuery 직접 subscription** (Dataflow 불필요, 더 단순)
2. **S3 + Athena → BigQuery 통합** (저장 + 쿼리 한 곳)
3. **EC2 t4g.small → Compute Engine e2-small** (x86, ARM 없음)
4. **Lambda → Cloud Run** (컨테이너 기반, 더 유연)
5. **모든 리소스에 비용 추적 라벨 부착** (Terraform `labels` 표준화)

### 비용 (매장 100개, 케이스 B)

- AWS 설계 v2-fix: 월 $51
- GCP 설계 v1: **월 $73** (Cloud Armor 포함, 동등 보안)
- AWS에 WAF 추가 시 GCP보다 비싸짐 → 본질적으로 GCP가 동등 또는 우수

상세는 `docs/gcp_cost_model.md` 참조.

---

## 3. Terraform 배포 가이드

### 3.1 사전 준비

```bash
# 1. GCP 계정 생성 + 프로젝트 생성
# - tryops-production (운영)
# - tryops-dev (개발)

# 2. gcloud CLI 인증
gcloud auth login
gcloud config set project tryops-production

# 3. 필수 API 활성화 (각 프로젝트에)
gcloud services enable \
  compute.googleapis.com \
  bigquery.googleapis.com \
  pubsub.googleapis.com \
  run.googleapis.com \
  cloudkms.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudbilling.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  identitytoolkit.googleapis.com \
  iap.googleapis.com

# 4. Terraform Service Account 생성
gcloud iam service-accounts create terraform-deploy \
  --display-name "Terraform Deployer"

gcloud projects add-iam-policy-binding tryops-production \
  --member="serviceAccount:terraform-deploy@tryops-production.iam.gserviceaccount.com" \
  --role="roles/editor"

# 5. Terraform state 버킷 생성 (Terraform 실행 전 수동)
gsutil mb -p tryops-production -l asia-northeast3 \
  gs://tryops-production-terraform-state

gsutil versioning set on gs://tryops-production-terraform-state
```

### 3.2 Terraform 실행

```bash
# Dev 환경 먼저 테스트
cd tryops_gcp/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars 편집 (project_id 등)

terraform init
terraform plan
terraform apply

# Production 환경 배포
cd ../production
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars 편집

terraform init
terraform plan
terraform apply
```

### 3.3 Terraform 적용 후 수동 작업

본 Terraform 코드로 자동 안 되는 항목:

1. **Billing Export 활성화** (필수)
   - GCP Console → Billing → Billing Export → BigQuery Export
   - 데이터셋: `billing_export` (Terraform이 생성)
   - "Detailed usage cost data" 체크
   - 24시간 내 첫 데이터 적재

2. **Identity Platform 멀티테넌트 활성화**
   - GCP Console → Identity Platform → Settings → Multi-tenancy
   - 활성화 후 본사별 tenant 생성

3. **Cloud Run 이미지 첫 배포**
   - GitHub Actions 또는 로컬에서:
   ```bash
   docker build -t asia-northeast3-docker.pkg.dev/tryops-production/tryops-production/ingest:latest .
   docker push asia-northeast3-docker.pkg.dev/tryops-production/tryops-production/ingest:latest
   ```

---

## 4. 비용 모니터링 (사용자 요구사항)

### 4.1 자동화된 비용 추적

Terraform이 모든 리소스에 다음 라벨 자동 부착:

```hcl
labels = {
  project     = "tryops"
  environment = "production"  # or "dev", "staging"
  module      = "data"        # 모듈별
  cost_center = "ingest"      # 기능별 (ingest|etl|dashboard|core)
  managed_by  = "terraform"
}
```

### 4.2 비용 분석 쿼리 (BigQuery)

```sql
-- 모듈별 일별 비용 (Billing Export 활성화 후 24시간 후 가능)
SELECT
  labels.value AS module,
  DATE(usage_start_time) AS date,
  ROUND(SUM(cost), 2) AS daily_cost_usd
FROM `tryops-production.billing_export.gcp_billing_export_v1_XXX`,
  UNNEST(labels) AS labels
WHERE labels.key = "module"
  AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY module, date
ORDER BY date DESC, daily_cost_usd DESC;
```

상세 쿼리 예시 5종은 `docs/gcp_cost_model.md` 섹션 7.1 참조.

### 4.3 비용 알람

Terraform이 자동 생성하는 알람:
- 50% 도달 (이메일 경고)
- 80% 도달 (이메일 + Slack — 추가 설정 시)
- 100% 도달 (긴급)
- 예측치 100% 초과 (트렌드)

기본 예산 $100/월 (PoC 단계). 매장 수 증가 시 상향:
- 매장 100개: $100
- 매장 500개: $300
- 매장 1,000개: $700

### 4.4 Cloud Monitoring 대시보드

Terraform이 자동 생성: `tryops-production-cost-dashboard`
- Daily Cost (Last 30 Days)
- Cost by Service
- Pub/Sub Throughput

GCP Console → Monitoring → Dashboards 에서 확인.

---

## 5. 본 GCP 설계의 한계

본 v1 설계는:

- 🔴 실제 GCP 계정 미배포 — Terraform 코드 실행 검증 0건
- 🔴 Pub/Sub BigQuery subscription 실제 latency 미측정
- 🔴 Compute Engine e2-small의 ETL 처리량 미검증
- 🔴 Identity Platform 멀티테넌트 격리 미실측
- 🔴 비용 모델 (케이스 B) 가정의 실측 검증 부재

**진짜 사업 시작 시**: dev 환경 첫 배포 → 1주 운영 → v2 정밀화.

---

## 6. AWS 설계와의 관계

| 항목 | AWS 설계 (`/tryops_design/`) | GCP 설계 (본 문서) |
|---|---|---|
| 시스템 골격 | 동일 | 동일 |
| 컴포넌트 매핑 | AWS 기준 | GCP 매핑 |
| 비용 우선순위 | 매장당 한계비용 최소 | 동일 + 라벨 추적 |
| 보안 | security_design.md | 본 설계 섹션 5 + Terraform |
| Stage 0 | concept_validation_spec.md (GCP 무관) | 동일 (재사용) |
| 데이터 거버넌스 | data_governance.md | Terraform `labels` 자동 부착 |

**Stage 0 (개념 검증)** 은 GCP 무관 — 본인 환경 + ESP32-S3 + 노트북. AWS·GCP 선택은 Stage 1 진입 시점에만 결정.

---

## 7. 활용 가이드

**진짜 사업 시작 시**:
1. AWS vs GCP 최종 선택 (본 GCP 설계 또는 AWS 설계 v2-fix)
2. Stage 0 통과 후 진입
3. Terraform 코드로 자동 배포
4. PoC Week 1~4 실측 → 비용 모델 v2 정밀화

**면접 활용**:
- GCP 매핑 능력 시각화 (AWS와 GCP 양쪽 모두 설계)
- Terraform IaC 실력 입증 (실제 배포 가능한 코드)
- 비용 추적 자동화 설계 (Labels 표준화)

**본 설계의 진짜 가치**: AWS·GCP 양쪽 모두 가능한 *"클라우드 무관 설계 능력"* + Terraform IaC 실력 + 비용 추적 자동화.
