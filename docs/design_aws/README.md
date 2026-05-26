# TryOps Design — 시스템 설계 단계 README

> 본 README는 TryOps 시스템 설계 단계의 진입점이다.
>
> 본 설계 단계는 **Stage 1 매장 MVP 이후의 시스템**을 다룬다. **Stage 0 (개념 검증)** 은 별도 문서 `concept_validation_spec.md` 참조.

---

## 0. 본 설계 단계가 무엇인가

본 설계는 TryOps 시스템의 **Stage 1·2 (매장 MVP + 확장) 단계** 정밀 설계다. **Stage 0 (개념 검증) 통과 후 진행**.

### 0.1 단계 분리 — Stage 0 vs Stage 1 vs Stage 2

| 단계 | 환경 | 비용 | 시간 | 목적 |
|---|---|---|---|---|
| **Stage 0 — 개념 검증** | 본인 집·옷장 | **약 3만원** | **4주** | 알고리즘 본질 검증 |
| Stage 1 — 매장 MVP | 실제 매장 1개 | 1.5~2.5억원 | 6개월 | 매장 환경 검증 + 본사 영업 |
| Stage 2 — 확장 | 매장 10~500개 | 5억~30억원/년 | 1~3년 | 본격 사업 |

🟢 **Stage 0 우선 진행**. Stage 0 통과 후에만 Stage 1 진입. 본 설계 단계는 Stage 1·2 자료.

### 0.2 설계 목표 (Stage 1·2 한정)

- 목표: Phase 1·2 정밀 설계 (매장 MVP + 확장 단계 한정)
- 검증 깊이: 컴포넌트 다이어그램 + 데이터 흐름 (논리 설계)
- 비용 우선순위: 매장당 한계비용 최소 (확장 시 단가 우선)

### 0.3 진화 단계

- v1: 4개 문서 (1,803줄) — 비용·아키텍처·데이터 흐름·진화 경로
- v2: 7개 문서 (3,905줄) — v1 셀프리뷰 후 보안·운영·거버넌스 추가
- v2-fix: 인건비·통합 위험·보안 비용 정정 + 부하 분산 다이어그램
- **v3 (현재)**: **Stage 0 분리 + concept_validation_spec.md 신규 추가**

---

## 1. 5분 / 15분 / 1시간 읽기 가이드

### 5분 (면접 첫 인상)
1. 본 README 읽기 (2분)
2. `architecture.md` 섹션 0 Executive Summary + 섹션 1 시스템 전체 구성도 (3분)

### 15분 (PM·엔지니어 사고 깊이 확인)
1. 5분 코스 +
2. `architecture.md` 섹션 3 통합 위험 (가장 큰 실패 위험) + 섹션 4 핵심 설계 결정 5가지 (5분)
3. `architecture.md` 섹션 6 비용 모델 (5분)

### 1시간 (전체 시스템 점검)
1. 15분 코스 +
2. `architecture.md` 전체 (15분)
3. `infra_cost_model.md` 매장 수별 시나리오 5종 (10분)
4. `data_pipeline.md` 섹션 1.6·1.7 (ESP32 한계 + HW 비교) + 섹션 5 ETL (15분)
5. `tech_stack_evolution.md` 섹션 6.5 매장 게이트웨이 개발 일정 (5분)

### 깊이 확인 (3~4시간)
- `security_design.md` 전체 (45분)
- `devops_setup.md` 전체 (45분)
- `data_governance.md` 전체 (30분)
- 셀프리뷰 v1·v2 진화 추적 (30분)

---

## 2. 문서 9개의 역할과 연결

