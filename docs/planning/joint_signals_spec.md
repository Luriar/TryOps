# Joint Signal Specification v2

> v1 대비 변경: ① 센서 레이어를 mmWave+CSI 하이브리드로 교체 ② RFID 이벤트에 EPC 필드 추가,
> Session-POS 매칭을 3단 신뢰도 구조로 ③ 6번째 신호(Ghost-read 필터) 추가
> ④ occupancy_estimate → multi_occupancy_probability 톤다운.
> 아키텍처 결정 근거는 `docs/ADR-001-sensor-architecture.md` 참조.

---

## 0. 적용 범위 (v1 유지)

| 항목 | Funnel Module | Flow Module |
|---|---|---|
| Joint Signal 6종 (본 문서) | ✅ 메인 | ❌ 적용 안 함 |
| 공간 흐름 5종 | 보조 | ✅ 메인 |

---

## 1. 입력 데이터 명세

### 1.1 RFID 이벤트 (변경: epc·rssi 추가)

```json
{
  "store_id": "store_001",
  "fitting_room_id": 3,
  "epc": "urn:epc:id:sgtin:8801234.056789.100000000042",
  "sku_id": "SKU_LEGGINGS_M_BLACK",
  "event_type": "enter",
  "timestamp": "2026-07-06T15:23:45.123+09:00",
  "rssi": -54,
  "metadata": { "category": "leggings", "size": "M", "color": "black", "season": "2026FW" }
}
```

- `epc`: 개체 단위 일련번호(SGTIN). **세션-구매 결정론적 매칭의 열쇠.**
- `rssi`: 인접 피팅룸 오독 필터링용 (임계값 이하 = 오독 후보).
- 🔴 검증 필요: 본사 POS가 EPC 레벨 로그를 남기는지 (Month 1~3 인터뷰 1순위).
  미보유 시 sku_id 시간창 매칭으로 강등 (3단 구조의 2단).

### 1.2 POS 결제 이벤트 (변경: items[].epc 추가)

```json
{
  "store_id": "store_001",
  "transaction_id": "TXN_20260706_1834",
  "timestamp": "2026-07-06T15:42:18.456+09:00",
  "items": [
    { "epc": "urn:epc:id:sgtin:8801234.056789.100000000042",
      "sku_id": "SKU_LEGGINGS_L_BLACK", "quantity": 1, "price": 89000 }
  ],
  "payment_method": "card"
}
```

### 1.3 점유 윈도우 (변경: 센서 융합형으로 재정의)

```json
{
  "store_id": "store_001",
  "zone_id": "fitting_room_3",
  "zone_type": "fitting_room",
  "window_start": "2026-07-06T15:23:00+09:00",
  "window_end": "2026-07-06T15:24:00+09:00",
  "presence": true,
  "presence_source": "mmwave",
  "still_presence": true,
  "activity_score": 0.74,
  "activity_source": "csi",
  "multi_occupancy_probability": 0.15,
  "sensor_health": { "mmwave": "ok", "csi": "ok" }
}
```

변경 요점:
- `presence`(재실)와 `activity_score`(활동 강도) 분리. 피팅룸 재실은 mmWave가 판정(정지 인물 포함).
- `still_presence`: 재실인데 움직임 없음 — Assistance Need의 핵심 원신호.
- `multi_occupancy_probability`: LD2450 타겟 수 기반 0~1 확률. **인원 수 절대값을 산출·표기하지 않는다**
  (v1 Companion 회색지대 원칙 유지).
- 대기구역(zone_type: "waiting_area")은 CSI 단독, `still_presence` 없음.
- 프라이버시 바이 디자인: **raw CSI는 게이트웨이 밖으로 전송·보존하지 않는다.** 1분 집계만 적재.

---

## 2. Try-on Session 정의 (변경: 융합 점유 기반)

### 2.1 Session 생성

