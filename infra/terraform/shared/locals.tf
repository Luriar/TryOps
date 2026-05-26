/**
 * TryOps Terraform Shared Locals
 * 
 * 본 파일은 모든 환경 (dev·staging·production) 에서 공유되는 상수 정의.
 * 비용 추적 라벨 표준 + 리전 + 프로젝트 명명 규칙.
 */

locals {
  # 비용 추적 표준 라벨 — 모든 GCP 리소스에 부착
  # GCP Billing Export → BigQuery 에서 라벨 기준 비용 분석 가능
  common_labels = {
    project     = "tryops"
    managed_by  = "terraform"
    environment = var.environment  # production | staging | dev
  }

  # 리전 표준 — asia-northeast3 (서울)
  region = "asia-northeast3"
  zone   = "asia-northeast3-a"
  
  # 멀티 리전 (BigQuery·Cloud Storage 옵션)
  multi_region = "asia-northeast3"
  
  # 명명 규칙 — 모든 리소스명에 환경 prefix 부착
  resource_prefix = "tryops-${var.environment}"
}