```
README (본 문서)
 │
 ├─ concept_validation_spec.md ─ Stage 0 명세 (신규, Stage 1 진입 전 필수)
 │   ├─ 칩 2개 + 가상 RFID 데이터 + 본인 환경 4주
 │   ├─ H&M Kaggle 데이터셋 활용 (CC BY 4.0)
 │   ├─ 5종 검증 시나리오 + 통과 기준
 │   └─ Stage 0 → Stage 1 진입 결정 매트릭스
 │
 ├─ architecture.md ─── 시스템 아키텍처 메인 (883줄)
 │   ├─ 섹션 0: Executive Summary (30초 핵심)
 │   ├─ 섹션 1: 시스템 전체 구성도
 │   ├─ 섹션 2: 핵심 설계 결정 5가지
 │   ├─ 섹션 3: 가장 큰 실패 위험 (통합 부담)
 │   ├─ 섹션 4: 핵심 설계 결정 5가지
 │   ├─ 섹션 5: 데이터 흐름 5단계
 │   ├─ 섹션 6: 비용 모델
 │   ├─ 섹션 7: SLA 5종
 │   ├─ 섹션 8: UI/UX 와이어프레임 3종
 │   ├─ 섹션 9: Phase 진화 트리거
 │   └─ 섹션 10~13: 보안·검증·활용
 │
 ├─ infra_cost_model.md ─── AWS 비용 정밀 모델 (381줄)
 │   ├─ AWS 12종 단가 검증
 │   ├─ 매장 수 5종 시나리오 (1·10·100·500·1,000)
 │   └─ 비용 최적화 옵션 9가지
 │
 ├─ data_pipeline.md ─── 데이터 흐름 상세 (703줄)
 │   ├─ Stage 1~5 처리 로직
 │   ├─ ESP32-CSI 한계 명시 (섹션 1.6)
 │   ├─ Raspberry Pi vs Industrial-grade 비교 (섹션 1.7)
 │   └─ 멀티테넌트 격리 + 재처리 전략
 │
 ├─ tech_stack_evolution.md ─── 진화 경로 (400줄)
 │   ├─ Phase 1~5 진화 단계
 │   ├─ Phase 3 진화 트리거 5가지
 │   ├─ 매장 게이트웨이 SW + 펌웨어 개발 일정 (섹션 6.5)
 │   └─ 진화하지 않을 것 리스트
 │
 ├─ security_design.md ─── 보안 설계 (522줄)
 │   ├─ STRIDE 위협 모델링
 │   ├─ 4가지 P0/P1 위협 + 대응
 │   ├─ 멀티테넌트 격리 5레이어
 │   ├─ 한국 법규 매핑
 │   └─ 보안 비용 정직 추정 (ISMS-P·ISO 27001 포함)
 │
 ├─ devops_setup.md ─── DevOps 운영 설계 (720줄)
 │   ├─ Monorepo 구조
 │   ├─ 테스트 피라미드 (단위 60% / 통합 30% / E2E 10%)
 │   ├─ GitHub Actions CI/CD
 │   ├─ Terraform IaC
 │   ├─ Ansible 매장 프로비저닝
 │   ├─ 모니터링 (CloudWatch + Grafana Free)
 │   ├─ 인력 매트릭스 (시니어/미드/주니어 분리)
 │   └─ DR (RTO/RPO)
 │
 └─ data_governance.md ─── 데이터 거버넌스 (507줄)
     ├─ 데이터 분류 5등급 (L0~L4)
     ├─ 보존 정책 표
     ├─ 삭제 시나리오 4가지
     ├─ 한국 개인정보보호법 + GDPR 매핑
     ├─ DPA 골격
     └─ 감사 운영 체크리스트
```

---

## 3. 본 설계의 5가지 핵심 결정

1. **Kinesis Firehose** (Data Streams 아님) — $0.029/GB, 시간당 비용 없음. 약 220배 저렴
2. **매장 게이트웨이가 데이터 99% 줄임** — Raspberry Pi 4B에서 1분 집계, AWS는 1분당 1KB만 받음
3. **Polars + DuckDB on EC2 t4g.small** — PySpark는 매장 300개+ 도달 시
4. **S3 Parquet + store_id/date 파티셔닝** — Athena 비용 90% 절감
5. **Cloudflare Pages + Lambda + Cognito 무료 한도** — 본사 1,000개까지 무료

---

## 4. 본 설계의 결정적 발견 — 비용 차이 114배

