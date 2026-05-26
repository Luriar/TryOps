# Concept Validation Spec — Stage 0 개념 검증 명세

> 본 문서는 TryOps의 Stage 0 (Concept Validation) 명세다. **본인 환경에서 칩 2개 + 가상 RFID 데이터로 알고리즘 본질을 검증하는 가장 싸고 빠른 단계**.
>
> **Stage 0 통과 후에만 Stage 1 (매장 MVP) 진행**. 즉, 본 단계가 *"매장 MVP에 1.5~2.5억 투자할 가치가 있는가"* 의 본질 판단 도구.

---

## 0. Stage 0의 본질 — 무엇이고 무엇이 아닌가

### 0.1 Stage 0는 무엇인가

- **기술 아이디어 + 알고리즘 본질 검증**
- 본인 자원으로 즉시 시작
- 매장 없이도 가능 (집·옷장·작은 공간)
- 가상 데이터 + 실제 CSI 신호 조합

### 0.2 Stage 0는 무엇이 아닌가

- ❌ 매장 MVP — 진짜 매장 환경 데이터가 아니라 의미 있는 비즈니스 데이터 불가
- ❌ 본사 영업 자료 — 실제 매장 사례 없이 본사 설득 안 됨
- ❌ 매장 게이트웨이·AWS·본사 대시보드 — 전부 Stage 1 이후

### 0.3 Stage 0 통과 vs 실패의 의미

| 결과 | 의미 | 다음 단계 |
|---|---|---|
| **통과** (정확도 80%+) | 알고리즘이 진짜 *"움직임·반복·체류"* 를 잡음 | Stage 1 진행 정당화 |
| **부분 통과** (정확도 50~80%) | 알고리즘 동작하지만 매장 환경 검증 필요 | Stage 1 진행, 단 노이즈 보정 우선 |
| **실패** (정확도 50% 미만) | ESP32-CSI 매장 환경에서 못 쓸 가능성 | Stage 1 보류, 다른 센서 검토 (mmWave 등) |

🟢 **이게 Stage 0의 진짜 가치**: 매장 MVP에 2~3억 투자 전에 **2~3만원으로 본질 검증**.

---

## 1. Stage 0 환경 구성

### 1.1 필요한 하드웨어

| 항목 | 수량 | 가격 (원) | 비고 |
|---|---|---|---|
| ESP32-S3 노드 | 2개 | 약 8,000~12,000 × 2 = 16,000~24,000 | 알리·LCSC 구매 |
| USB-C 케이블 | 2개 | 약 5,000 × 2 = 10,000 | 전원·디버깅 |
| 노트북 | 1대 | 기존 보유 | CSI 데이터 수집·분석 |
| **합계** | | **약 2.6~3.4만원** | |

### 1.2 필요한 SW

```bash
# 노트북 SW 환경
- Python 3.11
- numpy, pandas, polars (데이터 처리)
- esp-idf 또는 PlatformIO (ESP32-S3 펌웨어)
- ESP-CSI 라이브러리 (https://github.com/espressif/esp-csi)
- matplotlib (시각화)
- Jupyter Notebook (분석)
```

### 1.3 실험 환경 설계

```
┌────────────────────────────────────────────┐
│  본인 환경 (집 옷장·작은 공간)              │
│                                              │
│  ESP32-S3 #1 (송신, AP 모드)                 │
│         │                                    │
│         │ WiFi 신호                          │
│         ↓                                    │
│  [피팅 구역]    ← 본인 또는 친구              │
│   (옷장·커튼)                                │
│         ↑                                    │
│         │ WiFi 신호 (CSI 변동 측정)          │
│         │                                    │
│  ESP32-S3 #2 (수신, Station 모드)            │
│         │                                    │
│         ↓ USB 시리얼                         │
│  노트북 (CSI 데이터 수집·분석)                │
└────────────────────────────────────────────┘
```

**위치 추천**:
- 송신 노드 #1: 천장 또는 높은 곳 (1.8~2.0m)
- 수신 노드 #2: 반대편 비슷한 높이
- 피팅 구역: 두 노드 사이 (약 1.5~2m)

---

## 2. Stage 0 검증 시나리오 5종

본 설계 v2의 Joint Signal 5종을 Stage 0에서 단순화한 형태로 검증.

### 2.1 시나리오 1: 점유 추정 (Occupancy Detection)

**목적**: *"비어있음 vs 사람 있음"* 의 가장 기본 신호 검증.

