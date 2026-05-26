output "store_gateway_api_keys_secret_id" {
  value = google_secret_manager_secret.store_gateway_api_keys.secret_id
}

output "armor_policy_id" {
  value = google_compute_security_policy.main.id
}

output "audit_logs_dataset_id" {
  value = google_bigquery_dataset.audit_logs.dataset_id
}
output "store_gw_sa_email" {
  value = google_service_account.store_gw.email
}

output "ingest_sa_email" {
  value = google_service_account.ingest.email
}
