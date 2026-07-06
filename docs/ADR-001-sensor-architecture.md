# ADR-001: 센서 아키텍처 — mmWave + WiFi CSI 하이브리드

- 상태: 승인 (2026-07)
- 결정자: TryOps 기획
- 대체: v1 기획의 "RuView/WiFi CSI 단독" 아키텍처

---

## 컨텍스트

TryOps는 피팅룸 내부의 비영상 행동 신호를 RFID·POS와 융합해 Joint Signal을 생성한다.
v1 기획은 RuView(ruvnet/RuView) 기반 WiFi CSI 단독 센싱을 전제했으나, 다음이 확인됨:

1. **RuView는 비작동 프로젝트.** 독립 기술 감사(3개 AI 교차검증)에서 CSI 파서가 `np.random.rand()` 반환,
   학습 가중치 부재, 성능 수치 조작 확인. HA 커뮤니티·Reddit 실사용자 다수가 동일 증상 보고
   ("항상 presence: true", "랜덤 데이터"). 운영사(Cognitum)는 NDA 없이 사용 사례 제공 거부.
2. **커머디티 CSI의 현실적 한계.** 실사용 검증된 프로젝트(ESPectre, TOMMY, esp-csi)와
   실사용자 증언 기준, 상용 수준으로 되는 것은 존 단위 모션/재실 감지까지.
   정확한 인원 카운트·자세 추정·2D 위치는 연구 단계.
3. **정지 인물 감지 조건.** CSI 기반 정지 재실(호흡 미세움직임)은 ESP32-C5(5GHz)/C6에서 조건부 가능
   (TOMMY 기준: S3 불가). mmWave(24GHz FMCW)는 단일 모듈로 안정적.

## 결정

**역할 분리형 하이브리드:**

| 구역 | 센서 | 역할 |
|---|---|---|
| 피팅룸 내부 | HLK-LD2410C (재실) + 선택적 LD2450 (다중타겟 x/y, 최대 3) | 재실·정지 감지·다중 점유 가능성 — Assistance Need, Companion, Phantom의 원신호 |
| 피팅룸 대기구역·광역 | ESP32-C6 페어 + esp_wifi_sensing | 존 활동 강도 — Fitting Friction, Hesitation 보조 |
| 사물 식별 | RFID (EPC 레벨) | 어떤 옷이 어디에 — 개인 식별 없이 세션 매칭 |

**칩 선택: ESP32-C6** (Espressif 공식 CSI 성능 랭킹: C5 > C6 > C3 ≈ S3 > ESP32).
C5(5GHz 지원)는 Stage 0에서 비교 검증 후 상향 옵션.

**소프트웨어 기반: Espressif esp-csi / esp_wifi_sensing (Apache-2.0)** 위에 자체 알고리즘.

## 검토한 대안

| 대안 | 기각 사유 |
|---|---|
| RuView 기반 | 비작동. 명칭 노출 자체가 실사 평판 리스크 |
| ESPectre 코드 임베드 | GPLv3 — 상용 펌웨어 소스 공개 의무. 알고리즘(MVS/NBVI) 아이디어 참조는 허용, 코드 복사 금지 |
| TOMMY 상용 라이선스 | 클로즈드 코어 종속: 마진 훼손, 기업 실사(에스크로) 대응 불가, 벤더 리스크. 벤치마크 도구로만 사용 |
| CSI 단독 (C5/C6 페어로 정지 감지) | 조건부 가능하나 노드 수·튜닝 부담 대비 mmWave가 피팅룸 소공간에서 압도적으로 단순·확실 |
| mmWave 단독 | 대기구역 광역 커버에 노드 수 증가. CSI는 벽 투과·광역에서 비용 우위. "WiFi 센싱" 포지셔닝(802.11bf 흐름) 유지 가치 |
| 카메라 | 개인정보보호법 제25조 — 피팅룸 설치 불가. TryOps 차별점의 근간이므로 영구 배제 |

## 결과

**긍정적:**
- Joint Signal 6종 전부에 검증된 원신호 확보 (v1에서 유일하게 깨졌던 인원수 의존 제거)
- 라이선스 청정 (Apache-2.0 + 자체 코드) — 기업 실사 대응 가능
- "익명 점유 센서 + 사물 식별 태그" 융합 패턴은 스마트홈 커뮤니티에서 수년간 검증된 구조의 리테일 적용
- 프라이버시 바이 디자인: 1분 집계 윈도우만 보존, raw CSI 비전송 → KIT BFId(CCS 2025) 발 재식별 규제 강화에 선제 대응

**부정적 / 관리 필요:**
- 하드웨어 종류 증가 (ESP32 + mmWave 2종) → 게이트웨이 수신 로직 복잡도 소폭 상승
- mmWave 모듈 KC 전파인증 확인 필요 (Stage 1 전)
- esp_wifi_sensing은 v0.1.x 초기 컴포넌트 → Stage 0 Week 1 게이트로 성숙도 검증, 실패 시 mmWave 단독 폴백
- LD2450 다중타겟은 근접 2인 분리 불가 → Companion은 "가능성 신호"로만 표현 (v1 톤다운 유지)

## 참고 자료

- Espressif esp-csi (Apache-2.0): https://github.com/espressif/esp-csi
- esp_wifi_sensing 데모: examples/esp-radar/wifi_sensing_demo
- RuView 기술 감사: https://github.com/deletexiumu/wifi-densepose
- CMU DensePose from WiFi (연구 근거): https://arxiv.org/abs/2301.00250
- KIT BFId 재식별 연구: DOI 10.1145/3719027.3765062 (CCS 2025)
- IEEE 802.11bf: 2024년 말 비준, 2026 상용 파일럿 단계
- LD2450 스펙: 5~6m, 3타겟, x/y 좌표: https://www.espboards.dev/sensors/ld2450/
