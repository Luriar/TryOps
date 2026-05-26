/**
 * Security Module
 * 
 * Secret Manager (API 키·비밀번호) + Cloud Armor (WAF) + Audit Logs
 * security_design.md 위협 모델링 대응
 */

locals {
  module_labels = merge(var.common_labels, {
    module      = "security"
    cost_center = "core"
  })
}

# ===================================================================
# Secret Manager — API 키·비밀번호 보관
# ===================================================================

# 매장 게이트웨이 API 키 (T-1 대응: API 키 회전)
resource "google_secret_manager_secret" "store_gateway_api_keys" {
  project   = var.project_id
  secret_id = "tryops-${var.environment}-store-gateway-api-keys"
  
  labels = merge(local.module_labels, {
    cost_center = "ingest"
    purpose     = "auth"
  })
  
  replication {
    auto {}
  }
  
  # 자동 회전 (90일)
  rotation {
    next_rotation_time = timeadd(timestamp(), "2160h")  # 90일 후
    rotation_period    = "7776000s"
  }
  
  topics {
    name = google_pubsub_topic.secret_rotation_notification.id
  }
  
  lifecycle {
    ignore_changes = [rotation[0].next_rotation_time]
  }
}

# 비밀 회전 알림 토픽 (회전 시 자동 발송)
resource "google_pubsub_topic" "secret_rotation_notification" {
  project = var.project_id
  name    = "tryops-${var.environment}-secret-rotation"
  
  labels = merge(local.module_labels, {
    purpose = "secret-notification"
  })
}

# Pub/Sub Service Agent에게 publish 권한
resource "google_pubsub_topic_iam_member" "secret_manager_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.secret_rotation_notification.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-secretmanager.iam.gserviceaccount.com"
}

data "google_project" "current" {
  project_id = var.project_id
}

# ===================================================================
# Cloud Armor — WAF + DDoS 방어
# ===================================================================

resource "google_compute_security_policy" "main" {
  project = var.project_id
  name    = "tryops-${var.environment}-armor-policy"
  
  description = "TryOps WAF + DDoS protection"
  
  # 기본 규칙: 모든 트래픽 허용
  rule {
    action      = "allow"
    description = "Default allow"
    priority    = 2147483647  # 최저 우선순위
    
    match {
      versioned_expr = "SRC_IPS_V1"
      
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
  
  # Rate limit — IP당 분당 100 요청
  rule {
    action      = "rate_based_ban"
    description = "Rate limit per IP"
    priority    = 1000
    
    match {
      versioned_expr = "SRC_IPS_V1"
      
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    rate_limit_options {
      conform_action      = "allow"
      exceed_action       = "deny(429)"
      enforce_on_key      = "IP"
      ban_duration_sec    = 600  # 10분 차단
      
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
  }
  
  # SQL Injection 방지 (사전 정의 규칙)
  rule {
    action      = "deny(403)"
    description = "Block SQL injection attempts"
    priority    = 100
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
  }
  
  # XSS 방지
  rule {
    action      = "deny(403)"
    description = "Block XSS attempts"
    priority    = 200
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
  }
  
  # 알려진 악성 IP 차단 (선택)
  rule {
    action      = "deny(403)"
    description = "Block known bad IPs"
    priority    = 300
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('scannerdetection-v33-stable')"
      }
    }
  }
}

# ===================================================================
# Audit Logs (Cloud Audit Logs는 기본 활성화 — Data Access 로그만 추가)
# ===================================================================

resource "google_project_iam_audit_config" "all_services" {
  project = var.project_id
  service = "allServices"
  
  audit_log_config {
    log_type = "ADMIN_READ"
  }
  
  audit_log_config {
    log_type = "DATA_READ"
    
    # 본사 사용자가 BigQuery 데이터 접근한 기록
    exempted_members = []
  }
  
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

# Audit Log 별도 저장소 (BigQuery 또는 Cloud Storage)
resource "google_logging_project_sink" "audit_logs_to_bigquery" {
  project = var.project_id
  name    = "tryops-${var.environment}-audit-logs-sink"
  
  # BigQuery 데이터셋 생성은 audit_logs 데이터셋 별도
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.audit_logs.dataset_id}"
  
  filter = <<-EOT
    logName:"cloudaudit.googleapis.com" OR
    logName:"data_access" OR
    severity>=WARNING
  EOT
  
  unique_writer_identity = true
}

resource "google_bigquery_dataset" "audit_logs" {
  project       = var.project_id
  dataset_id    = "audit_logs"
  friendly_name = "GCP Audit Logs"
  description   = "Cloud Audit Logs (보안 감사용)"
  location      = var.region
  
  # 1년 보존 (security_design.md 섹션 7.4)
  default_table_expiration_ms = 31536000000
  
  labels = merge(local.module_labels, {
    purpose     = "audit"
    cost_center = "core"
  })
}

resource "google_bigquery_dataset_iam_member" "audit_sink_writer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.audit_logs.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.audit_logs_to_bigquery.writer_identity
}

# ===================================================================
# Service Accounts
# ===================================================================

# Store Gateway Service Account
resource "google_service_account" "store_gw" {
  project      = var.project_id
  account_id   = "tryops-${var.environment}-store-gw"
  display_name = "Store Gateway Service Account"
}

# Ingest Service Account
resource "google_service_account" "ingest" {
  project      = var.project_id
  account_id   = "tryops-${var.environment}-ingest"
  display_name = "Cloud Run Ingest Service Account"
}

# Store Gateway needs Token Creator for JWTs
resource "google_project_iam_member" "store_gw_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.store_gw.email}"
}

# (The run.invoker role will be granted on the Cloud Run service in compute module, or globally here)
# For simplicity, granting globally if ingest isn't created in security module
resource "google_project_iam_member" "store_gw_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.store_gw.email}"
}
