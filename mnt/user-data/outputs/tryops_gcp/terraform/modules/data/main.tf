/**
 * Data Module
 * 
 * Pub/Sub 토픽 + BigQuery 데이터셋·테이블 + BigQuery subscription
 * 본 설계의 핵심 데이터 파이프라인.
 */

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast3"
}

variable "common_labels" {
  description = "Common labels"
  type        = map(string)
}

locals {
  module_labels = merge(var.common_labels, {
    module      = "data"
    cost_center = "ingest"
  })
}

# ===================================================================
# Pub/Sub 토픽 — 매장 → AWS Ingest 데이터 수신
# ===================================================================

resource "google_pubsub_topic" "store_events" {
  project = var.project_id
  name    = "tryops-${var.environment}-store-events"
  
  labels = merge(local.module_labels, {
    cost_center = "ingest"
  })
  
  message_retention_duration = "604800s"  # 7일 (data_governance.md 보존 정책)
  
  schema_settings {
    schema   = google_pubsub_schema.store_event.id
    encoding = "JSON"
  }
}

# Pub/Sub 스키마 — 메시지 형식 강제
resource "google_pubsub_schema" "store_event" {
  project = var.project_id
  name    = "tryops-${var.environment}-store-event-schema"
  type    = "AVRO"
  
  definition = jsonencode({
    type = "record"
    name = "StoreEvent"
    fields = [
      { name = "brand_id", type = "string" },
      { name = "store_id", type = "string" },
      { name = "batch_start", type = { type = "long", logicalType = "timestamp-micros" } },
      { name = "batch_end", type = { type = "long", logicalType = "timestamp-micros" } },
      { name = "csi_aggregates", type = "string" },  # JSON string
      { name = "rfid_events", type = "string" },
      { name = "pos_events", type = "string" },
      { name = "ingested_at", type = { type = "long", logicalType = "timestamp-micros" } }
    ]
  })
}

# Dead Letter Topic (전송 실패 메시지)
resource "google_pubsub_topic" "store_events_dlq" {
  project = var.project_id
  name    = "tryops-${var.environment}-store-events-dlq"
  
  labels = merge(local.module_labels, {
    cost_center = "ingest"
    purpose     = "dlq"
  })
  
  message_retention_duration = "604800s"
}

# ===================================================================
# BigQuery 데이터셋
# ===================================================================

resource "google_bigquery_dataset" "tryops_data" {
  project       = var.project_id
  dataset_id    = "tryops_${var.environment}_data"
  friendly_name = "TryOps Production Data"
  description   = "본사·매장 데이터, Joint Signal 결과, 보고서"
  location      = var.region
  
  labels = merge(local.module_labels, {
    cost_center = "core"
  })
  
  # 모든 본사 데이터를 한 데이터셋에 보관, brand_id 컬럼으로 격리
  # (브랜드별 데이터셋 분리는 Phase 3+ 진화)
  
  default_table_expiration_ms = null  # 테이블별 보존 정책 적용
  
  access {
    role          = "OWNER"
    user_by_email = var.terraform_service_account
  }
}

# Billing Export 데이터셋
resource "google_bigquery_dataset" "billing_export" {
  project       = var.project_id
  dataset_id    = "billing_export"
  friendly_name = "GCP Billing Export"
  description   = "GCP 청구 내역 자동 적재 (라벨별 비용 분석용)"
  location      = var.region
  
  labels = merge(local.module_labels, {
    module      = "monitoring"
    cost_center = "core"
    purpose     = "billing-analysis"
  })
}

# ===================================================================
# BigQuery 테이블
# ===================================================================

# raw_events 테이블 — Pub/Sub subscription이 자동 적재
resource "google_bigquery_table" "raw_events" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.tryops_data.dataset_id
  table_id   = "raw_events"
  
  # 데이터 보존 90일 (data_governance.md)
  expiration_time = null
  
  time_partitioning {
    type          = "DAY"
    field         = "batch_start"
    expiration_ms = 7776000000  # 90일
  }
  
  clustering = ["brand_id", "store_id"]
  
  schema = jsonencode([
    { name = "brand_id", type = "STRING", mode = "REQUIRED" },
    { name = "store_id", type = "STRING", mode = "REQUIRED" },
    { name = "batch_start", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "batch_end", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "csi_aggregates", type = "JSON", mode = "NULLABLE" },
    { name = "rfid_events", type = "JSON", mode = "NULLABLE" },
    { name = "pos_events", type = "JSON", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" }
  ])
  
  labels = merge(local.module_labels, {
    table_purpose = "raw"
    data_class    = "L2-confidential"
  })
  
  deletion_protection = true
}

