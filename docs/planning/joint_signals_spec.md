# Joint Signal Specification

> 본 문서는 `product_strategy.md` 섹션 10 Joint Signal 5종의 알고리즘 명세 골격이다. 데이터 엔지니어·ML 엔지니어가 Phase 1 시뮬레이션 데이터로 알고리즘 구현 시 참조.
>
> **본 문서의 한계**: 실제 RuView·CSI 신호 데이터 없이 알고리즘 검증 불가. 본 명세는 알고리즘 골격 + 임계값 가설 + 검증 방법. PoC 단계에서 실측으로 정밀화.

---

## 0. 본 문서의 적용 범위

| 항목 | Funnel Module | Flow Module |
|---|---|---|
| Joint Signal 5종 (본 문서) | ✅ 메인 | ❌ 적용 안 함 |
| 공간 흐름 5종 | 보조 | ✅ 메인 |

본 문서는 Funnel Module 전용 Joint Signal 5종에 집중. Flow Module의 공간 흐름 5종은 별도 문서 예정.

---

## 1. 입력 데이터 명세

### 1.1 RFID 이벤트

```json
{
  "store_id": "store_001",
  "fitting_room_id": 3,
  "sku_id": "SKU_LEGGINGS_M_BLACK",
  "event_type": "enter",  // "enter" or "exit"
  "timestamp": "2026-05-22T15:23:45.123+09:00",
  "metadata": {
    "category": "leggings",
    "size": "M",
    "color": "black",
    "season": "2026SS"
  }
}
```

### 1.2 POS 결제 이벤트

```json
{
  "store_id": "store_001",
  "transaction_id": "TXN_20260522_1834",
  "timestamp": "2026-05-22T15:42:18.456+09:00",
  "items": [
    {"sku_id": "SKU_LEGGINGS_L_BLACK", "quantity": 1, "price": 89000}
  ],
  "payment_method": "card",
  "anonymous_member_id": "hashed_id_xxx"  // 선택, 가명처리
}
```

### 1.3 CSI 활동 윈도우

```json
{
  "store_id": "store_001",
  "fitting_room_id": 3,
  "window_start": "2026-05-22T15:23:00+09:00",
  "window_end": "2026-05-22T15:24:00+09:00",
  "activity_score": 0.74,
  "occupancy_estimate": 1,
  "movement_pattern": "moderate"
}
```

CSI 윈도우는 1분 단위. activity_score는 0~1 정규화 값.

---

## 2. Try-on Session 정의

여러 RFID enter/exit 이벤트 + CSI 윈도우를 결합한 *"한 명의 손님이 피팅룸에서 시도한 단일 세션"*.

### 2.1 Session 생성 알고리즘

```python
def reconstruct_sessions(rfid_events, csi_windows, store_id, date):
    """
    Try-on session 재구성 알고리즘 골격.
    
    1. 동일 fitting_room_id의 RFID 이벤트 시간순 정렬
    2. CSI 윈도우와 시간축 결합
    3. CSI activity > 임계값(0.1) 구간을 "점유 구간"으로 정의
    4. 점유 구간 안의 RFID enter/exit 이벤트를 한 세션으로 묶음
    5. 점유 구간 종료 후 3분 이내 새 enter 이벤트는 동일 손님 가능성 (보수적으로 별 세션)
    """
    # 가설: 점유 구간 정의 임계값 0.1, 세션 간격 3분
    # PoC 검증 필요
    sessions = []
    for room_id, events in group_by_room(rfid_events).items():
        occupancy_windows = identify_occupancy(csi_windows, room_id, threshold=0.1)
        for window in occupancy_windows:
            session_rfid = [e for e in events if window.start <= e.timestamp <= window.end]
            if session_rfid:
                sessions.append(Session(
                    store_id=store_id,
                    fitting_room_id=room_id,
                    rfid_events=session_rfid,
                    csi_window=window,
                    duration=window.end - window.start
                ))
    return sessions
```

🔴 점유 구간 임계값(0.1)·세션 간격(3분)은 모두 가설. PoC 시 RFID-CSI 시간축 매칭 정확도 검증 후 조정.

### 2.2 Session 정확도 검증

PoC Week 2 검증 항목:
- 정밀도(Precision): RFID enter/exit이 같은 손님인지
- 재현율(Recall): 손님 입실 누락 비율
- 목표: 정밀도·재현율 90%+

---

## 3. Joint Signal 5종 알고리즘 명세

### 3.1 Hesitation Score

**정의**: 같은 SKU 또는 같은 카테고리의 다른 사이즈가 한 세션 안에서 반복 입출고되는 동안 CSI 활동 강도가 높게 유지되는 정도.

**알고리즘 골격**:

