/**
 * Storage Module
 * 
 * Cloud Storage 버킷 + Cloud KMS 키
 * 본사별 격리·암호화 설계
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

variable "brand_ids" {
  description = "List of brand IDs to provision KMS keys for"
  type        = list(string)
  default     = []
}

locals {
  module_labels = merge(var.common_labels, {
    module      = "storage"
    cost_center = "core"
  })
}

# KMS Keyring
resource "google_kms_key_ring" "main" {
  project  = var.project_id
  name     = "tryops-${var.environment}-keyring"
  location = var.region
}

# Brand별 KMS Key (data_governance.md 섹션 3.1 시나리오 1 — 본사 계약 종료 시 키 폐기로 데이터 즉시 불가)
resource "google_kms_crypto_key" "brand_keys" {
  for_each = toset(var.brand_ids)
  
  name            = "brand-${each.value}-data-key"
  key_ring        = google_kms_key_ring.main.id
  rotation_period = "7776000s"  # 90일 자동 회전
  purpose         = "ENCRYPT_DECRYPT"
  
  labels = merge(local.module_labels, {
    brand_id    = each.value
    cost_center = "core"
  })
  
  lifecycle {
    prevent_destroy = true
  }
}

# 매장 게이트웨이 SQLite 백업 버킷
resource "google_storage_bucket" "store_backups" {
  project       = var.project_id
  name          = "tryops-${var.environment}-store-backups"
  location      = var.region
  force_destroy = false  # 실수로 삭제 방지
  
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 7  # 7일 후 자동 삭제 (data_governance.md 보존 정책)
    }
    action {
      type = "Delete"
    }
  }
  
  labels = merge(local.module_labels, {
    cost_center = "ingest"
    data_class  = "L3-restricted"  # data_governance.md 섹션 1.2 분류
  })
}

# 보고서 보관 버킷 (3년 보존)
resource "google_storage_bucket" "reports" {
  project       = var.project_id
  name          = "tryops-${var.environment}-reports"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  lifecycle_rule {
    condition {
      age = 1095  # 3년
    }
    action {
      type = "Delete"
    }
  }
  
  labels = merge(local.module_labels, {
    cost_center = "dashboard"
    data_class  = "L2-confidential"
  })
}

# Terraform state 백업 버킷
resource "google_storage_bucket" "terraform_state" {
  project       = var.project_id
  name          = "tryops-${var.environment}-terraform-state"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  
  versioning {
    enabled = true
  }
  
  labels = merge(local.module_labels, {
    cost_center = "core"
    purpose     = "terraform-state"
  })
}

# Outputs
output "kms_keyring_id" {
  value = google_kms_key_ring.main.id
}

output "brand_key_ids" {
  value = { for k, v in google_kms_crypto_key.brand_keys : k => v.id }
}

output "store_backups_bucket" {
  value = google_storage_bucket.store_backups.name
}

output "reports_bucket" {
  value = google_storage_bucket.reports.name
}

output "terraform_state_bucket" {
  value = google_storage_bucket.terraform_state.name
}
