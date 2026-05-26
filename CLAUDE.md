# CLAUDE.md — TryOps Developer Guide

This file outlines build, run, test, and style commands for each component in the TryOps monorepo.

---

## 🛠️ Build & Run Commands

### 1. Stage 0 Concept Validation
- **Location**: `apps/stage0_validation/`
- **Language**: Python 3.10+
- **Run**: `python validate.py`

### 2. Store Gateway (Raspberry Pi)
- **Location**: `apps/store_gateway/`
- **Language**: Python 3.10+
- **Run**: `python main.py`
- **Test**: `pytest`

### 3. ESP32 Firmware
- **Location**: `apps/esp32_firmware/`
- **Language**: C++ (ESP-IDF 5.x)
- **Build**: `idf.py build`
- **Flash**: `idf.py -p <PORT> flash`
- **Monitor**: `idf.py monitor`

### 4. GCP Ingest Gateway
- **Location**: `apps/gcp_ingest/`
- **Language**: Python (FastAPI) + Docker
- **Run**: `uvicorn main:app --host 0.0.0.0 --port 8080 --reload`
- **Docker Build**: `docker build -t tryops-ingest .`

### 5. GCP ETL Service
- **Location**: `apps/gcp_etl/`
- **Language**: Python (Polars + Airflow)
- **Run**: `python main.py` or `airflow dags trigger tryops_etl_dag`

### 6. GCP Query API
- **Location**: `apps/gcp_query/`
- **Language**: Python (FastAPI)
- **Run**: `uvicorn main:app --host 0.0.0.0 --port 8081 --reload`

### 7. Web Dashboard (Next.js)
- **Location**: `apps/web/`
- **Language**: TypeScript (Next.js App Router)
- **Install**: `npm install`
- **Run Dev**: `npm run dev`
- **Build**: `npm run build`
- **Start**: `npm run start`

### 8. Infrastructure (Terraform)
- **Location**: `infra/terraform/environments/dev/` or `infra/terraform/environments/production/`
- **Command**:
  ```bash
  terraform init
  terraform plan
  terraform apply
  ```

---

## 🎨 Code Style & Standards

### Python (store_gateway, gcp_ingest, gcp_etl, gcp_query, stage0_validation)
- **Style**: PEP 8 compliance. Use standard Python typing hints.
- **Formatting**: `black -l 100` and `isort`.
- **Linting**: `flake8` or `ruff`.

### JavaScript / TypeScript (web)
- **Style**: ESLint standard config, Prettier for formatting.
- **Framework**: Next.js App Router, using functional React components.
- **Styling**: Vanilla CSS for layouts. Do not use TailwindCSS unless explicitly asked.

### C++ (esp32_firmware)
- **Style**: ESP-IDF styling standard. Lowercase snake_case for functions, camelCase for variables, prefixed `g_` for globals.
- **Compiler**: gcc-xtensa (managed by ESP-IDF).

### Terraform (infra)
- **Style**: Standard `terraform fmt` format.
- **Labels**: Every GCP resource must include `local.common_labels` for cost tracking.
- **Naming**: Format resources as `tryops-${var.environment}-${resource_type}`.