```python
def calculate_hesitation_score(session):
    """
    Hesitation Score 알고리즘.
    
    1. 세션 안의 RFID 이벤트 분석
    2. 같은 SKU의 다른 사이즈 반복 입출 카운트
    3. 세션 duration vs CSI activity 평균
    4. 가중치 적용해 0~1 점수 반환
    """
    same_category_size_changes = count_size_swaps(session.rfid_events)
    avg_activity = mean(session.csi_window.activity_score)
    duration_factor = min(session.duration / 600, 1.0)  # 10분 기준 정규화
    
    score = (
        0.4 * normalize(same_category_size_changes, max=5) +
        0.3 * avg_activity +
        0.3 * duration_factor
    )
    return score  # 0~1
```

**임계값 가설** (🔴 PoC 검증 필요):
- 0.0 ~ 0.3: 낮은 망설임 (빠른 결정)
- 0.3 ~ 0.6: 중간 망설임 (일반적)
- 0.6 ~ 1.0: 높은 망설임 (구매 실패 원인 후보)

**검증 방법**:
- PoC 매장 3개에서 4주간 측정
- Hesitation Score와 conversion(구매/미구매)의 상관관계 분석
- 0.6+ 세션의 conversion rate가 0.0~0.3 세션 대비 통계적으로 낮은지 확인

**비즈니스 활용**:
- 본사 MD: high try-on / low conversion SKU 발견 → 사이즈 가이드 개선
- 매장 매니저: 사이즈 비교 행동 빈도 → 사이즈 차트 검증

### 3.2 Assistance Need Signal

**정의**: 입실 후 일정 시간 경과, 추가 사이즈/색상 요청 RFID 이벤트 없음, CSI 활동 강도 중간 이하 → 고객이 도움 필요하지만 호출 못 하는 상태 후보.

**알고리즘 골격**:

```python
def calculate_assistance_need(session, current_time):
    """
    Assistance Need 실시간 알람.
    
    1. 입실 후 경과 시간 측정 (current_time - session.start)
    2. 입실 후 추가 RFID enter 이벤트 카운트 (0이면 도움 필요 가능성)
    3. 최근 1분 CSI activity (낮으면 정체)
    4. 임계값 충족 시 알람
    """
    elapsed = (current_time - session.start).total_seconds()
    additional_requests = count_additional_enters(session, after=session.start)
    recent_activity = session.csi_window.recent_activity(minutes=1)
    
    if elapsed > 420 and additional_requests == 0 and recent_activity < 0.3:
        return AlertLevel.HIGH
    elif elapsed > 300 and recent_activity < 0.5:
        return AlertLevel.MEDIUM
    return AlertLevel.NONE
```

**임계값 가설** (🔴 PoC 검증 필요):
- 입실 후 5분 + 활동 강도 0.5 미만 → 중간 알람
- 입실 후 7분 + 활동 강도 0.3 미만 → 높은 알람

**검증 방법**:
- PoC 매장 직원에게 알람 발생 시 응대 시도 권장
- 알람 발생 세션의 구매 전환율 vs 미발생 세션 비교
- 직원 개입 후 구매 전환 +10%p 이상 시 알고리즘 유효

**비즈니스 활용**:
- 매장 매니저: 실시간 알람 → 직원 개입 타이밍
- 본사: 매장별 Assistance Need 발생률 → 직원 배치 의사결정

### 3.3 Companion Effect

**정의**: 한 세션 안에서 2명 이상 존재 가능성 또는 동행자 행동 패턴 관측.

**알고리즘 골격**:

```python
def detect_companion(session):
    """
    Companion Effect 추정.
    
    핵심: "정확한 인원 측정" 표현 피하고 "동행 가능성 신호" 로 톤다운.
    
    1. CSI 점유 추정값이 2 이상인 구간 비율
    2. RFID 이벤트의 동시성 (같은 fitting_room에 다른 SKU 입력)
    3. 세션 duration이 평균보다 길고 활동 패턴 복잡함
    """
    multi_occupancy_ratio = session.csi_window.occupancy_estimate_above(2) / len(session.csi_window)
    concurrent_rfid = check_concurrent_skus(session.rfid_events)
    long_duration = session.duration > 600  # 10분
    
    companion_probability = (
        0.5 * multi_occupancy_ratio +
        0.3 * (1.0 if concurrent_rfid else 0) +
        0.2 * (1.0 if long_duration else 0)
    )
    return companion_probability  # 0~1
```

**🔴 회색지대 주의**:
- 의료기기법·개인정보 회피 위해 *"정확한 인원 카운트"* 표현 금지
- *"동행 가능성 신호"* 로만 표현

**비즈니스 활용**:
- 본사: 동행 매장 운영 분석 (가족 매장 vs 단독 매장)
- 매장: 동행자 응대 가이드 작성

### 3.4 Fitting Friction Score

**정의**: RFID 회전율 + CSI 대기 강도를 결합한 매장 단위 마찰 지수.

**알고리즘 골격**:

