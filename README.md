# TryOps - 오프라인 매장 고객 행동 분석 플랫폼

TryOps는 mmWave 레이더와 Wi-Fi CSI(Channel State Information) 센서, RFID 안테나 신호를 융합하여 오프라인 매장에서 고객의 제품 피팅 및 관심 행동을 측정·분석하는 플랫폼입니다.

피팅룸 내부는 mmWave(재실·정지 감지), 대기구역·광역은 ESP32-C6 기반 Wi-Fi 센싱(Espressif 공식 esp_wifi_sensing, Apache-2.0), 사물 식별은 RFID EPC가 담당하며, 세 신호를 시간축에서 융합해 "고객이 입어봤지만 사지 않은 이유"를 추정합니다. 센서 아키텍처 결정 근거는 `docs/ADR-001-sensor-architecture.md`, v2 전환 지침은 `docs/REDESIGN_MASTER_PLAN.md`를 참고하십시오.

본 리포지토리는 기획 설계 문서, 인프라 구축을 위한 IaC(Terraform), 그리고 각 디바이스 펌웨어 및 클라우드 애플리케이션을 포함하는 모노레포(Monorepo) 구조입니다.

---

## 📂 프로젝트 구조

```
tryops/                              ← 프로젝트 루트
├── docs/                            ← 기획 및 아키텍처 설계 문서
│   ├── REDESIGN_MASTER_PLAN.md      ← v2 센서 아키텍처 전환 지침 (2026-07)
│   │
│   ├── ADR-001-sensor-architecture.md ← mmWave+CSI 하이브리드 결정 (ADR)
│   │
│   ├── planning/                    ← 비즈니스 기획 및 전략 문서 (12개)
│   │   ├── README.md                ← 기획 문서 목차 및 가이드
│   │   ├── product_strategy.md      ← 제품 로드맵 및 시장 진입 전략
│   │   ├── personas_extended.md     ← 페르소나 및 사용자 여정 정의
│   │   ├── market_analysis_detail.md← 리테일 테크 시장 분석 및 포지셔닝
│   │   ├── legal_review.md          ← 개인정보보호법 및 글로벌 규제 검토
│   │   ├── funnel_vs_flow.md        ← 온라인 퍼널-오프라인 플로우 매핑
│   │   ├── roi_model.md             ← 도입 ROI 예측 및 수익 모델
│   │   ├── joint_signals_spec.md    ← 센서-RFID(EPC) 멀티모달 융합 스펙 (v2)
│   │   ├── simulator_spec.md        ← 가상 유저 행동 생성 시뮬레이터 명세
│   │   ├── executive_summary.md     ← 의사결정용 전체 프로젝트 요약
│   │   ├── lessons_learned.md       ← 과거 프로젝트 교훈 및 회고
│   │   ├── planning_playbook.md     ← 기획 프로세스 표준 운영 절차 (SOP)
│   │   └── concept_validation_spec.md← Stage 0 개념 검증 명세서 v2 (CSI/mmWave 병렬)
│   │
│   ├── design_aws/                  ← AWS 아키텍처 설계 (참조용)
│   └── design_gcp/                  ← GCP 아키텍처 설계 (메인)
│
├── infra/                           ← 클라우드 인프라 코드 (GCP IaC)
│   └── terraform/                   ← shared / modules / environments
│
├── apps/                            ← 디바이스 펌웨어 및 애플리케이션 소스 코드
│   ├── store_gateway/               ← 매장 Raspberry Pi 게이트웨이 (Python, mmWave/CSI 융합)
│   ├── esp32_firmware/              ← ESP32-C6 Wi-Fi 센싱 노드 (esp_wifi_sensing 기반 재작성 예정)
│   ├── gcp_ingest/                  ← 실시간 데이터 수집 Gateway (Cloud Run)
│   ├── gcp_etl/                     ← Polars + Airflow 기반 분석/ETL 서비스
│   ├── gcp_query/                   ← 본사/매장 쿼리 API (Cloud Run)
│   ├── web/                         ← MD용 관리 및 분석용 Next.js 대시보드 웹 앱
│   └── stage0_validation/           ← Stage 0 개념 검증 코드 (CSI/mmWave 병렬)
│
├── .gitignore
└── CLAUDE.md                        ← 개발 가이드 및 명령어 규칙
```

---

## 🧭 기술 스택 요약 (v2)

| 레이어 | 기술 | 라이선스 |
|---|---|---|
| 피팅룸 재실·정지 감지 | HLK-LD2410C / LD2450 (24GHz mmWave) | 하드웨어 모듈 |
| 대기구역·광역 활동 감지 | ESP32-C6 + esp_wifi_sensing (Espressif esp-csi) | Apache-2.0 |
| 사물 식별 | RFID (EPC/SGTIN 레벨) | - |
| 융합·신호 알고리즘 | 자체 구현 (Joint Signal 6종) | 자체 IP |
| 클라우드 | GCP (Cloud Run, BigQuery 등, Terraform IaC) | - |

프라이버시 바이 디자인: raw CSI는 게이트웨이 밖으로 전송·보존하지 않으며, 1분 집계 신호만 적재합니다. 개인 식별 정보는 수집하지 않습니다.

---

## 🛠️ 개발 가이드 및 도구 정보

상세 개발 환경 구축 및 로컬 실행 방법은 프로젝트 루트의 `CLAUDE.md` 가이드를 참고해 주시기 바랍니다.

- **클라우드 인프라 배포**: `infra/terraform` 내의 환경 설정을 통해 GCP로 자동 빌드 및 배포할 수 있습니다.
- **개념 검증 (Stage 0)**: `apps/stage0_validation` 코드를 사용하여 H&M Kaggle 데이터셋 및 가상 EPC-센서 매칭 정확도를 시뮬레이션할 수 있습니다. Stage 0 하드웨어(약 6~10만원)와 4주 일정은 `docs/planning/concept_validation_spec.md` 참조.
