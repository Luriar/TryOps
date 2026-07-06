# Concept Validation Spec v2 — Stage 0 개념 검증 명세 (개정판)

> v1 대비 변경: ① 하드웨어 S3 → C6(+옵션 C5) + mmWave 추가 ② CSI 단독 검증 → CSI/mmWave
> **병렬 비교 검증** ③ CSI 트랙에 타임박스 게이트 ④ 소프트웨어 기반을 esp_wifi_sensing으로 확정.
> Stage 0의 목적(매장 MVP 2~3억 투자 전 본질 검증)과 5종 시나리오 구조는 v1 유지.
> 아키텍처 결정 근거는 `docs/ADR-001-sensor-architecture.md` 참조.

---

## 0. v2 핵심 변경 — 왜 병렬 검증인가

v1은 "CSI 실패 시 mmWave 검토"의 순차 구조였다. 그러나:
- 실사용 증언 기준 커머디티 CSI의 정지 인물 감지는 조건부(C5/C6 + 튜닝)이며 실패 확률이 유의미
- mmWave 추가 비용은 ~3만원에 불과
- 4주 뒤 실패 확인 후 재시작하면 Stage 0가 8주로 늘어남

→ **처음부터 두 센서를 같은 시나리오에 동시 투입**하고, 산출물을 "센서-신호 매핑표"로 바꾼다.
Stage 0의 질문도 바뀐다: v1 "CSI가 되는가?" → v2 **"어느 신호를 어느 센서에서 얻는가?"**

## 1. 환경 구성

### 1.1 하드웨어 (개정 BOM)

| 항목 | 수량 | 예상가 | 용도 |
|---|---|---|---|
| ESP32-C6 DevKit (외장 안테나형 권장) | 2 | 1.6~3만원 | CSI 송수신 페어 |
| ESP32-C5 DevKit (옵션) | 1 | 2~3만원 | 5GHz 성능 상한 확인 |
| HLK-LD2410C | 2 | 0.8~1.4만원 | 재실·정지 감지 |
| HLK-LD2450 | 1 | 1.2~2만원 | 다중타겟 x/y |
| USB-C 케이블·점퍼선 | - | ~1만원 | |
| **합계** | | **약 6~10만원** | v1(3만원) 대비 +3~7만원 |

노트북·공유기는 기존 보유분. mmWave는 UART→USB 어댑터 또는 남는 ESP32에 브리지.

### 1.2 소프트웨어

```
- ESP-IDF ≥ 5.4  (Apache-2.0)
- esp_wifi_sensing 컴포넌트 ≥ 0.1.1  (esp-csi 리포, Apache-2.0)
- wifi_sensing_demo + tools/web_serial_monitor.html (실시간 튜닝)
- Python 3.11: polars, numpy, matplotlib, pyserial(mmWave 파서)
- 가상 RFID/POS: H&M Kaggle 데이터셋 (CC BY 4.0) — v1 합성 방법 유지, epc 필드 추가 합성
- 금지: ESPectre 코드 복사(GPLv3). 알고리즘 아이디어(MVS/NBVI) 참조는 가능
- 참조 전용: TOMMY 무료판 — 벤치마크 비교용, 코드/데이터 미사용
```

### 1.3 실험 배치

v1의 옷장 실험 구조 유지. 추가: mmWave 모듈을 피팅 구역 정면 1.5m, 높이 1.2~1.5m에 설치
(LD2450은 벽면 부착 기준 5~6m/3타겟). CSI 페어와 mmWave가 같은 구간을 동시 관측하도록.

## 2. 검증 시나리오 5종 (구조 유지, 측정 이중화)

각 시나리오를 CSI/mmWave **동시 기록**하고 센서별 정확도를 분리 산출한다.
스크립트: `run_stage0_XX.py --sensor csi|mmwave|both`

| # | 시나리오 | v1 통과 기준 | v2 추가 측정 |
|---|---|---|---|
| 1 | 점유 추정 (빈/정지/움직임) | 80%+ | **정지 인물 구분**을 센서별 분리 채점 — CSI가 여기서 깨질 것으로 예상, mmWave로 커버 확인 |
| 2 | Hesitation 패턴 | 80%+ | 활동 강도 신호원 비교 (CSI vs mmWave 에너지) |
| 3 | Dwell Time (±10초) | 90%+ | mmWave hold_time 파라미터 스윕 (5/15/30s) |
| 4 | Phantom (가상 RFID 매칭) | 80%+ | **Ghost-read 역시나리오 추가**: 옆 공간에 태그 이벤트 주입 → presence 부재로 걸러내는지 |
| 5 | 노이즈 강건성 | 60%+ | 폰 WiFi/BT + 옆방 활동 하에서 센서별 열화 폭 비교 |

**전체 통과 기준 (v2):** 시나리오 1·2를 **센서 조합으로** 통과 + 5종 중 4종 통과.
특정 센서 단독 통과 불필요 — 매핑표가 산출물이다.

