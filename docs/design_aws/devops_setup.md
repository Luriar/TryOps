# DevOps Setup — 테스트·CI/CD·IaC·배포 전략

> 본 문서는 `architecture.md` 시스템을 *"실제로 만들고 운영하는"* 방법을 정의한다. 테스트·CI/CD·IaC·배포·모니터링 전략 통합.
>
> **본 문서의 한계**: 본 v1은 도구·전략 선택까지. 실제 코드·스크립트·파이프라인 설정은 PoC Week 1~4 단계 작성.

---

## 0. DevOps 설계 원칙 5가지

1. **Infrastructure as Code (IaC) 100%** — 콘솔 클릭으로 만든 리소스 0건
2. **모든 배포 자동화** — main 머지 → 자동 배포 (staging) → 수동 승인 → production
3. **테스트 자동화 우선** — 단위·통합·E2E 모두 CI에 통합
4. **관측 가능성 (Observability)** — 로그·메트릭·추적 모두 한 곳
5. ***"가장 싸게"* 원칙 일관 적용** — 비싼 도구 회피 (Datadog·New Relic 등)

---

## 1. 코드 저장소 구조 (Monorepo)

```
tryops/
├── apps/
│   ├── store_gateway/        # Raspberry Pi 게이트웨이 (Python)
│   │   ├── src/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   ├── esp32_firmware/        # ESP32-S3 펌웨어 (C++/ESP-IDF)
│   │   ├── main/
│   │   ├── components/
│   │   └── platformio.ini
│   ├── aws_ingest/           # AWS Ingest Lambda
│   │   ├── src/
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── aws_etl/              # ETL on EC2 (Airflow + Polars)
│   │   ├── dags/
│   │   ├── src/
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── aws_api/              # 본사 대시보드 API Lambda
│   │   ├── src/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── web/                  # 본사·매장 대시보드 (Next.js)
│       ├── src/
│       ├── tests/
│       └── package.json
├── infra/
│   ├── terraform/            # AWS IaC
│   │   ├── modules/
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   └── main.tf
│   └── ansible/              # 매장 게이트웨이 프로비저닝
│       ├── playbooks/
│       └── inventory/
├── shared/
│   ├── proto/                # 매장 ↔ AWS 데이터 스키마 (Protobuf 또는 JSON Schema)
│   └── docs/                 # 기술 문서
├── .github/
│   └── workflows/            # GitHub Actions CI/CD
├── Makefile
└── README.md
```

**Monorepo 선택 이유**:
- 매장 게이트웨이 ↔ AWS Lambda 스키마 변경 시 atomic 변경 가능
- 작은 팀(1~3명)에 monorepo가 단순
- 공통 도구(린트·테스트·CI)통합 쉬움

---

## 2. 테스트 전략

### 2.1 테스트 피라미드

```
              ┌─────────┐
              │   E2E   │  10% (매장 게이트웨이 → AWS → 본사 대시보드)
              └─────────┘
            ┌─────────────┐
            │ Integration │  30% (Lambda + S3, EC2 + Airflow)
            └─────────────┘
          ┌─────────────────┐
          │     Unit        │  60% (Polars 집계, Joint Signal 알고리즘)
          └─────────────────┘
```

### 2.2 단위 테스트 (60%)

**도구**: pytest (Python) + Vitest (Next.js)

**대상**:
- 매장 게이트웨이 1분 집계 로직 (Polars)
- Joint Signal 5종 알고리즘
- AWS Lambda 핸들러 (mocked AWS SDK)
- 본사 대시보드 UI 컴포넌트

**예시**:
```python
# apps/aws_etl/tests/test_joint_signals.py
import polars as pl
from src.signals import calculate_hesitation

def test_hesitation_high_when_size_swap_repeats():
    """같은 SKU 사이즈 반복 입출고 시 Hesitation 0.7+ 기대."""
    df = pl.DataFrame({
        "rfid_event_type": ["enter", "exit", "enter", "exit"],
        "sku_size": ["M", "M", "L", "L"],
        "sku_category": ["leggings", "leggings", "leggings", "leggings"],
        "timestamp_ms": [0, 60000, 120000, 180000],
        "csi_activity": [0.8, 0.7, 0.85, 0.6]
    })
    
    score = calculate_hesitation(df)
    assert score >= 0.7
```