**실험 설계**:
- 10분 빈 공간 → 10분 본인 정지 → 10분 본인 움직임 → 10분 빈 공간
- 4단계 각 10분, 총 40분 데이터

**기대 결과**:
- 빈 공간: activity_score < 0.1
- 정지 사람: activity_score 0.2~0.4
- 움직임 사람: activity_score > 0.5

**통과 기준**: 4단계 구분 정확도 80%+

### 2.2 시나리오 2: Hesitation Pattern (반복 행동 감지)

**목적**: *"옷 입었다 벗었다 반복"* 의 신호 검증.

**실험 설계**:
- 패턴 A (3분): 옷 1번 입고 그대로 → conversion 가정
- 패턴 B (5분): 옷 1번 입고 → 거울 보기 → 다시 벗기 → 다른 사이즈 입기 → hesitation 가정
- 패턴 C (3분): 옷 안 입고 그냥 가만히 → 정지 가정

**기대 결과**:
- Hesitation Score: 패턴 B > 패턴 A > 패턴 C
- 패턴 B 가 0.6+ 점수

**통과 기준**: 3가지 패턴 정확 구분 80%+

### 2.3 시나리오 3: Dwell Time (체류 시간)

**목적**: *"오래 머무름"* 의 신호 검증.

**실험 설계**:
- 짧은 체류 2분 → 빈 공간 2분 → 긴 체류 8분 → 빈 공간 2분
- 4단계, 총 14분

**기대 결과**: 점유 구간의 시작·종료 시각이 ±10초 이내 정확

**통과 기준**: 점유 구간 정밀도 90%+

### 2.4 시나리오 4: Phantom Detection (가상 RFID 매칭)

**목적**: *"CSI 활동 + RFID 이벤트 동시성"* 검증.

**실험 설계**:
- 본인이 *"가상 try-on"* 시 노트북에 RFID 이벤트 수동 입력 (또는 자동 스크립트로 시뮬레이션)
- 시나리오: 10번 try-on 중 2번은 RFID 이벤트 누락 (의도적)
- CSI 활동 강도 + RFID 매칭으로 *"Phantom"* 발견 능력 검증

**기대 결과**: 2건 Phantom 모두 발견

**통과 기준**: Phantom 발견 정확도 80%+

### 2.5 시나리오 5: 노이즈 환경 (강건성 검증)

**목적**: *"다른 WiFi·블루투스·사람 영향"* 의 매장 환경 시뮬레이션.

**실험 설계**:
- 시나리오 1~4를 *"노이즈 환경"* 에서 반복:
  - 폰 WiFi 켜기
  - 블루투스 이어폰 페어링
  - 옆 방에서 다른 사람 활동
- 4단계 강도

**기대 결과**: 노이즈에도 시나리오 1~4 정확도 60%+ 유지

**통과 기준**: 노이즈 강건성 60%+

---

## 3. 가상 RFID·POS 데이터 활용 (사용자 결정 반영)

### 3.1 데이터 소스 결정

🟢 **1차 선택: H&M Personalized Fashion Recommendations** (Kaggle 대회 데이터, CC BY 4.0)

링크: https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data

구성:
- **articles.csv**: 10.6만 제품 메타데이터 (product_name, type, group, colour, department, garment group, description)
- **customers.csv**: 137만 고객 (club member, subscription, age)
- **transactions_train.csv**: 실제 구매 이력 (article_id, customer_id, t_dat, price, sales_channel_id)

🟢 **2차 옵션: UCI Online Retail II** (CC BY 4.0)

링크: https://archive.ics.uci.edu/dataset/502/online+retail+ii

구성: 약 100만 트랜잭션, 의류 외 일반 리테일

→ H&M이 압도적 적합. 의류 카테고리·가먼트 그룹·색상·가격 모두 있어 *"피팅룸 try-on"* 시뮬레이션 정확.

### 3.2 H&M 데이터 → TryOps RFID 이벤트 합성 방법