## 3. 일정 (4주, 게이트 추가)

**Week 1: 셋업 + 게이트**
- 부품 수령, ESP-IDF 셋업, wifi_sensing_demo 빌드·플래시
- mmWave UART 파서 작성 (LD2410C 프로토콜 단순)
- 🚧 **게이트 G1 (Week 1 종료):** esp_wifi_sensing이 재실 ACTIVE/INACTIVE를 1주 내 재현 못 하면
  → CSI 트랙 중단, mmWave 단독으로 진행 (컴포넌트가 v0.1.x 초기 버전이므로 현실적 가능성 있음.
  이 경우에도 Stage 0는 유효 — 대기구역 신호는 Stage 1에서 재시도)
- 🚧 **게이트 G2:** mmWave가 1일 내 재실 감지 안 되면 배선/모듈 불량 — 교체 (기술 리스크 아님)

**Week 2: 알고리즘 v1 + 시나리오 1·3**
- 1분 집계 윈도우 파이프라인 (polars)
- 시나리오 1(점유)·3(dwell) 실행, hold_time 스윕

**Week 3: 시나리오 2·4·5 + 가상 RFID**
- H&M 합성 (epc 포함), Phantom + Ghost-read 양방향 검증
- 노이즈 시나리오

**Week 4: 결론 + 매핑표**
- 센서-신호 매핑표 확정 (joint_signals_spec §5 실측 갱신)
- Stage 1 진입 판정 (아래 매트릭스)

시간 투자: v1과 동일 (주 15~20시간 × 4주).

## 4. Stage 0 → Stage 1 결정 매트릭스 (개정)

| 결과 | 판정 |
|---|---|
| 조합으로 5종 중 4종+ (1·2 포함) | ✅ Stage 1 진행. 매핑표대로 매장 설계 |
| mmWave만으로 1·3·4 통과, CSI 전멸 | ✅ 진행 가능 — 피팅룸 신호는 확보됨. Friction(대기구역)만 Stage 1에서 재검증. CSI는 광역 옵션으로 강등 |
| mmWave조차 1(점유) 실패 | ❌ 보류 — 배치·모듈 재검토. (가능성 낮음: LD2410 계열은 검증된 상용 부품) |
| 시나리오 2(Hesitation) 실패 | 🟡 신중 진행 — 핵심 동인이 RFID 스왑이므로 사업 치명타는 아님. 활동 강도 가중치 하향으로 알고리즘 조정 |

v1의 "실패 시 mmWave 등 다른 센서 검토" 항목은 병렬 검증으로 흡수되어 삭제.

## 5. 가상 RFID·POS 데이터 (v1 유지 + epc 합성 추가)

- 1차: H&M Personalized Fashion Recommendations (Kaggle, CC BY 4.0) — v1 결정 유지
- 합성 파이프라인 v1 유지 (`synthesize_tryops_data`), 변경점: article_id 기반 가상 SGTIN epc 생성
  (개체 일련번호 랜덤 부여), POS 이벤트에도 동일 epc 전파 — 3단 매칭 로직 검증용
- 한계 명시 v1 유지 + 추가: 가상 epc는 실제 SGTIN 인코딩 체계와 다를 수 있음 (Stage 1 실물 검증)

## 6. 결과물 (v1 유지 + 추가)

- v1 목록(데이터·코드·영업·면접 자산) 유지
- 추가: **센서-신호 매핑표** (Stage 1 매장 설계의 직접 입력)
- 추가: Ghost-read 필터 PoC 결과 (RFID 솔루션사 영업 자료)
- 추가: C5 vs C6 성능 비교 노트 (Stage 1 BOM 결정 근거)

## 7. Stage 1 이월 체크리스트 (Stage 0 범위 아님, 잊지 말 것)

- 🔴 mmWave 모듈 KC 전파인증 — KC 기인증 완제품 소싱 우선, 불가 시 적합성평가 비용 반영
- 🔴 피팅룸 RFID 안테나 오독 대응 — 차폐재/편파/near-field 안테나 설계, 실측 오독률
- 🔴 본사 POS EPC 로그 실재 확인 (인터뷰 1순위 질문)
- 🔴 매장 환경 캘리브레이션 절차 (영업시간 외 기준선 수집 등)

## 8. 본 spec의 한계 (정직성 유지)

- 🔴 esp_wifi_sensing v0.1.x 실빌드 시도 0건 — G1 게이트가 이를 흡수
- 🔴 집 옷장 ≠ 매장 환경 (v1 한계 유지)
- 🔴 mmWave 커튼/합판 투과 특성 미실측 — Week 2에서 피팅 구역 가림막 재질 바꿔가며 확인
- 🔴 H&M 합성 데이터의 epc 필드는 가상 — 실제 EPC 인코딩(SGTIN)은 Stage 1에서 실물 검증
