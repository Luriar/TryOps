/**
 * API Module
 * 
 * Cloud Endpoints (API 관리) + Identity Platform (인증)
 * 본사 사용자 + 매장 매니저 멀티테넌트 인증
 */

locals {
  module_labels = merge(var.common_labels, {
    module      = "api"
    cost_center = "core"
  })
}

# ===================================================================
# Identity Platform (Firebase Auth 기반)
# ===================================================================

# Identity Platform은 Terraform google provider에서 일부 리소스만 지원
# 멀티테넌트 활성화는 콘솔에서 진행 후 Terraform으로 import 권장

resource "google_identity_platform_config" "auth" {
  project = var.project_id
  
  autodelete_anonymous_users = true
  
  # 멀티테넌트 활성화
  multi_tenant {
    allow_tenants           = true
    default_tenant_location = "projects/${var.project_id}"
  }
  
  sign_in {
    allow_duplicate_emails = false
    
    email {
      enabled           = true
      password_required = true
    }
  }
}

# Brand별 Tenant 생성 (예시 — 실제 본사 추가는 별도)
# 실제 운영에서는 google_identity_platform_tenant 리소스로 본사별 tenant 자동 생성
resource "google_identity_platform_tenant" "demo_brand" {
  count = var.environment == "dev" ? 1 : 0  # dev 환경만 demo tenant 생성
  
  project      = var.project_id
  display_name = "Demo Brand"
}

# ===================================================================
# Artifact Registry (Docker 이미지 저장소)
# ===================================================================

resource "google_artifact_registry_repository" "main" {
  project       = var.project_id
  location      = var.region
  repository_id = "tryops-${var.environment}"
  description   = "TryOps Docker images"
  format        = "DOCKER"
  
  labels = merge(local.module_labels, {
    cost_center = "core"
    purpose     = "docker-registry"
  })
  
  cleanup_policies {
    id     = "keep-recent-50"
    action = "KEEP"
    
    most_recent_versions {
      keep_count = 50
    }
  }
  
  cleanup_policies {
    id     = "delete-untagged-after-30d"
    action = "DELETE"
    
    condition {
      tag_state  = "UNTAGGED"
      older_than = "2592000s"  # 30일
    }
  }
}

# Outputs
