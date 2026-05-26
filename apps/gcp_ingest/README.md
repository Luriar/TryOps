# TryOps Cloud Run Ingest Service

GCP Cloud Run 환경에서 동작하는 Serverless Ingest API입니다.
매장 게이트웨이(Raspberry Pi)가 5분 단위로 보내는 배치 데이터를 수신하여 Pub/Sub으로 전달합니다.

## 기능 (Features)
- **Zero Trust Auth**: Cloud Run IAM 프록시가 주입하는 `X-Goog-Authenticated-User-Email` 헤더 기반 인증.
- **Idempotency (멱등성)**: Firestore를 사용하여 7일간 `idempotency_key`를 보관하며 중복 처리를 방지합니다.
- **Pub/Sub Split Publish**: BigQuery Direct Subscription을 지원하기 위해, Ingest 서비스가 배치 Array를 개별 Row(메시지) 단위로 쪼개어 Pub/Sub에 발행합니다.
- **Resiliency**: Pub/Sub 발행 실패 시 `tenacity` 라이브러리를 통한 지수 백오프(Exponential Backoff) 자동 재시도.
- **Structured Logging**: GCP Cloud Logging 호환 JSON 로깅.

## 환경 변수
- `PROJECT_ID`: GCP 프로젝트 ID
- `PUBSUB_TOPIC_ID`: 데이터를 전송할 Pub/Sub 토픽 ID (Terraform으로 생성됨)

## 배포
이 서비스는 `.github/workflows/deploy-ingest.yml`을 통해 CI/CD로 자동 배포됩니다.