# joint_signals 테이블 — ETL 결과
resource "google_bigquery_table" "joint_signals" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.tryops_data.dataset_id
  table_id   = "joint_signals"
  
  time_partitioning {
    type          = "DAY"
    field         = "signal_date"
    expiration_ms = 31536000000  # 1년
  }
  
  clustering = ["brand_id", "store_id", "sku_id"]
  
  schema = jsonencode([
    { name = "brand_id", type = "STRING", mode = "REQUIRED" },
    { name = "store_id", type = "STRING", mode = "REQUIRED" },
    { name = "sku_id", type = "STRING", mode = "NULLABLE" },
    { name = "session_id", type = "STRING", mode = "REQUIRED" },
    { name = "signal_date", type = "DATE", mode = "REQUIRED" },
    { name = "session_start", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "session_duration_seconds", type = "INT64", mode = "NULLABLE" },
    { name = "hesitation_score", type = "FLOAT64", mode = "NULLABLE" },
    { name = "companion_probability", type = "FLOAT64", mode = "NULLABLE" },
    { name = "fitting_friction", type = "FLOAT64", mode = "NULLABLE" },
    { name = "assistance_need_alert", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "phantom_detection", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "computed_at", type = "TIMESTAMP", mode = "REQUIRED" }
  ])
  
  labels = merge(local.module_labels, {
    table_purpose = "mart"
    cost_center   = "etl"
  })
  
  deletion_protection = true
}

# reports 테이블 — 본사 월간 보고
resource "google_bigquery_table" "reports" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.tryops_data.dataset_id
  table_id   = "reports"
  
  time_partitioning {
    type          = "MONTH"
    field         = "report_month"
    expiration_ms = 94608000000  # 3년
  }
  
  clustering = ["brand_id"]
  
  schema = jsonencode([
    { name = "brand_id", type = "STRING", mode = "REQUIRED" },
    { name = "report_month", type = "DATE", mode = "REQUIRED" },
    { name = "metrics", type = "JSON", mode = "REQUIRED" },
    { name = "generated_at", type = "TIMESTAMP", mode = "REQUIRED" }
  ])
  
  labels = merge(local.module_labels, {
    table_purpose = "reports"
    cost_center   = "dashboard"
  })
  
  deletion_protection = true
}

# ===================================================================
# Pub/Sub → BigQuery subscription
# ===================================================================

# Pub/Sub Service Account에게 BigQuery 쓰기 권한 부여
data "google_project" "current" {
  project_id = var.project_id
}

resource "google_bigquery_table_iam_member" "pubsub_writer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.tryops_data.dataset_id
  table_id   = google_bigquery_table.raw_events.table_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# BigQuery subscription
resource "google_pubsub_subscription" "to_bigquery" {
  project = var.project_id
  name    = "tryops-${var.environment}-to-bigquery"
  topic   = google_pubsub_topic.store_events.name
  
  labels = merge(local.module_labels, {
    cost_center = "ingest"
  })
  
  bigquery_config {
    table               = "${var.project_id}.${google_bigquery_dataset.tryops_data.dataset_id}.${google_bigquery_table.raw_events.table_id}"
    use_topic_schema    = true
    write_metadata      = false
    drop_unknown_fields = false
  }
  
  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"  # 7일
  retain_acked_messages      = false
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.store_events_dlq.id
    max_delivery_attempts = 5
  }
  
  expiration_policy {
    ttl = ""  # 영구
  }
  
  depends_on = [
    google_bigquery_table_iam_member.pubsub_writer
  ]
}

# Outputs
output "pubsub_topic_id" {
  value = google_pubsub_topic.store_events.id
}

output "pubsub_topic_name" {
  value = google_pubsub_topic.store_events.name
}

output "bigquery_dataset_id" {
  value = google_bigquery_dataset.tryops_data.dataset_id
}

output "bigquery_raw_events_table" {
  value = "${var.project_id}.${google_bigquery_dataset.tryops_data.dataset_id}.${google_bigquery_table.raw_events.table_id}"
}

output "bigquery_joint_signals_table" {
  value = "${var.project_id}.${google_bigquery_dataset.tryops_data.dataset_id}.${google_bigquery_table.joint_signals.table_id}"
}

output "billing_export_dataset_id" {
  value = google_bigquery_dataset.billing_export.dataset_id
}

# 추가 변수
variable "terraform_service_account" {
  description = "Terraform Service Account email"
  type        = string
}
