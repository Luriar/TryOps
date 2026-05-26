variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "common_labels" {
  description = "Common labels"
  type        = map(string)
}

variable "billing_account_id" {
  description = "GCP Billing Account ID (X-X-X 형식)"
  type        = string
}

variable "alert_email" {
  description = "비용 알람 이메일"
  type        = string
}

variable "monthly_budget_usd" {
  description = "월 예산 (USD)"
  type        = number
  default     = 100  # PoC 단계 기본
}