```python
def reconstruct_sessions(rfid_events, occupancy_windows, store_id, date):
    """
    v2 변경점:
    1. 점유 구간 판정을 activity_score 임계값(v1: 0.1)이 아니라
       mmWave presence == True 연속 구간으로 정의 (hold_time 15s로 순간 끊김 보정)
    2. RFID 이벤트는 RSSI 필터 + Ghost-read 필터(3.6) 통과분만 사용
    3. 세션 간격 3분 규칙 유지 (보수적 별도 세션)
    """
    sessions = []
    for room_id, events in group_by_room(filter_ghost_reads(rfid_events)).items():
        occ = merge_presence_intervals(occupancy_windows, room_id, hold_time_s=15)
        for interval in occ:
            session_rfid = events_in(events, interval)
            if session_rfid:
                sessions.append(Session(room_id, session_rfid, interval))
    return sessions
```

🔴 hold_time(15s)·세션 간격(3분)은 가설. Stage 0 시나리오 3에서 정밀화.

### 2.2 Session ↔ 구매 매칭: 3단 신뢰도 구조 (신규 — v2 핵심)

| 단계 | 방법 | 신뢰도 | 산출 |
|---|---|---|---|
| 1단 | **EPC 정확 매칭**: 세션에 enter한 EPC가 당일 POS items.epc에 존재 | 결정론 | "입어본 바로 그 옷이 팔림/안 팔림" |
| 2단 | **SKU 시간창 매칭**: 같은 sku_id(또는 동일 스타일 타 사이즈)가 세션 종료 후 30분 내 결제 | 확률 (confidence 부여) | "입어보고 새 상품 집어간 케이스" 커버 |
| 3단 | **SKU 집계**: 일/주 단위 try-on 수 vs 판매 수 | 항상 유효 | high try-on / low conversion SKU 발굴 (MD 핵심 니즈) |

- conversion 라벨은 1단 > 2단 > 3단 순으로 채택하고 `match_tier` 필드에 기록.
- 🔴 2단 시간창(30분)은 가설, PoC 검증.

### 2.3 정확도 검증 (v1 유지 + 추가)

- 정밀도·재현율 90%+ 목표 (PoC Week 2)
- 추가: EPC 매칭 커버리지(전체 세션 중 1단 매칭 비율) 측정 — 영업 문구 결정 근거

---

## 3. Joint Signal 6종

### 3.1 Hesitation Score (변경 미미)

v1 알고리즘 유지. 가중치 입력만 변경: `avg_activity`는 융합 activity_score 사용.
핵심 동인은 여전히 RFID 사이즈 스왑 카운트(0.4) — 센서 교체의 영향 최소.
임계값 가설(0.3/0.6)·검증 방법(전환율 상관, PoC 4주)·비즈니스 활용 전부 v1 유지.

### 3.2 Assistance Need Signal (변경: still_presence 기반)

```python
def calculate_assistance_need(session, current_time):
    """
    v2: '활동 낮음'(CSI, 부재와 혼동)이 아니라
        '재실인데 정지'(mmWave still_presence)를 직접 사용 — 오탐 구조 제거.
    """
    elapsed = (current_time - session.start).total_seconds()
    additional_requests = count_additional_enters(session)
    still_ratio = session.recent_still_presence_ratio(minutes=2)

    if elapsed > 420 and additional_requests == 0 and still_ratio > 0.7:
        return AlertLevel.HIGH
    elif elapsed > 300 and still_ratio > 0.5:
        return AlertLevel.MEDIUM
    return AlertLevel.NONE
```

🔴 임계값(7분/0.7, 5분/0.5)은 가설. 직원 개입 → 전환 +10%p 검증 기준 v1 유지.

### 3.3 Companion Effect (변경: 입력 교체)

v1 로직 유지하되 `multi_occupancy_ratio` → `mean(multi_occupancy_probability)`.
표현 원칙 유지: "동행 가능성 신호"로만. 인원 수 절대값 금지.

### 3.4 Fitting Friction Score (변경 없음)

대기 강도 입력이 대기구역 CSI activity_score라는 점만 명시. 알고리즘·활용 v1 유지.

