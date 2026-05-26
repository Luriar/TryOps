output "billing_export_setup_required" {
  value = <<-EOT
  ⚠️  Billing Export 활성화 필수 (Terraform으로 자동 안 됨)
  
  1. GCP Console → Billing → Billing Export → BigQuery Export 클릭
  2. 다음 데이터셋 선택: 'billing_export' (이미 생성됨)
  3. "Detailed usage cost data" 체크
  4. 활성화
  5. 24시간 내 첫 데이터 적재
  
  비용 분석 쿼리는 gcp_architecture.md 섹션 6.4 참조.
  EOT
}

output "email_alert_channel_id" {
  value = google_monitoring_notification_channel.email.id
}

output "cost_dashboard_id" {
  value = google_monitoring_dashboard.cost.id
}

output "monthly_budget_id" {
  value = google_billing_budget.monthly_budget.id
}
