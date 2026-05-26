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