| 매장 수 | product_strategy.md 가정 | 본 설계 v2 | 차이 |
|---|---|---|---|
| 1 | 7.5만원/월 | 21,000원/월 | 3.6배 저렴 |
| **100** | **7.5만원/월** | **약 660원/월** | **114배 저렴** |
| 1,000 | 7.5만원/월 | 340원/월 | 221배 저렴 |

🟢 결정적 발견. 그러나 **PoC Week 1~4 실측 후 v3 정밀화 필수**.

🔴 단, **PoC 총 비용은 AWS만이 아님** — 인건비·HW·법무·인증 포함 1년차 약 1.5~3억원 (architecture.md 섹션 4.6 참조).

---

## 5. 본 설계의 *"가장 싸게"* 원칙

본 설계는 사용자 발화 *"가장 싸게 서비스하고 싶어"* 의 본질적 정합.

**"가장 싸게"의 4가지 본질**:

1. **불필요한 진화 차단** (tech_stack_evolution.md 섹션 5.2)
   - ❌ Kubernetes·마이크로서비스·ElasticSearch·다국어
   - 진화는 *"미리 하지 않음"*

2. **무료 한도 적극 활용** (devops_setup.md 섹션 9)
   - GitHub Actions·LocalStack·Terraform Cloud·Grafana Cloud Free
   - Cognito·Lambda·API Gateway 무료 한도 (본사 1,000개까지)

3. **매장 게이트웨이가 데이터 99% 줄임** (architecture.md 섹션 4.2)
   - Kinesis Firehose 비용 무시 수준
   - S3 적재 비용 최소

4. **단순 아키텍처 유지** (architecture.md 섹션 4.3·4.5)
   - Polars + DuckDB on EC2 단일 인스턴스
   - 복잡도 = 비용 (인건비 + 운영 비용)

---

## 6. 본 설계의 가장 큰 위험 3가지

`architecture.md` 섹션 3 + 셀프리뷰 v2 본질 비판.

**위험 1: 외부 시스템 통합 부담 누적**
- RFID·POS·ERP 통합이 누적 10~30개월 추가 작업 가능
- PoC 1년차 1.5억 → 실제 3~5억 가능성

**위험 2: ESP32-CSI 매장 환경 정확도**
- 매장 실측 검증 0건
- 정확도 50~70% 가능성 시 매장당 노드 수 재설계 필요

**위험 3: 보안 인증 비용 과소평가**
- ISMS-P 약 5,000만~1억원
- ISO 27001 약 3,000~7,000만원
- Phase 3 도달 시 누적 1억~2.5억원

---

## 7. 셀프리뷰 진화 — 점수가 떨어지는 게 정직

| 단계 | 평균 점수 | 주요 변화 |
|---|---|---|
| v1 | 49 | 비용·아키텍처 강함, 보안·운영·UI 부재 |
| v2 | 78 | 11개 비판 해소, 신규 3개 문서 |
| v2 셀프리뷰 정직 | 72 | 인건비 인플레이션·통합 위험·보안 비용 정정 |
| **v2-fix (현재)** | **약 76** | 본질 3개 + 형식 4개 해소 |

---

## 8. 본 설계의 한계 — 정직 명시

본 v2-fix는:
- 🔴 실제 AWS 계정 미생성, 모든 비용 공개 가격표 + 추정
- 🔴 매장당 데이터량 1.5MB/일 가정 미검증
- 🔴 ESP32-S3 매장 환경 정확도 미검증
- 🔴 Polars 1분 집계 처리 시간 미실측
- 🔴 셀메이트·토스플레이스 통합 실측 0건
- 🔴 한국 법무법인 정식 의견서 미확보
- 🔴 KISA·ISMS-P 사전 검토 미진행

진짜 검증은 **PoC Week 1~4** 단계.

---

## 9. PoC Week 1~4 검증 우선순위 (통합 매트릭스)

본 설계의 6개 문서 *"향후 검증 과제"* 통합 우선순위:

### 9.1 P0 검증 (Week 1, 절대 필수)

