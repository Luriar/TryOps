# TryOps - 오프라인 매장 고객 행동 분석 플랫폼

TryOps는 ESP32-S3 기반 Wi-Fi CSI(Channel State Information) 센서와 RFID 안테나 신호를 융합하여 오프라인 매장에서 고객의 제품 피팅 및 관심 행동을 측정·분석하는 플랫폼입니다. 

본 리포지토리는 기획 설계 문서, 인프라 구축을 위한 IaC(Terraform), 그리고 각 디바이스 펌웨어 및 클라우드 애플리케이션을 포함하는 모노레포(Monorepo) 구조입니다.

---

## 📂 프로젝트 구조

```
tryops/                              ← 프로젝트 루트
├── docs/                            ← 기획 및 아키텍처 설계 문서
│   ├── planning/                    ← 비즈니스 기획 및 전략 문서 (12개)
│   │   ├── README.md                ← 기획 문서 목차 및 가이드
│   │   ├── product_strategy.md      ← 제품 로드맵 및 시장 진입 전략
│   │   ├── personas_extended.md     ← 페르소나 및 사용자 여정 정의
│   │   ├── market_analysis_detail.md← 리테일 테크 시장 분석 및 포지셔닝
│   │   ├── legal_review.md          ← 개인정보보호법 및 글로벌 규제 검토
│   │   ├── funnel_vs_flow.md        ← 온라인 퍼널-오프라인 플로우 매핑
│   │   ├── roi_model.md             ← 도입 ROI 예측 및 수익 모델
│   │   ├── joint_signals_spec.md    ← CSI-RFID 멀티모달 센서 융합 스펙
│   │   ├── simulator_spec.md        ← 가상 유저 행동 생성 시뮬레이터 명세
│   │   ├── executive_summary.md     ← 의사결정용 전체 프로젝트 요약
│   │   ├── lessons_learned.md       ← 과거 프로젝트 교훈 및 회고
│   │   ├── planning_playbook.md     ← 기획 프로세스 표준 운영 절차 (SOP)
│   │   └── concept_validation_spec.md← Stage 0 개념 검증 명세서 (H&M Kaggle 활용)
│   │
│   ├── design_aws/                  ← AWS 아키텍처 설계 (참조용)
│   │   ├── README.md                ← AWS 아키텍처 개요 및 5분 요약
│   │   ├── architecture.md          ← AWS 전체 시스템 구성 및 핵심 결정
│   │   ├── data_pipeline.md         ← 실시간 데이터 파이프라인 상세
│   │   ├── infra_cost_model.md      ← AWS 12종 리소스 비용 정밀 추정 모델
│   │   ├── tech_stack_evolution.md  ← 아키텍처의 점진적 진화 로드맵
│   │   ├── security_design.md       ← STRIDE 위협 모델링 및 보안 아키텍처
│   │   ├── devops_setup.md          ← DevOps 모니터링 및 CI/CD 파이프라인
│   │   └── data_governance.md       ← 데이터 보존, 마스킹 및 GDPR 준수 정책
│   │
│   └── design_gcp/                  ← GCP 아키텍처 설계 (메인)
│       ├── README.md                ← GCP 아키텍처 개요 및 5분 요약
│       ├── gcp_architecture.md      ← GCP 기반 시스템 아키텍처 맵핑
│       └── gcp_cost_model.md        ← GCP 리소스 단가 및 비용 정밀 시나리오
│
├── infra/                           ← 클라우드 인프라 코드 (GCP IaC)
│   └── terraform/
│       ├── shared/locals.tf         ← 공통 상수, 리전 및 비용 라벨 정의
│       ├── modules/                 ← GCP 리소스 구축 모듈 (networking, storage, data, compute, api, monitoring, security)
│       └── environments/            ← 환경별 배포 구성 (dev, production)
│
├── apps/                            ← 디바이스 펌웨어 및 애플리케이션 소스 코드
│   ├── store_gateway/               ← 매장 Raspberry Pi 게이트웨이 (Python)
│   ├── esp32_firmware/              ← ESP32-S3 무선 CSI 수집 센서 (C++/ESP-IDF)
│   ├── gcp_ingest/                  ← 실시간 데이터 수집 Gateway (Cloud Run)
│   ├── gcp_etl/                     ← Polars + Airflow 기반 분석/ETL 서비스 (Compute Engine)
│   ├── gcp_query/                   ← 본사/매장 쿼리 API (Cloud Run)
│   ├── web/                         ← MD용 관리 및 분석용 Next.js 대시보드 웹 앱
│   └── stage0_validation/           ← Stage 0 가상 데이터 개념 검증용 코드
│
├── .gitignore
└── CLAUDE.md                        ← 개발 가이드 및 명령어 규칙
```

---

## 🛠️ 개발 가이드 및 도구 정보

상세 개발 환경 구축 및 로컬 실행 방법은 프로젝트 루트의 [CLAUDE.md](file:///c:/Users/HP/OneDrive/바탕%20화면/TryOps/CLAUDE.md) 가이드를 참고해 주시기 바랍니다.

- **클라우드 인프라 배포**: `infra/terraform` 내의 환경 설정을 통해 GCP로 자동 빌드 및 배포할 수 있습니다.
- **개념 검증 (Stage 0)**: `apps/stage0_validation` 코드를 사용하여 H&M Kaggle 데이터셋 및 가상 CSI-RFID 매칭 정확도를 시뮬레이션할 수 있습니다.
