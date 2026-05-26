/**
 * Production Environment
 * 
 * 본 파일은 모든 모듈을 호출해 production 환경 전체 인프라 생성.
 * 
 * 사용:
 *   cd infra/terraform/environments/production
 *   terraform init
 *   terraform plan
 *   terraform apply
 */

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  
  # State 저장소 — Cloud Storage 백엔드
  backend "gcs" {
    bucket = "tryops-production-terraform-state"
    prefix = "production"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# ===================================================================
# 변수
# ===================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  # 예: "tryops-production-prod"
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

variable "billing_account_id" {
  description = "GCP Billing Account ID"
  type        = string
}

variable "alert_email" {
  description = "비용·운영 알람 이메일"
  type        = string
}

variable "monthly_budget_usd" {
  description = "월 예산 (USD) — 임계점 초과 시 알람"
  type        = number
  default     = 100
}

variable "brand_ids" {
  description = "초기 본사 ID 리스트 (KMS 키 생성용)"
  type        = list(string)
  default     = ["brand-001", "brand-002"]
}

variable "terraform_service_account" {
  description = "Terraform Service Account 이메일"
  type        = string
}

# ===================================================================
# 공통 라벨 (모든 리소스 부착)
# ===================================================================

locals {
  environment = "production"
  
  common_labels = {
    project     = "tryops"
    environment = local.environment
    managed_by  = "terraform"
  }
}

# ===================================================================
# 모듈 호출
# ===================================================================

# 1. Networking
module "networking" {
  source = "../../modules/networking"
  
  project_id    = var.project_id
  environment   = local.environment
  region        = var.region
  common_labels = local.common_labels
}

# 2. Storage (Cloud Storage + KMS)
module "storage" {
  source = "../../modules/storage"
  
  project_id    = var.project_id
  environment   = local.environment
  region        = var.region
  common_labels = local.common_labels
  brand_ids     = var.brand_ids
}

# 3. Data (Pub/Sub + BigQuery)
module "data" {
  source = "../../modules/data"
  
  project_id                = var.project_id
  environment               = local.environment
  region                    = var.region
  common_labels             = local.common_labels
  terraform_service_account = var.terraform_service_account
}

# 4. Compute (Compute Engine + Cloud Run)
module "compute" {
  source = "../../modules/compute"
  
  project_id          = var.project_id
  environment         = local.environment
  region              = var.region
  zone                = var.zone
  common_labels       = local.common_labels
  subnet_id           = module.networking.subnet_id
  subnet_self_link    = module.networking.subnet_self_link
  pubsub_topic_id     = module.data.pubsub_topic_id
  bigquery_dataset_id = module.data.bigquery_dataset_id
  
  depends_on = [
    module.networking,
    module.data
  ]
}

# 5. API (Identity Platform + Artifact Registry)
module "api" {
  source = "../../modules/api"
  
  project_id         = var.project_id
  environment        = local.environment
  region             = var.region
  common_labels      = local.common_labels
  ingest_service_url = module.compute.ingest_service_url
  query_service_url  = module.compute.query_service_url
}

# 6. Security (Secret Manager + Cloud Armor + Audit Logs)
module "security" {
  source = "../../modules/security"
  
  project_id    = var.project_id
  environment   = local.environment
  region        = var.region
  common_labels = local.common_labels
}

# 7. Monitoring (비용 대시보드 + 알람)
module "monitoring" {
  source = "../../modules/monitoring"
  
  project_id         = var.project_id
  environment        = local.environment
  common_labels      = local.common_labels
  billing_account_id = var.billing_account_id
  alert_email        = var.alert_email
  monthly_budget_usd = var.monthly_budget_usd
}

# ===================================================================
# Outputs — 다른 도구·SW가 참조할 값
# ===================================================================

output "vpc_name" {
  value = module.networking.vpc_name
}

output "pubsub_topic" {
  value = module.data.pubsub_topic_name
}

output "bigquery_dataset" {
  value = module.data.bigquery_dataset_id
}

output "ingest_url" {
  value = module.compute.ingest_service_url
}

output "query_url" {
  value = module.compute.query_service_url
}

output "artifact_registry_url" {
  value = module.api.artifact_registry_url
}

output "billing_export_setup_instructions" {
  value = module.monitoring.billing_export_setup_required
}

output "store_gateway_service_account_email" {
  value       = module.compute.store_gateway_service_account_email
  description = "매장 게이트웨이가 Cloud Run Ingest 호출 시 사용할 Service Account"
}