```python
def calculate_fitting_friction(store, time_window):
    """
    Fitting Friction Score - 매장 단위 시간대별 마찰 지수.
    
    1. RFID 회전율: 시간당 fitting_room 사용 횟수
    2. CSI 대기 강도: 피팅룸 외부 영역 CSI 활동
    3. POS 결제 시각 vs 피팅룸 입실 시각의 평균 간격
    """
    rfid_turnover = count_sessions(store, time_window) / time_window.hours
    wait_intensity = mean_external_csi_activity(store, time_window)
    avg_purchase_delay = mean_pos_to_fitting_delay(store, time_window)
    
    friction = (
        0.4 * normalize(rfid_turnover, max=10) +
        0.4 * wait_intensity +
        0.2 * normalize(avg_purchase_delay, max=300)
    )
    return friction
```

**임계값 해석**:
- 상황 A: RFID 회전율 높음 + CSI 대기 강도 높음 → 피팅룸 돌아가지만 대기 병목
- 상황 B: RFID 회전율 보통 + CSI 대기 강도 낮음 → 피팅룸 진입 전 포기 (RFID로 절대 못 잡는 신호)

**비즈니스 활용**:
- 매장 매니저: 피크 시간대 피팅룸 전담 직원 배치
- 본사: 매장 신규 출점 시 피팅룸 개수 의사결정

### 3.5 Phantom Try-on Detection

**정의**: CSI상 입실 감지되었지만 RFID 이벤트 없음 → RFID 데이터 품질 검증.

**알고리즘 골격**:

```python
def detect_phantom(csi_windows, rfid_events, threshold=0.3):
    """
    Phantom Try-on Detection - RFID 누락 의심 케이스 발견.
    
    1. CSI 점유 추정 활동이 임계값 이상인 구간 식별
    2. 같은 시간대에 RFID enter 이벤트 부재 확인
    3. 알람 생성
    """
    phantoms = []
    for window in csi_windows:
        if window.activity_score > threshold and window.duration > 60:
            rfid_in_window = [e for e in rfid_events if window.start <= e.timestamp <= window.end]
            if not rfid_in_window:
                phantoms.append(PhantomAlert(
                    store_id=window.store_id,
                    fitting_room_id=window.fitting_room_id,
                    timestamp=window.start,
                    confidence=window.activity_score
                ))
    return phantoms
```

**비즈니스 활용**:
- 본사 RFID 운영팀: 누락 케이스 발견 → RFID 인프라 점검
- 영업 훅: *"PoC 첫 주에 Phantom 5건 발견했습니다"*

**검증 방법**:
- PoC 매장에서 RFID 운영팀 확인 → Phantom 알람의 실제 RFID 누락 정확도
- 정확도 80%+ 목표

---

## 4. Joint Signal 알고리즘 통합 흐름

```
[Raw Data 수집]
  RFID + POS + CSI raw
       ↓
[Stage 1: Session Reconstruction]
  reconstruct_sessions() → Try-on Session 마트
       ↓
[Stage 2: Joint Signal 계산 (배치)]
  - Hesitation Score (세션 단위)
  - Companion Effect (세션 단위)
  - Fitting Friction Score (매장 단위)
       ↓
[Stage 3: Real-time Alert (스트리밍)]
  - Assistance Need Signal (실시간)
  - Phantom Try-on Detection (실시간)
       ↓
[Stage 4: 분석 마트 적재]
  - SKU-Session 마트 (Hesitation 분석)
  - 매장-시간 마트 (Friction 분석)
  - 본사 통합 마트 (전사 트렌드)
       ↓
[Stage 5: 본사·매장 대시보드]
```

---

## 5. PoC 단계 검증 액션

### 5.1 Week 1: 데이터 수집 안정화

- ESP32-S3 노드 설치 (피팅룸당 1~2개)
- RFID·POS 데이터 통합 적재
- CSI raw 데이터 품질 확인

### 5.2 Week 2: Session Reconstruction 검증

- 정밀도·재현율 90%+ 목표
- 점유 구간 임계값(0.1)·세션 간격(3분) 정밀화

### 5.3 Week 3: Joint Signal 5종 측정

- Hesitation Score 분포 확인
- Phantom Detection 정확도 80%+
- Friction Score 시간대별 트렌드

### 5.4 Week 4: 비즈니스 임팩트 검증

- high try-on / low conversion SKU 5개 이상 발굴
- MD 회의 액션 1개 이상 채택
- 알고리즘 v2 정밀화

---

## 6. 향후 검증 과제

- 🔴 5종 Joint Signal 임계값 정확도 (PoC 4주 측정)
- 🔴 Session Reconstruction 정밀도·재현율 (PoC Week 2)
- 🔴 매장별 calibration 필요성 (다매장 PoC 시)
- 🔴 시즌별 매출 패턴과의 상관관계 (Pilot 12주)
- 🔴 ML 모델 vs 룰 기반 알고리즘 비교 (Phase 3)

**본 문서 활용 가이드**: 알고리즘 골격 + 임계값 가설 + 검증 방법은 Phase 1 시뮬레이션 데이터 개발 시 즉시 활용. 실측 후 v2로 정밀화.
