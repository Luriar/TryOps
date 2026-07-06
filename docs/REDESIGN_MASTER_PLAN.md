# TryOps 재설계 마스터 플랜 (v2 전환 가이드)

> 2026-07 센서 아키텍처 재설계에 따른 리포 전체 전환 지침.
> 배경: RuView(ruvnet/RuView)가 비작동 AI 생성 프로젝트로 판명됨에 따라
> 센서 레이어를 mmWave + Espressif 공식 WiFi 센싱 하이브리드로 교체.
> 사업 구조(가격·GTM·ROI·법적 우위)는 변경 없음.

---

## 0. 핵심 결정 요약

| 항목 | 기존 (v1) | 변경 (v2) |
|---|---|---|
| 기술 근거 | RuView | Espressif esp_wifi_sensing + CMU DensePose 논문 + IEEE 802.11bf |
| 센서 칩 | ESP32-S3 | ESP32-C6 (옵션: C5) — 공식 CSI 랭킹 C5 > C6 > S3 |
| 피팅룸 내부 센서 | WiFi CSI 단독 | mmWave 1차 (LD2410C 재실 + LD2450 다중타겟) + CSI 보조 |
| 대기구역/광역 | WiFi CSI | ESP32-C6 페어 + esp_wifi_sensing (유지, 칩만 변경) |
| RFID 스키마 | sku_id | **epc 필드 추가** — EPC 우선 3단 매칭 |
| Joint Signal | 5종 | 6종 (RFID Ghost-read 필터 추가) |
| 인원 수 표현 | occupancy_estimate | multi_occupancy_probability (톤다운) |
| 라이선스 전략 | 미정 | Apache-2.0 스택(esp-csi/ESP-IDF) + 자체 알고리즘. ESPectre(GPLv3) 코드 사용 금지, TOMMY(클로즈드) 벤치마크 전용 |
| 포지셔닝 | "CSI 기술 우위" | "센서 불가지론적 비영상 행동 신호 플랫폼 + 프라이버시 바이 디자인" |

---

## 1. 파일별 처리 지침

### 1.1 삭제 없음 원칙
전면 삭제 대상 디렉토리는 없다. 유일한 전면 재작성은 `apps/esp32_firmware`.

### 1.2 docs/planning — 수정

| 파일 | 작업 | 상태 |
|---|---|---|
| executive_summary.md | RuView 문구 전량 교체. 차별점에 802.11bf 표준화·시장 전망 추가. "CSI 기술 우위(RuView 기반)" → "검증된 융합 알고리즘 + EPC 조인 레이어" | 반영 |
| joint_signals_spec.md | v2로 교체 | 반영 |
| concept_validation_spec.md | v2로 교체 | 반영 |
| product_strategy.md | RuView 참조 교체, 6번 신호(Ghost-read) 추가 | 반영 |
| legal_review.md | RuView 참조 교체 + 추가: ① KIT BFId(CCS 2025) 발 규제 강화 대비 "집계 신호만 보존" 원칙 ② mmWave KC 전파인증 | 반영 |
| lessons_learned.md | RuView 사례 교훈 추가 (오픈소스 채택 검증 기준) | 반영 |
| market_analysis_detail.md | RuView 참조 교체, 802.11bf 시장 데이터 | 반영 |
| roi_model.md | 매장당 BOM에 mmWave 추가(영향 미미), RFID 차폐 설계 비용 | 후속 |
| 나머지 | RuView 문자열 없음 확인 | 완료 |

### 1.3 docs — 신규
- `ADR-001-sensor-architecture.md` (센서 아키텍처 결정 기록)
- 본 문서

### 1.4 infra/terraform — 유지 (변경 없음)

### 1.5 apps — 부분 수정 (후속 작업)

| 디렉토리 | 작업 |
|---|---|
| esp32_firmware/ | **전면 재작성.** ESP32-C6, ESP-IDF ≥5.4, esp_wifi_sensing(≥0.1.1) 기반. 기존 S3 코드는 legacy 브랜치 보존 후 제거. 신규: ① wifi_sensing FSM ② mmWave UART 브리지 ③ MQTT 1분 집계 발행 (raw CSI 비전송) |
| store_gateway/ | mmWave 이벤트 수신, CSI/mmWave 융합 점유 판정, hold_time 파라미터 |
| gcp_ingest/ | 스키마에 epc, sensor_type, multi_occupancy_probability 추가 |
| gcp_etl/ | Session Reconstruction EPC 우선 3단 매칭, Ghost-read 필터 배치 |
| gcp_query/, web/ | 신규 필드 노출, Ghost-read 알람 위젯 |
| stage0_validation/ | 입력 소스 CSI/mmWave 이중화, `--sensor csi|mmwave|both` 인자, 센서별 정확도 분리 |

### 1.6 전역 문자열 정리
```bash
grep -rn -i "ruview\|densepose\|ruvnet" --include="*.md" --include="*.py" --include="*.ts" --include="*.tsx" .
```
기술 언급 → "WiFi 센싱(Espressif esp_wifi_sensing)", 논문 인용 → CMU DensePose from WiFi(arXiv:2301.00250, 연구 근거로만).

---

## 2. 작업 순서

1. **Week 0 (문서):** 본 커밋으로 완료
2. **Week 0 (부품 주문):** ESP32-C6 ×2, (옵션) C5 ×1, LD2410C ×2, LD2450 ×1 — 약 6~10만원
3. **Week 1~4 (Stage 0):** concept_validation_spec.md v2 일정 따름
4. **펌웨어 재작성은 Stage 0 Week 1 게이트(G1) 통과 후 착수**

---

## 3. 검증 잔여 항목 (🔴)

- 🔴 본사 POS가 EPC 레벨 로그를 남기는지 (Month 1~3 인터뷰 1순위 — "결정론적 매칭" 영업 문구 사용 가능 여부)
- 🔴 esp_wifi_sensing v0.1.x 성숙도 (Stage 0 Week 1 게이트 G1)
- 🔴 RFID 인접 피팅룸 오독률 (Stage 1 PoC Week 1~2 실측)
- 🔴 mmWave 모듈 KC 인증 상태 (Stage 1 전 소싱 확인)
- 🔴 Joint Signal ↔ 전환율 상관관계 (PoC 4주 — 사업 가설의 본질)