### 3.5 Phantom Try-on Detection (변경: presence 기반)

트리거를 `activity_score > 0.3`에서 `presence == True and duration > 60s`로 교체
(mmWave 재실이 더 확실). 나머지 v1 유지. 목표 정확도 80%+ 유지.

### 3.6 Ghost-read Filter (신규 — Phantom의 역방향)

**정의**: RFID enter 이벤트가 있는데 해당 피팅룸에 점유가 없음 → 인접 피팅룸 오독 의심.

```python
def detect_ghost_reads(rfid_events, occupancy_windows):
    """
    RFID 실배포 최대 리스크(인접 존 stray read)를 센서 융합으로 필터링.
    1. enter 이벤트 시각 ±30s에 해당 room presence == False → ghost 후보
    2. 같은 EPC가 같은 시각대 인접 room(점유 있음)에서 미검출이면 → 재배정 시도
    3. ghost 확정분은 세션 재구성에서 제외 + RFID 운영팀 알람
    """
```

**비즈니스 활용**: RFID 솔루션사 파트너십 영업 훅 — "귀사 리더의 오독을 우리가 잡아드립니다."
Phantom(누락)과 Ghost(오독)를 묶어 "RFID 데이터 품질 모듈"로 패키징.

🔴 검증: Stage 1 PoC Week 1~2에서 실측 오독률·필터 정확도 측정.
하드웨어 대응(차폐재, 편파, RSSI 임계값)은 Stage 1 설치 가이드에 별도 문서화.

---

## 4. 통합 흐름 (v1 대비 Stage 0.5 추가)

```
[Raw 수집] RFID(epc) + POS(epc) + mmWave/CSI 1분 윈도우
    ↓
[Stage 0.5: 데이터 품질] Ghost-read 필터 + RSSI 필터   ← 신규
    ↓
[Stage 1: Session Reconstruction] presence 기반 + 3단 매칭
    ↓
[Stage 2: 배치 신호] Hesitation / Companion / Friction
    ↓
[Stage 3: 실시간] Assistance Need / Phantom / Ghost 알람
    ↓
[Stage 4~5: 마트 적재 → 대시보드] (v1 유지)
```

---

## 5. 센서-신호 매핑표 (신규)

| 신호 | 1차 센서 | 보조 | 비고 |
|---|---|---|---|
| Session 점유 판정 | mmWave presence | CSI | hold_time 보정 |
| Hesitation | RFID(epc 스왑) | 융합 activity | 센서 의존 최소 |
| Assistance Need | mmWave still_presence | RFID 무요청 | CSI 단독 불가 |
| Companion | LD2450 타겟 수 | RFID 동시성 | 확률 표현만 |
| Friction | 대기구역 CSI | RFID 회전율 | CSI의 주 무대 |
| Phantom | mmWave presence | - | RFID 누락 검출 |
| Ghost-read | mmWave presence 부재 | RSSI | RFID 오독 검출 |

---

## 6. PoC 검증 액션 (v1 구조 유지, 항목 갱신)

- Week 1: 데이터 수집 안정화 + **실측 오독률 측정** (신규)
- Week 2: Session Reconstruction 검증 (정밀도·재현율 90%+, **EPC 커버리지 측정** 신규)
- Week 3: Joint Signal 6종 측정
- Week 4: 비즈니스 임팩트 검증 (high try-on/low conversion SKU 5개+, MD 액션 1개+ — v1 유지)

## 7. 향후 검증 과제 (갱신)

- 🔴 3단 매칭 각 단계 커버리지·정확도 (PoC Week 2)
- 🔴 hold_time·시간창·still_ratio 임계값 (Stage 0 + PoC)
- 🔴 인접 피팅룸 오독률 및 Ghost 필터 정확도 (PoC Week 1~2)
- 🔴 본사 POS EPC 로그 실재 여부 (인터뷰)
- 🔴 매장별 calibration 필요성 (다매장 PoC 시)
- 🔴 Joint Signal ↔ 전환율 상관 (PoC 4주 — 사업 가설 본질)
