# TryOps GCP Query API

Next.js 대시보드에 데이터를 제공하는 Cloud Run 기반 FastAPI 백엔드입니다.

## 기능
- Firebase JWT 토큰 검증 및 역할(Role) 기반 인가(Authorization)
- BigQuery 데이터 조회 (Parameterized 쿼리 강제 적용)
- 매장 매니저 본인 매장만 접근 가능 (🛡️ Shield Data 분리)

## 개발 및 테스트
로컬에서 개발 및 테스트하는 방법:

```bash
# 의존성 설치
pip install -e ".[test]"

# 테스트 실행 (유닛 테스트 및 JWT 인가 시나리오 테스트)
pytest tests/

# 로컬 서버 실행 (Mock 모드: 실제 BigQuery를 조회하지 않고 더미 데이터 반환)
USE_MOCK_DATA=true uvicorn src.query.main:app --reload --port 8000
```

## 환경 변수
- `USE_MOCK_DATA`: `true`일 경우 실제 BigQuery 쿼리를 실행하지 않고 Mock 데이터를 반환합니다. PoC 단계용.
- `CORS_ORIGINS`: 쉼표로 구분된 허용 CORS Origin 리스트 (예: `http://localhost:3000,https://tryops.cloudflare.com`)

## 배포
Cloud Run 배포 (Terraform에서 관리):
```bash
gcloud builds submit --tag gcr.io/tryops/gcp-query
gcloud run deploy gcp-query --image gcr.io/tryops/gcp-query --platform managed --region asia-northeast3 --allow-unauthenticated
```