```python
import pandas as pd
import polars as pl

def synthesize_tryops_data(hm_articles_path, hm_transactions_path):
    """H&M 데이터를 TryOps Stage 0 RFID·POS 이벤트로 변환."""
    
    # 1. 의류 카테고리만 필터링 (피팅룸 가능 제품)
    articles = pl.read_csv(hm_articles_path)
    fittable = articles.filter(
        pl.col("garment_group_name").is_in([
            "Jersey Basic", "Dresses Ladies", "Knitwear",
            "Trousers Denim", "Trousers", "Shirts", "Blouses",
            "Outdoor", "Skirts", "Sweaters"
        ])
    )
    
    # 2. 실제 트랜잭션 로드
    transactions = pl.read_csv(hm_transactions_path).filter(
        pl.col("article_id").is_in(fittable["article_id"])
    )
    
    # 3. "구매 = try-on 1.3건" 가정으로 try-on 이벤트 합성
    try_on_events = synthesize_try_on_from_transactions(transactions, ratio=1.3)
    
    # 4. "high try-on / low conversion" 케이스 의도적 추가 (10%)
    hesitation_cases = inject_hesitation_cases(try_on_events, ratio=0.1)
    
    # 5. RFID enter/exit 이벤트 포맷 변환
    rfid_events = convert_to_rfid_format(hesitation_cases)
    
    # 6. POS 결제 이벤트 (실제 H&M 트랜잭션)
    pos_events = convert_to_pos_format(transactions)
    
    return rfid_events, pos_events
```

### 3.3 합성 데이터의 한계 명시

🔴 **본 합성의 한계**:
- 실제 매장 try-on 행동 시간 분포 ≠ H&M 온라인 구매 시간
- 한국 매장 vs UK 온라인 차이 (사이즈·가격·시즌)
- *"의도적 hesitation 케이스"* 의 합성 비율 (10%) 가정

→ Stage 0 검증의 한계는 *"알고리즘 작동 가능성"* 까지만. *"실제 매장 정확도"* 는 Stage 1에서 검증.

### 3.4 H&M 데이터셋 라이선스 정리

- 라이선스: CC BY 4.0 (Creative Commons Attribution)
- **상업 사용 가능**
- 출처 표기 필수: *"H&M Personalized Fashion Recommendations Dataset, Kaggle Competition 2022"*
- 향후 TryOps 영업 자료 활용 시도 가능 (단, *"Stage 0 합성 데이터"* 명시)

---

## 4. Stage 0 일정

### 4.1 4주 일정

**Week 1: 셋업**
- ESP32-S3 노드 2개 구매·배송 (3~5일)
- ESP-IDF 환경 셋업
- ESP-CSI 라이브러리 빌드
- 첫 CSI 데이터 수집 성공

**Week 2: 알고리즘 구현**
- Polars로 CSI 1분 집계
- activity_score / occupancy_estimate 알고리즘 v1
- 시나리오 1 (점유 추정) 실험

**Week 3: 검증 시나리오**
- 시나리오 2~5 차례 실험
- 가상 RFID 데이터 합성 (H&M 데이터셋)
- Phantom Detection 알고리즘 v1
- 결과 분석

**Week 4: 결론 + 보고**
- 5가지 시나리오 통과 vs 실패 평가
- Stage 1 진행 결정 권고
- 알고리즘 v1 정밀화 또는 폐기 결정

### 4.2 시간 투자

- Week 1~4: 본인 시간 약 60~80시간 (주 15~20시간)
- 또는 풀타임 4주 (160시간)

🟢 **본인 자원으로 즉시 시작 가능**. 외주·인력 채용 0건.

---

## 5. Stage 0 검증 통과 기준

### 5.1 정량 기준 (5종 시나리오)

| 시나리오 | 통과 기준 | 측정 |
|---|---|---|
| 1. 점유 추정 | 80%+ | 빈/정지/움직임 구분 |
| 2. Hesitation | 80%+ | 3가지 패턴 구분 |
| 3. Dwell Time | 90%+ | 시간 정밀도 ±10초 |
| 4. Phantom Detection | 80%+ | Phantom 발견 |
| 5. 노이즈 강건성 | 60%+ | 노이즈 환경 정확도 |

**전체 통과 기준**: 5종 중 **4종 이상 통과 + 시나리오 1·2 무조건 통과**.

### 5.2 정성 기준 (비즈니스 임팩트)

- 알고리즘이 *"진짜 행동"* 을 잡는가 직관적 확신
- 매장 환경에서 *"노이즈 보정"* 으로 끌어올릴 가능성
- 본사 영업 시 *"기술 작동 증명"* 자료로 활용 가능 여부

---

## 6. Stage 0 → Stage 1 진입 결정 매트릭스

| Stage 0 결과 | Stage 1 진입 | 사전 작업 |
|---|---|---|
| **완전 통과** (5종 ≥ 80%) | ✅ 즉시 진입 | Stage 1 자금 모금 |
| **부분 통과** (3~4종 통과) | ✅ 진입, 단 보강 | 노이즈 보정 알고리즘 우선 |
| **시나리오 1·2 통과만** | 🟡 진입 가능, 신중 | 매장 1개 PoC 단계 더 보수적 |
| **시나리오 1·2 실패** | ❌ 보류 | mmWave 등 다른 센서 검토 |
| **실패** | ❌ 중단 | TryOps 컨셉 재검토 또는 폐기 |