| # | 검증 항목 | 위치 | 영향 |
|---|---|---|---|
| 1 | 매장당 데이터량 1.5MB/일 실측 | architecture.md 4.7 | 전체 비용 모델 |
| 2 | ESP32-S3 매장 환경 정확도 측정 | data_pipeline.md 1.6 | 시스템 도입 결정 |
| 3 | 매장 → AWS 전송 성공률 99.5%+ | architecture.md 7 | SLA 충족 |
| 4 | Firehose 60초 버퍼링 실제 latency | architecture.md 5 | 실시간 알람 가능성 |

### 9.2 P1 검증 (Week 2, 핵심)

| # | 검증 항목 | 위치 | 영향 |
|---|---|---|---|
| 5 | 셀메이트 RFID webhook 통합 (1개) | architecture.md 3 | 시나리오 A 가능성 |
| 6 | 토스플레이스 POS API 통합 (1개) | architecture.md 3 | 시나리오 B 가능성 |
| 7 | Polars 1분 집계 처리 시간 | data_pipeline.md 2 | EC2 사이즈 |
| 8 | Session Reconstruction 정확도 90%+ | joint_signals_spec.md | Joint Signal 5종 |

### 9.3 P2 검증 (Week 3~4, 중요)

| # | 검증 항목 | 위치 | 영향 |
|---|---|---|---|
| 9 | Hesitation Score conversion 상관관계 | joint_signals_spec.md | 알고리즘 v2 |
| 10 | Athena 쿼리 패턴 실측 | architecture.md 4.8 | 캐싱 전략 |
| 11 | 매장 게이트웨이 OTA 1회 시도 | devops_setup.md 5 | 운영 가능성 |
| 12 | SQLCipher 성능 영향 측정 | security_design.md 2.2 | 매장 게이트웨이 부하 |
| 13 | 본사 MD 회의 액션 1개 채택 | architecture.md 11 | 비즈니스 가치 |

### 9.4 P3 검증 (Pilot 5~12주, 보강)

| # | 검증 항목 | 위치 | 영향 |
|---|---|---|---|
| 14 | A/B 테스트 사이즈 가이드 효과 | roi_model.md 7.2 | ROI 모델 v2 |
| 15 | 매장 매니저 본인 대시보드 활용도 | architecture.md 8.3 | 강희정 페르소나 검증 |
| 16 | 매장 손님 거부감 비율 | personas_extended.md 5 | 76.2% 가설 |
| 17 | KISA 외부 침투 테스트 1회 | security_design.md 8 | 보안 자산 |

총 **17개 P0~P3 검증 과제**. PoC 1년차 핵심 작업.

---

## 10. 본 설계 활용 가이드

**진짜 사업 시작 시**:
1. AWS 계정 생성 + ap-northeast-2 리전 설정
2. 매장 게이트웨이 1대 준비 (Raspberry Pi 4B 8GB 약 16만원)
3. ESP32-S3 노드 6개 알리에서 구매 (약 5~7만원)
4. `architecture.md` 본문대로 PoC 1매장 구축 (예상 약 1~2주)
5. Week 1~4 P0·P1 검증 (본 README 섹션 9)
6. 실측 데이터로 v3 설계 갱신

**면접 활용**:
- 시스템 설계 답변 시 `architecture.md` 다이어그램 활용
- 매장당 한계비용 114배 절감의 핵심 결정 (Firehose, 매장 집계 99% 절감) 강조
- 본 설계의 가장 큰 위험 (통합 부담·ESP32 정확도·보안 비용) 솔직 인정
- 셀프리뷰 v1·v2 진화로 PM 사고 깊이 시각화

**본사 영업 시**:
- 본 설계 + roi_model.md + legal_review.md 패키지 제출
- SLA 5종 + 보안 위협 4가지 대응 + 데이터 거버넌스 5등급 분류
- 본사 보안·법무 검토 4~8주 예상

---

## 11. 본 README 활용

다음 기획·설계 시:
- `planning_playbook.md` 단계 7 마무리 산출물 (README) 의 실제 예시
- 본 README 구조를 그대로 차용해 다음 프로젝트에 적용 가능

본 설계 단계가 *"실제 사업 시작 시 동일 프로세스 재사용"* 의 핵심 자산.
