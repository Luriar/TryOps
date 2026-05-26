# TryOps Store Gateway

Raspberry Pi(ARM64) 환경에서 동작하는 Edge IoT 게이트웨이 서비스입니다.

## 기능 (Features)
- **MQTT 수집**: 매장 내 ESP32-S3 노드로부터 CSI 데이터를 비동기로 수집합니다.
- **RFID Webhook (FastAPI)**: RFID 리더기에서 보내는 이벤트(enter/exit) 웹훅을 수신합니다.
- **POS Polling**: 매장 POS API를 주기적으로 폴링합니다.
- **로컬 암호화 버퍼 (SQLCipher)**: 수집된 원본 데이터를 AES-256으로 암호화하여 SQLite에 최대 7일간 보관합니다. 인터넷 장애 시 데이터 유실을 방지합니다.
- **1분 단위 집계 (Polars)**: CSI 데이터를 1분 단위로 병합하여 네트워크 전송량을 줄입니다.
- **GCP 전송 (Cloud Run)**: 5분마다 집계된 데이터를 GCP Cloud Run Ingest 엔드포인트로 전송하며, 이때 GCP Service Account JWT를 통해 인증합니다.

## 개발 환경 설정 (Local Dev)

로컬(Windows 등) 개발 시에는 SQLCipher 빌드 이슈를 피하기 위해 일반 `sqlite3`를 fallback으로 사용합니다.

```bash
pip install -e .[dev]
```

환경변수 (`.env`):
```
STORE_ID=store_001
INGEST_URL=https://tryops-ingest-xxxx.a.run.app/ingest
SQLCIPHER_KEY=mock-key-for-dev
GCP_SA_KEY_PATH=/path/to/tryops-store-gw-key.json
```

## 프로덕션 배포 (Raspberry Pi 4B)

프로덕션 환경에서는 `Dockerfile`을 통해 `sqlcipher` 확장을 소스코드부터 직접 빌드하여 안정성을 보장합니다.

```bash
docker build -t tryops-store-gateway .
```