**목표**: 코어 알고리즘 (Joint Signal · Session reconstruction) **80%+ 커버리지**.

### 2.3 통합 테스트 (30%)

**도구**: pytest + LocalStack (AWS 로컬 모킹) + Testcontainers

**대상**:
- Lambda → Firehose → S3 흐름
- EC2 Airflow DAG 전체 실행
- 매장 게이트웨이 → AWS API 전송

**예시**:
```python
# apps/aws_ingest/tests/test_integration.py
def test_ingest_to_firehose(localstack):
    """Ingest Lambda → Firehose → S3 통합 흐름."""
    
    # Given: localstack에 Firehose 스트림 생성
    setup_firehose_stream(localstack, "tryops-ingest")
    
    # When: Lambda 호출
    response = invoke_lambda("aws_ingest", {
        "body": json.dumps(sample_payload)
    })
    
    # Then: S3에 Parquet 적재 확인
    assert response["statusCode"] == 200
    s3_objects = list_s3_objects(localstack, "tryops-data", "raw/")
    assert len(s3_objects) > 0
```

### 2.4 E2E 테스트 (10%)

**도구**: Playwright (UI) + 매장 게이트웨이 시뮬레이터

**대상**:
- 시뮬레이터가 매장 데이터 → 본사 대시보드까지 흐름
- 본사 데이터팀장 시나리오 (Hesitation 발견 → 액션 채택)
- 매장 매니저 시나리오 (Assistance Need 알람 수신)

**실행 주기**: nightly (매일 자정 자동)

### 2.5 부하 테스트

**도구**: Locust 또는 k6

**시나리오**:
- 매장 100개 동시 5분 배치 송신
- 본사 사용자 50명 동시 대시보드 사용
- ETL DAG 매장 100개 데이터 동시 처리

**목표**: SLA 충족 검증 (architecture.md 섹션 7).

---

## 3. CI/CD 파이프라인

### 3.1 도구 선택

- **CI/CD**: GitHub Actions (저장소가 GitHub이라 가장 단순)
- **IaC**: Terraform (멀티 클라우드 가능성 + 한국 시장 표준)
- **Container Registry**: GitHub Container Registry (private 무료)
- **Secrets**: AWS Systems Manager Parameter Store + GitHub Actions Secrets

**왜 다른 도구 안 쓰는가**:
- ❌ Jenkins: 자체 호스팅 비용·운영 부담
- ❌ CircleCI / Travis: 비용 추가
- ❌ AWS CDK: Terraform 학습 곡선이 더 보편적
- ❌ Pulumi: 한국 채용 풀 제한

