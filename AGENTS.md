# AGENTS.md — TryOps Project Context for AI Agents

## 본 프로젝트가 무엇인가

**TryOps** — 카메라 없는 피팅룸 인텔리전스 SaaS.

- 매장 측 ESP32-S3 + Raspberry Pi 게이트웨이
- GCP 클라우드 (asia-northeast3 서울 리전)
- 본사 대시보드 (Next.js + Cloudflare Pages)
- 타겟: K-D2C 패션 본사

## 본 프로젝트의 단계

| Stage | 환경 | 비용 | 시간 | 작업 우선순위 |
|---|---|---|---|---|
| Stage 0 | 본인 환경 (옷장) | 3만원 | 4주 | **현재 진행** |
| Stage 1 | 매장 1개 | 1.5~2.5억 | 6개월 | Stage 0 통과 후 |
| Stage 2 | 매장 10~500개 | 5~30억/년 | 1~3년 | 본격 사업 |

## 작업 디렉터리 가이드

| 디렉터리 | 작업 가능 여부 | 비고 |
|---|---|---|
| `docs/` | **읽기 전용** | 기획·설계 문서, 코드 작성 시 참조 |
| `infra/terraform/` | 수정 가능 | GCP IaC, 모듈별 분리 유지 |
| `apps/*/` | 수정 가능 | 각 앱의 README.md 우선 작성 |

## 핵심 설계 결정 (변경 금지)

1. **Pub/Sub → BigQuery 직접 subscription** (Dataflow 불필요)
2. **EC2 t4g.small이 아닌 Compute Engine e2-small** (x86)
3. **모든 GCP 리소스에 비용 추적 라벨 5종 부착**:
   - `project = "tryops"`
   - `environment = "production"|"dev"|"staging"`
   - `module = "data"|"compute"|...`
   - `cost_center = "ingest"|"etl"|"dashboard"|"core"`
   - `managed_by = "terraform"`
4. **서울 리전 (asia-northeast3)** — 한국 본사 신뢰·법규 준수
5. **비용 가정: 케이스 B (기업 GCP 계정 통합, 무료 한도 0)** — 케이스 A는 첨언

## 작업 시 반드시 참조할 문서

- `docs/design_gcp/gcp_architecture.md` — 시스템 아키텍처 메인
- `docs/design_gcp/gcp_cost_model.md` — 비용 모델
- `docs/design_aws/security_design.md` — 보안 위협 모델 (GCP에도 적용)
- `docs/design_aws/data_governance.md` — 데이터 거버넌스
- `docs/planning/concept_validation_spec.md` — Stage 0 진행 시
- `docs/planning/joint_signals_spec.md` — 알고리즘 명세

## 작업 원칙

1. **단순함이 가장 싸다** — Kubernetes·마이크로서비스·다국어 절대 추가 금지
2. **신뢰도 표기 시스템** (🟢/🟡/🔴) 유지 — 가정·검증·실측 명시
3. **모든 코드에 단위 테스트 필수** — pytest (Python), Vitest (Next.js)
4. **변경 시 관련 docs 동기화** — 코드 변경이 설계에 영향 시 docs/design_gcp 업데이트
5. **민감 데이터 금지** — POS 카드번호·전화번호 등 매장 게이트웨이에서 즉시 제거

## 작업 금지 사항

- ❌ AWS 서비스 도입 (본 프로젝트는 GCP 메인)
- ❌ Terraform 외 인프라 도구 (Pulumi·CDK 등)
- ❌ 라벨 없는 리소스 생성
- ❌ 영상·얼굴 인식 (개인정보보호법 제25조 영향)

## 비용 추적 검증

새 GCP 리소스 추가 시 다음 5종 라벨 모두 있는지 확인:
```hcl
labels = merge(local.common_labels, {
  module      = "..."
  cost_center = "..."
})
```

## 자주 묻는 질문

**Q: 매장당 한계비용 목표?**
A: 7.5만원/월 (`docs/planning/roi_model.md`). 실제 본 설계로 약 950원/월 (114배 저렴) 가능.

**Q: 매장 데이터량 가정?**
A: 매장당 일 1.5MB (`docs/design_gcp/gcp_architecture.md` 섹션 4.7 산식 참조). PoC 실측 필수.

**Q: 알고리즘 5종?**
A: Hesitation Score, Assistance Need, Companion Effect, Fitting Friction, Phantom Detection. `docs/planning/joint_signals_spec.md`.
