/**
 * Compute Module
 * 
 * Compute Engine e2-small (ETL용) + Cloud Run (Ingest·Query API)
 * Service Account 권한 분리
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

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "asia-northeast3-a"
}

variable "common_labels" {
  description = "Common labels"
  type        = map(string)
}

variable "subnet_id" {
  description = "VPC Subnet ID"
  type        = string
}

variable "subnet_self_link" {
  description = "VPC Subnet self link"
  type        = string
}

variable "pubsub_topic_id" {
  description = "Pub/Sub topic ID"
  type        = string
}

variable "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}

locals {
  module_labels = merge(var.common_labels, {
    module = "compute"
  })
}

# ===================================================================
# Service Accounts
# ===================================================================

# ETL Service Account (Compute Engine용)
resource "google_service_account" "etl" {
  project      = var.project_id
  account_id   = "tryops-${var.environment}-etl"
  display_name = "TryOps ETL Service Account"
  description  = "Compute Engine에서 ETL 작업 수행 (Polars + BigQuery)"
}

resource "google_project_iam_member" "etl_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.etl.email}"
  
  condition {
    title       = "Only tryops dataset"
    description = "Restrict to tryops dataset"
    expression  = "resource.name.startsWith('projects/${var.project_id}/datasets/${var.bigquery_dataset_id}')"
  }
}

resource "google_project_iam_member" "etl_bigquery_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.etl.email}"
}

resource "google_project_iam_member" "etl_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.etl.email}"
}

# Ingest Service Account (Cloud Run용)
resource "google_service_account" "ingest" {
  project      = var.project_id
  account_id   = "tryops-${var.environment}-ingest"
  display_name = "TryOps Ingest Service Account"
  description  = "Cloud Run Ingest 서비스 (Pub/Sub publish)"
}

resource "google_project_iam_member" "ingest_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.ingest.email}"
}

resource "google_project_iam_member" "ingest_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.ingest.email}"
}

# Query Service Account (Cloud Run 대시보드 API용)
resource "google_service_account" "query" {
  project      = var.project_id
  account_id   = "tryops-${var.environment}-query"
  display_name = "TryOps Query Service Account"
  description  = "Cloud Run Query API 서비스 (BigQuery 읽기)"
}

resource "google_project_iam_member" "query_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.query.email}"
}

resource "google_project_iam_member" "query_bigquery_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.query.email}"
}

# Store Gateway Service Account (매장 게이트웨이 → GCP 호출용)
resource "google_service_account" "store_gateway" {
  project      = var.project_id
  account_id   = "tryops-${var.environment}-store-gw"
  display_name = "TryOps Store Gateway Service Account"
  description  = "매장 게이트웨이가 Cloud Run Ingest 호출 시 사용"
}

# ===================================================================
# Compute Engine ETL 인스턴스
# ===================================================================

resource "google_compute_instance" "etl" {
  project      = var.project_id
  name         = "tryops-${var.environment}-etl"
  machine_type = "e2-small"
  zone         = var.zone
  
  labels = merge(local.module_labels, {
    cost_center = "etl"
    purpose     = "polars-airflow"
  })
  
  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30  # GB
      type  = "pd-balanced"  # SSD가 너무 비싸므로 balanced 선택
      
      labels = merge(local.module_labels, {
        cost_center = "etl"
      })
    }
  }
  
  network_interface {
    subnetwork = var.subnet_self_link
    
    # 외부 IP 없음 (Cloud NAT 통해 outbound만)
  }
  
  service_account {
    email  = google_service_account.etl.email
    scopes = ["cloud-platform"]
  }
  
  metadata = {
    enable-oslogin = "TRUE"  # IAP SSH 사용
    ssh-keys       = ""       # 직접 SSH 키 차단
  }
  
  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update
    apt-get install -y python3-pip python3-venv
    
    # ETL 사용자 생성
    useradd -m -s /bin/bash etl
    
    # Polars + DuckDB + Airflow 환경 (실제 SW 설치는 별도 Ansible)
    sudo -u etl bash -c "python3 -m venv /home/etl/venv"
    sudo -u etl bash -c "/home/etl/venv/bin/pip install polars duckdb apache-airflow google-cloud-bigquery"
    
    # Cloud Logging Agent (Ops Agent 권장)
    curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
    sudo bash add-google-cloud-ops-agent-repo.sh --also-install
  EOT
  
  scheduling {
    preemptible       = false
    automatic_restart = true
    on_host_maintenance = "MIGRATE"
  }
  
  # 깜빡 삭제 방지
  deletion_protection = true
}

# ===================================================================
# Cloud Run — Ingest API
# ===================================================================

resource "google_cloud_run_v2_service" "ingest" {
  project  = var.project_id
  name     = "tryops-${var.environment}-ingest"
  location = var.region
  
  labels = merge(local.module_labels, {
    cost_center = "ingest"
  })
  
  template {
    service_account = google_service_account.ingest.email
    
    scaling {
      min_instance_count = 0  # 0부터 자동 확장
      max_instance_count = 10  # 매장 100개 5분 배치 가정 시 충분
    }
    
    containers {
      # 첫 배포 시 placeholder 이미지, CI/CD가 실제 이미지로 교체
      image = "asia-northeast3-docker.pkg.dev/${var.project_id}/tryops-${var.environment}/ingest:latest"
      
      resources {
        limits = {
          cpu    = "1000m"     # 1 vCPU
          memory = "512Mi"
        }
      }
      
      env {
        name  = "PUBSUB_TOPIC"
        value = var.pubsub_topic_id
      }
      
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
    
    timeout = "60s"
    
    labels = merge(local.module_labels, {
      cost_center = "ingest"
    })
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# 매장 게이트웨이 SA에게 ingest 호출 권한 (Cloud Run IAM)
resource "google_cloud_run_v2_service_iam_member" "store_gateway_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.ingest.location
  name     = google_cloud_run_v2_service.ingest.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.store_gateway.email}"
}

# ===================================================================
# Cloud Run — Query API (본사 대시보드)
# ===================================================================

resource "google_cloud_run_v2_service" "query" {
  project  = var.project_id
  name     = "tryops-${var.environment}-query"
  location = var.region
  
  labels = merge(local.module_labels, {
    cost_center = "dashboard"
  })
  
  template {
    service_account = google_service_account.query.email
    
    scaling {
      min_instance_count = 0
      max_instance_count = 20  # 본사 사용자 다수 동시 접근 대비
    }
    
    containers {
      image = "asia-northeast3-docker.pkg.dev/${var.project_id}/tryops-${var.environment}/query:latest"
      
      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"  # BigQuery 결과 캐싱
        }
      }
      
      env {
        name  = "BIGQUERY_DATASET"
        value = var.bigquery_dataset_id
      }
      
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
    
    timeout = "60s"
    
    labels = merge(local.module_labels, {
      cost_center = "dashboard"
    })
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Outputs
output "etl_instance_name" {
  value = google_compute_instance.etl.name
}

output "etl_service_account_email" {
  value = google_service_account.etl.email
}

output "ingest_service_url" {
  value = google_cloud_run_v2_service.ingest.uri
}

output "ingest_service_account_email" {
  value = google_service_account.ingest.email
}

output "query_service_url" {
  value = google_cloud_run_v2_service.query.uri
}

output "store_gateway_service_account_email" {
  value = google_service_account.store_gateway.email
}