### 3.2 GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff black mypy
      - run: ruff check apps/
      - run: black --check apps/
      - run: mypy apps/aws_etl/ apps/aws_ingest/
  
  test-python:
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      matrix:
        app: [store_gateway, aws_ingest, aws_etl, aws_api]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e apps/${{ matrix.app }}/[dev]
      - run: pytest apps/${{ matrix.app }}/tests/ --cov --cov-report=xml
      - uses: codecov/codecov-action@v3

  test-web:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd apps/web && npm ci && npm test

  integration-test:
    runs-on: ubuntu-latest
    needs: [test-python, test-web]
    services:
      localstack:
        image: localstack/localstack:latest
        ports: [4566:4566]
    steps:
      - uses: actions/checkout@v4
      - run: pytest apps/*/tests/integration/

  terraform-plan:
    runs-on: ubuntu-latest
    needs: integration-test
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: cd infra/terraform/environments/staging && terraform plan
```

### 3.3 배포 Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.STAGING_DEPLOY_ROLE }}
          aws-region: ap-northeast-2
      - run: cd infra/terraform/environments/staging && terraform apply -auto-approve
      - run: ./scripts/deploy-lambdas.sh staging
      - run: ./scripts/deploy-web.sh staging
  
  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment: production  # GitHub Environment에서 수동 승인 필수
    if: github.event.inputs.environment == 'production'
    steps:
      # ... 동일
```

### 3.4 환경 분리

| 환경 | AWS 계정 | 목적 |
|---|---|---|
| dev | 별도 계정 | 개발자 로컬·테스트 |
| staging | 별도 계정 | E2E 테스트·QA |
| production | 별도 계정 | 실제 본사·매장 운영 |

**AWS Organizations 활용**: 3개 계정을 한 조직으로 관리, 비용·보안 통합.

비용: AWS Organizations 무료, 계정별 별도 청구.

---

## 4. Terraform 구조

```
infra/terraform/
├── modules/
│   ├── networking/         # VPC, subnets, security groups
│   ├── storage/             # S3 buckets, KMS keys
│   ├── compute/             # EC2, Lambda
│   ├── data/                # Firehose, Athena, DynamoDB
│   ├── api/                 # API Gateway, Cognito
│   ├── monitoring/          # CloudWatch, alarms
│   └── security/            # IAM roles, GuardDuty
├── environments/
│   ├── dev/
│   │   ├── main.tf          # 모듈 호출 + 변수
│   │   ├── backend.tf       # S3 backend
│   │   └── terraform.tfvars
│   ├── staging/
│   └── production/
└── shared/
    └── locals.tf            # 공유 상수
```

### 4.1 State 관리

```hcl
# infra/terraform/environments/production/backend.tf
terraform {
  backend "s3" {
    bucket         = "tryops-terraform-state-production"
    key            = "terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "tryops-terraform-locks"
    encrypt        = true
  }
}
```

### 4.2 모듈화 원칙

- 모듈은 *"한 가지 책임"* (Single Responsibility)
- 환경별 차이는 variable로 분리
- 비밀값은 AWS Systems Manager Parameter Store

---

## 5. 매장 게이트웨이 배포 (Ansible)

매장 게이트웨이는 AWS와 별개. Ansible 사용.

```
infra/ansible/
├── playbooks/
│   ├── provision_gateway.yml      # 새 게이트웨이 초기 설정
│   ├── deploy_app.yml             # SW 배포
│   └── rotate_secrets.yml         # API 키 회전
├── roles/
│   ├── system/                    # Ubuntu 22.04 설정
│   ├── docker/                    # Docker 설치
│   ├── tryops_agent/              # 매장 게이트웨이 SW
│   └── monitoring/                # Prometheus node_exporter
└── inventory/
    ├── production.yml             # 매장 IP·접속 정보
    └── staging.yml
```

### 5.1 매장 게이트웨이 OTA 업데이트

```yaml
# OTA 흐름
1. GitHub Actions 빌드 → Docker image → GHCR
2. 매장 게이트웨이가 1시간마다 GHCR 폴링
3. 새 버전 감지 시:
   a. SQLite 백업
   b. 새 컨테이너 시작 (병행)
   c. heartbeat 확인 → 기존 컨테이너 종료
4. 실패 시 자동 롤백
```

### 5.2 매장 게이트웨이 초기 프로비저닝

```yaml
# Ansible playbook
- name: Provision new store gateway
  hosts: new_gateways
  vars:
    store_id: "{{ ansible_user_id_input }}"  # 매장 ID 입력
  tasks:
    - name: Install dependencies
    - name: Setup Docker
    - name: Generate SQLCipher key (매장당 고유)
    - name: Pull tryops_agent image
    - name: Register with AWS (heartbeat 시작)
    - name: Run smoke tests
```

작업 시간: 신규 매장당 약 30분 (자동).

---

## 6. 모니터링·관측 가능성

### 6.1 로그 수집

```
[Application Logs]
- 매장 게이트웨이: stdout → CloudWatch Logs Agent → CloudWatch
- AWS Lambda: stdout → CloudWatch (자동)
- EC2 Airflow: log file → CloudWatch Logs Agent

[Audit Logs]
- CloudTrail: 모든 AWS API 호출
- 본사 사용자 액션: 자체 audit_logs 테이블 (RDS)

[보존 기간]
- Application: 30일
- Audit: 1년
- CloudTrail: 90일 (KMS 암호화)
```

### 6.2 메트릭 (CloudWatch Metrics)

핵심 메트릭:
- 매장당 데이터 적재량 (MB/일)
- API Gateway latency (p50, p95, p99)
- Lambda 실패율
- Athena 쿼리 비용 (일별)
- ETL DAG 성공률

**커스텀 메트릭**:
- 매장 게이트웨이 heartbeat 정상률
- Joint Signal 계산 latency
- 본사 대시보드 응답 시간

### 6.3 알람 (CloudWatch Alarms)

```yaml
Critical (즉시 호출):
  - 매장 게이트웨이 50% 이상 heartbeat 없음 > 5분
  - AWS Lambda 에러율 > 10% > 5분
  - Athena 일별 비용 > $50

Warning (Slack/Email):
  - 매장 게이트웨이 일부 heartbeat 없음 > 30분
  - ETL DAG 실패
  - API latency p99 > 5초 > 10분

Info (Slack):
  - 매장 게이트웨이 OTA 업데이트 진행
  - Athena 쿼리 비효율 패턴 감지
```

### 6.4 대시보드 (Grafana 또는 CloudWatch Dashboard)

비용 우선순위 *"가장 싸게"* 기준:
- **Phase 1·2**: CloudWatch Dashboard 직접 (무료)
- **Phase 3+**: Grafana Cloud Free Tier (10K series 무료) 또는 자체 호스팅

대시보드 3종:
- **운영 대시보드**: 매장 상태·API latency·Lambda 에러
- **비용 대시보드**: 일별·서비스별 비용 추이
- **사업 대시보드**: 매장 수·본사 수·ARR 추적

### 6.5 분산 추적 (Distributed Tracing)

**도구**: AWS X-Ray (Phase 1·2) → OpenTelemetry (Phase 3+)

활용:
- 본사 대시보드 → API Gateway → Lambda → Athena → S3 흐름 추적
- 느린 쿼리 발견
- 에러 발생 지점 정확 파악

비용: X-Ray 첫 10만 trace 무료, 이후 $5/백만 trace.

---

## 7. 개발 환경 (Dev Setup)

### 7.1 로컬 개발 환경

```bash
# 새 개발자 온보딩 30분
git clone https://github.com/tryops/tryops.git
cd tryops
make setup        # Python venv + Node deps + LocalStack 시작
make test         # 모든 단위 테스트
make dev-web      # Next.js 로컬 개발 서버
```

### 7.2 LocalStack 활용

AWS 서비스 로컬 에뮬레이션:
- S3 · Lambda · DynamoDB · Firehose · API Gateway · Cognito
- 로컬 개발 시 실제 AWS 사용 X (비용 0)

```yaml
# docker-compose.yml
version: '3.8'
services:
  localstack:
    image: localstack/localstack
    ports: ["4566:4566"]
    environment:
      - SERVICES=s3,lambda,firehose,dynamodb,apigateway,cognito-idp
```

### 7.3 매장 게이트웨이 시뮬레이터

```python
# apps/store_gateway/simulator.py
"""매장 게이트웨이 시뮬레이션 (개발자 노트북에서)."""

from datetime import datetime
import random

def generate_store_data(store_id, duration_minutes=60):
    """가상 매장 데이터 생성."""
    for minute in range(duration_minutes):
        yield {
            "store_id": store_id,
            "batch_start": ...,
            "csi_aggregates": generate_csi_aggregates(),
            "rfid_events": generate_rfid_events(),
            "pos_events": generate_pos_events()
        }

# 실행: 매장 데이터를 LocalStack API Gateway에 송신
```

---

## 8. 인력·역할 매트릭스

본 시스템 개발·운영에 필요한 역할:

### 8.1 Phase 1 (PoC, 매장 1~3개)

| 역할 | FTE | 시니어리티 | 책임 |
|---|---|---|---|
| Full-stack 엔지니어 | 1.0 | 시니어 | 매장 게이트웨이 + AWS Lambda + 대시보드 |
| 펌웨어 엔지니어 (외주) | 0.3 | 시니어 외주 | ESP32-S3 펌웨어 |
| 데이터 엔지니어 | 0.5 | 미드 | Polars + Joint Signal 알고리즘 |
| **합계** | **1.8 FTE** | | |

월 인건비 (한국 시장 정직 추정):
- 시니어 Full-stack 1.0 FTE: 월 약 800~1,000만원
- 시니어 외주 펌웨어 0.3 FTE: 월 약 300~500만원
- 미드 데이터 0.5 FTE: 월 약 350~500만원
- **합계 월 약 1,450~2,000만원** (보수 1,200 ~ 낙관 2,200)

### 8.2 Phase 2 (매장 10~100개)

| 역할 | FTE | 시니어리티 |
|---|---|---|
| Full-stack 엔지니어 | 2.0 | 시니어 1 + 미드 1 |
| 데이터 엔지니어 | 1.0 | 미드 |
| DevOps · SRE | 1.0 | 시니어 |
| QA · 테스트 자동화 | 0.5 | 미드 |
| **합계** | **4.5 FTE** | |

월 인건비:
- 시니어 1 + 미드 1 Full-stack: 월 약 1,400~1,700만원
- 미드 데이터: 월 약 700~900만원
- 시니어 DevOps: 월 약 1,000~1,300만원
- 미드 QA 0.5 FTE: 월 약 350~500만원
- **합계 월 약 3,450~4,400만원**

### 8.3 Phase 3 (매장 100~500개)

| 역할 | FTE | 시니어리티 |
|---|---|---|
| 백엔드 엔지니어 | 3.0 | 시니어 1 + 미드 2 |
| 프론트엔드 엔지니어 | 2.0 | 미드 |
| 데이터 엔지니어 | 2.0 | 시니어 1 + 미드 1 |
| DevOps · SRE | 2.0 | 시니어 1 + 미드 1 |
| 보안 엔지니어 | 1.0 | 시니어 |
| 펌웨어 엔지니어 | 1.0 | 시니어 |
| **합계** | **11 FTE** | |

월 인건비:
- 백엔드 (시니어 1 + 미드 2): 약 2,300~2,700만원
- 프론트엔드 (미드 2): 약 1,400~1,800만원
- 데이터 (시니어 1 + 미드 1): 약 1,700~2,200만원
- DevOps (시니어 1 + 미드 1): 약 1,700~2,200만원
- 시니어 보안: 약 1,000~1,300만원
- 시니어 펌웨어: 약 900~1,200만원
- **합계 월 약 9,000~1.14억원**

### 8.4 인건비 추정의 한국 시장 검증

🟡 위 추정의 근거:
- 시니어 백엔드 연봉: 약 9,000~1.3억원 (월 750~1,080만원)
- 시니어 DevOps: 약 1억~1.5억원 (월 830~1,250만원)
- 미드 엔지니어: 약 6,000~9,000만원 (월 500~750만원)
- 시니어 외주 (FTE 환산): 약 1,200~1,500만원/월 (계약비)

🔴 본 추정의 한계:
- 한국 IT 시장 시세 2026.05 기준, 변동성 있음
- 시니어/미드 비율은 *"채용 가능성"* 에 의존
- 스톡옵션·복지 비용 제외 (인건비 +20~30% 가능)
- 외주 펌웨어는 *"검증된 인력 확보 가능"* 가정

### 8.5 인플레이션 정정 결과 (v2 셀프리뷰 본질 1 해소)

| 단계 | v2 표기 (인플레이션) | v2-fix 정직 표기 |
|---|---|---|
| Phase 1 월 인건비 | 1,500~2,000만원 | **1,450~2,000만원** (보수~낙관) |
| Phase 2 월 인건비 | 4,000~5,000만원 | **3,450~4,400만원** |
| Phase 3 월 인건비 | 1억~1.2억원 | **9,000~1.14억원** |

전체적으로 v2 표기가 약 5~10% 인플레이션. **본질적 인플레이션은 *"전체 시니어 가정"* 이었던 것** — 시니어/미드 분리하면 약간 정정됨. PoC 1년차 1.5억~2.5억은 여전히 합리적 범위.

🔴 PoC 시작 시점에 실제 채용 시도 후 v3 정밀화 필요.

---

## 9. 비용 영향

DevOps 도구 추가 비용 (매장 100개 기준):

| 항목 | 월 비용 (USD) | 비고 |
|---|---|---|
| GitHub Actions | $0 | 무료 (private 저장소 2,000분/월) |
| Container Registry | $0 | GHCR 무료 |
| LocalStack Community | $0 | 무료 |
| Terraform Cloud | $0 | 5명까지 무료 |
| AWS X-Ray | $1 | 10만 trace 무료 |
| Grafana Cloud Free | $0 | 10K series 무료 |
| Sentry Free (선택) | $0 | 5K events/월 무료 |
| **합계** | **약 $1** | 매장 100개 기준 매장당 무시 가능 |

🟢 본 *"가장 싸게"* 원칙 충실. Phase 3+ 시 일부 유료 전환 검토.

---

## 10. 백업·재해 복구 (DR)

### 10.1 백업 정책

| 데이터 | 백업 방법 | 보존 |
|---|---|---|
| S3 raw | Versioning + 다른 리전 Replication (Phase 3+) | 90일 |
| S3 mart | Versioning | 1년 |
| RDS Postgres | 자동 백업 + Snapshot | 35일 (7일+30일) |
| DynamoDB | Point-in-time Recovery | 35일 |
| 매장 게이트웨이 SQLite | S3에 일별 백업 (암호화) | 7일 |

### 10.2 재해 복구 (RTO/RPO)

| 시나리오 | RTO | RPO | 대응 |
|---|---|---|---|
| Lambda 다운 | <5분 | 0 | 자동 복구 (AWS) |
| EC2 다운 | <30분 | 0 | Auto Scaling + Multi-AZ |
| S3 리전 장애 | <2시간 | <1시간 | Cross-Region Replication (Phase 3+) |
| 본사 데이터 유실 | <4시간 | <24시간 | Versioning + Snapshot 복구 |
| 매장 게이트웨이 분실 | <1일 | 0 | 새 게이트웨이 발송 + S3 백업 복원 |

**RTO**: Recovery Time Objective (서비스 복구 시간)
**RPO**: Recovery Point Objective (데이터 손실 허용량)

### 10.3 DR 훈련

- 분기 1회: 가상 시나리오 DR 훈련
- 연 1회: 실제 staging 환경에서 DR 테스트
- 매 인시던트 후: postmortem + 매뉴얼 업데이트

---

## 11. 운영 (On-call·Incident Response)

### 11.1 On-call 로테이션

- Phase 1·2: 사용자 1인 (24/7 자체 부담)
- Phase 3: SRE 2명 로테이션 (주간 교대)
- Phase 4+: SRE 4~5명 로테이션

### 11.2 On-call 도구

- PagerDuty 또는 Opsgenie (월 $20~30/사용자)
- 또는 단순 SMS/Slack (Phase 1·2)
- CloudWatch Alarms → SNS → On-call

### 11.3 Incident Response 절차

```
[Detection] CloudWatch 알람 또는 사용자 신고
   ↓
[Alert] On-call 호출 (PagerDuty)
   ↓
[Acknowledge] 15분 이내 응답
   ↓
[Investigate] 로그·메트릭·추적 분석
   ↓
[Mitigate] 임시 조치 (롤백·서킷 브레이커 등)
   ↓
[Resolve] 근본 해결
   ↓
[Postmortem] 24시간 이내 (blameless)
   ↓
[Action Items] 재발 방지 작업
```

### 11.4 SLA 모니터링

`architecture.md` 섹션 7 SLA를 실시간 모니터링:

```yaml
SLA 목표:
  - 본사 대시보드 가용성: 99.5% (월 다운타임 3.6시간 허용)
  - API Gateway latency p95: <2초
  - 실시간 알람 전달: <5분 (Firehose 60초 + 알람 처리)
  - 데이터 손실 허용: <0.1%/월

월간 SLA 리포트:
  - 자동 생성, 본사에 공유 (Phase 2+)
  - SLA 미달 시 SLA Credit (예: 다음 달 10% 할인)
```

---

## 12. 향후 검증 과제 (PoC Week 1~4)

본 v1 설계도 다음은 검증 못 함:

- 🔴 GitHub Actions 매장 게이트웨이 OTA 실제 동작
- 🔴 LocalStack의 매장 → AWS 시뮬레이션 정확도
- 🔴 Terraform 모듈 구조의 확장성 (매장 1,000개+ 시)
- 🔴 매장 게이트웨이 OTA 실패 시 자동 롤백 메커니즘
- 🔴 Joint Signal 단위 테스트 커버리지 80% 달성 난이도

---

## 13. 본 DevOps 설계 v1의 한계

본 v1은:
- 🔴 실제 CI/CD 파이프라인 구성 0건 (계획만)
- 🔴 매장 게이트웨이 OTA 실측 0건
- 🔴 인력·인건비 시세 정밀 검증 부재
- 🔴 Terraform 모듈 코드 미작성 (구조만)
- 🔴 모니터링 대시보드 실제 구성 미진행

**진짜 사업 시작 시**: PoC Week 1에 GitHub 저장소 생성 + 기본 CI 설정. Week 2에 LocalStack 통합. Week 3에 Terraform 모듈 초기. Week 4에 staging 환경 가동.

**본 문서 활용 가이드**: 개발자 채용 시 본 문서를 *"우리 DevOps 표준"* 자료로 활용. 외주 펌웨어 엔지니어 계약 시 OTA·테스트 요구사항 명시.
