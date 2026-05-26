# TryOps Stage 0 Concept Validation

본 패키지는 TryOps의 **Stage 0 (개념 검증)** 단계를 위한 시뮬레이션 및 알고리즘 검증 코드입니다.
ESP32 실제 하드웨어 연결 없이도 가상 CSI 신호와 H&M Kaggle 데이터셋을 활용하여 5종의 핵심 알고리즘(Joint Signals)을 검증할 수 있습니다.

## 4주 일정 (docs/planning/concept_validation_spec.md 참조)
*   **Week 1**: 환경 셋업 (완료)
*   **Week 2**: CSI 1분 집계 알고리즘 구현
*   **Week 3**: 가상 RFID 데이터 합성 및 5종 시나리오 실험
*   **Week 4**: 결과 분석 및 Stage 1 진입 결정

## H&M Kaggle 데이터셋 준비
본 검증 패키지는 가상 RFID 이벤트 합성을 위해 H&M 데이터를 사용합니다. (테스트 코드 실행 시에는 내장된 Mock 데이터를 사용하므로 다운로드가 필수적이지는 않습니다.)

1. [Kaggle: H&M Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data) 접속
2. `articles.csv` 및 `transactions_train.csv` 다운로드
3. `data/hm/` 디렉터리 생성 후 파일 배치

## 사용법

1. 패키지 설치:
   ```bash
   pip install -e .[dev]
   ```
2. 테스트 실행:
   ```bash
   pytest tests/
   ```
3. 5종 시나리오 실행 (예시):
   ```bash
   python src/stage0/scenarios/scenario_1_occupancy.py
   python src/stage0/scenarios/scenario_2_hesitation.py
   ```
