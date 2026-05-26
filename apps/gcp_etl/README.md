# TryOps GCP ETL Service

Compute Engine (`e2-small`) 환경에서 Linux Cron을 통해 동작하는 가벼운 데이터 파이프라인 엔진입니다.
매장 게이트웨이가 수집하여 BigQuery에 꽂힌 `raw_events` 데이터를 분석 마트 데이터로 변환합니다.

## 기능 (Features)
- **Zero Airflow, High Efficiency**: 메모리를 많이 먹는 프레임워크를 제거하고 순수 Python 스크립트 + Cron 스케줄링으로 가장 싸게 동작합니다.
- **Engine Mix**: I/O가 많은 전처리와 시간축 병합(Join Asof)은 `Polars`로 처리하고, 복잡한 윈도우 함수 및 마트 집계 쿼리는 인메모리 `DuckDB`로 처리합니다.
- **Idempotency (멱등성)**: 스크립트를 재실행해도 데이터가 중복으로 쌓이지 않고 안전하게 `REPLACE` 되도록 설계되었습니다.

## 주요 스크립트 
- `scripts/tryops_hourly.py`: 매시간 실행. RFID와 CSI 데이터를 결합하여 세션(Try-on Session)을 재구성하고, Hesitation / Companion / Friction 점수를 계산합니다.
- `scripts/tryops_daily.py`: 자정 실행. 일일 마트 구성 및 데이터 정합성 검사(Data Quality Check).
- `scripts/tryops_monthly.py`: 월 1회 실행. 본사용 월간 분석 리포트 생성.

## 배포
- `ansible/deploy_etl.yml` 플레이북을 이용해 GCP Compute Engine 프로비저닝 시 관련 파이썬 환경과 crontab을 자동 구성합니다.