🟢 **이게 *"실제 사업 시작 시 동일 프로세스 재사용"* 의 본질적 검증 단계**. Stage 0 결과 없이 Stage 1 진입은 **2~3억 도박**.

---

## 7. Stage 0 결과물 (PoC 1단계 활용 자산)

### 7.1 데이터 자산

- CSI raw 데이터 4주분 (자체 보유)
- 알고리즘 v1 정확도 측정 리포트
- 5종 시나리오 실험 로그

### 7.2 코드 자산

- ESP32-S3 펌웨어 (Stage 1 매장 펌웨어의 기반)
- Polars 기반 CSI 분석 코드 (Stage 1 매장 게이트웨이 SW의 기반)
- 가상 RFID 합성 스크립트 (Stage 1 시뮬레이션 자료)

### 7.3 영업 자산

- *"기술 작동 증명"* 자료 (본사 영업 첫 슬라이드)
- *"알고리즘 정확도 80%+"* 의 정량 근거
- *"Phantom Detection 검증 사례"* (RFID 솔루션사 영업)

### 7.4 면접 자산

- *"2~3만원으로 본질 검증"* 의 PM 사고 사례
- 셀프 검증 시스템 (Stage 0 vs Stage 1 분리)
- 가설 흔들림 발견 시 즉시 인정 (실패 결과도 자산)

---

## 8. Stage 0 비용 정리

### 8.1 진짜 비용

| 항목 | 비용 |
|---|---|
| ESP32-S3 노드 2개 + 케이블 | 약 2.6~3.4만원 |
| 노트북 | 0원 (기존 보유) |
| 본인 시간 4주 | (기회 비용) |
| 한국 법무 검토 | 0원 (Stage 0는 매장 도입 없음, 법무 불요) |
| AWS 비용 | 0원 |
| **합계** | **약 2.6~3.4만원** |

### 8.2 비교 — Stage 1과 차이

| 단계 | 비용 (1년) | 시간 | 비고 |
|---|---|---|---|
| **Stage 0** | **약 3만원** | **4주** | **본인 자원** |
| Stage 1 (매장 MVP) | 약 1.5~2.5억원 | 6개월 | 인력 + HW + AWS + 법무 |
| Stage 2 (매장 10~100개) | 약 5~10억원/년 | - | 본격 사업 |

**Stage 0 = Stage 1의 1/5,000 비용**. 본 단계가 *"가장 싸게"* 의 본질적 정합.

---

## 9. Stage 0의 위치 — 본 프로젝트 전체에서

```
[기획 단계 완료]
  └ 페르소나 9인 + 1차 출처 21건 + 인터뷰 액션 플랜
  
[설계 단계 완료]  
  └ AWS Phase 1·2 정밀 설계 + 보안 + 운영 + 거버넌스
  
[Stage 0 — 본 문서] ★ 우선 진행 ★
  └ 칩 2개 + 가상 RFID 데이터 + 본인 환경 4주
  └ 알고리즘 본질 검증
  
[Stage 1 — 매장 MVP] (Stage 0 통과 후)
  └ 1.5~2.5억원 6개월
  └ 실제 매장 1개 PoC
  
[Stage 2 — 본격 확장]
  └ 매장 10~100개
```

---

## 10. 본 Stage 0 spec의 한계

본 v1은:
- 🔴 실제 ESP-CSI 라이브러리 빌드 시도 0건 (실패 시 일정 영향)
- 🔴 H&M 데이터셋의 *"의류 카테고리"* 한국 매장 적합성 미검증
- 🔴 노이즈 환경 시나리오 설계의 매장 환경 대표성 부재
- 🔴 본인 환경 (집 옷장) 의 매장 환경 대표성 부재

**진짜 검증 시작 시**: ESP32-S3 노드 구매 → ESP-CSI 빌드 → 첫 CSI 데이터 수집까지가 1주 안에 가능한지 즉시 확인 필수.

**본 문서 활용 가이드**: 본 v1을 토대로 Stage 0 즉시 착수. Week 1 결과에 따라 v2 갱신. Stage 0 4주 완료 후 Stage 1 진입 판단의 *"수치 근거"* 자료로 활용.
