/**
 * Dev Environment
 * 
 * 개발자 로컬 테스트용. Production 대비:
 * - deletion_protection 비활성화 (실수로 삭제해도 복구 쉬움)
 * - 더 작은 인스턴스
 * - 더 작은 예산
 * - Production과 별도 GCP Project
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
  
  backend "gcs" {
    bucket = "tryops-dev-terraform-state"
    prefix = "dev"
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
  description = "GCP Project ID (dev)"
  type        = string
}

variable "region" {
  type    = string
  default = "asia-northeast3"
}

variable "zone" {
  type    = string
  default = "asia-northeast3-a"
}

variable "billing_account_id" {
  type = string
}

variable "alert_email" {
  type    = string
  default = "dev-alerts@tryops.io"
}

variable "terraform_service_account" {
  type = string
}

# ===================================================================
# 공통 라벨
# ===================================================================

locals {
  environment = "dev"
  
  common_labels = {
    project     = "tryops"
    environment = local.environment
    managed_by  = "terraform"
  }
}

# ===================================================================
# 모듈 호출 (production 동일 구조, 변수만 다름)
# ===================================================================

module "networking" {
  source = "../../modules/networking"
  
  project_id    = var.project_id
  environment   = local.environment
  region        = var.region
  common_labels = local.common_labels
}

module "storage" {
  source = "../../modules/storage"
  
  project_id    = var.project_id
  environment   = local.environment
  region        = var.region
  common_labels = local.common_labels
  brand_ids     = ["demo-brand-001"]  # dev는 demo 본사만
}

module "data" {
  source = "../../modules/data"
  
  project_id                = var.project_id
  environment               = local.environment
  region                    = var.region
  common_labels             = local.common_labels
  terraform_service_account = var.terraform_service_account
}

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
}

module "api" {
  source = "../../modules/api"
  
  project_id         = var.project_id
  environment        = local.environment
  region             = var.region
  common_labels      = local.common_labels
  ingest_service_url = module.compute.ingest_service_url
  query_service_url  = module.compute.query_service_url
}

module "security" {
  source = "../../modules/security"
  
  project_id    = var.project_id
  environment   = local.environment
  region        = var.region
  common_labels = local.common_labels
}

module "monitoring" {
  source = "../../modules/monitoring"
  
  project_id         = var.project_id
  environment        = local.environment
  common_labels      = local.common_labels
  billing_account_id = var.billing_account_id
  alert_email        = var.alert_email
  monthly_budget_usd = 30  # dev는 예산 작게 ($30/월)
}

# ===================================================================
# Outputs
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

output "artifact_registry_url" {
  value = module.api.artifact_registry_url
}
