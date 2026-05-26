output "pubsub_topic_id" {
  value = google_pubsub_topic.store_events.id
}

output "pubsub_topic_name" {
  value = google_pubsub_topic.store_events.name
}

output "bigquery_dataset_id" {
  value = google_bigquery_dataset.tryops_data.dataset_id
}

output "bigquery_raw_events_table" {
  value = "${var.project_id}.${google_bigquery_dataset.tryops_data.dataset_id}.${google_bigquery_table.raw_events.table_id}"
}

output "bigquery_joint_signals_table" {
  value = "${var.project_id}.${google_bigquery_dataset.tryops_data.dataset_id}.${google_bigquery_table.joint_signals.table_id}"
}

output "billing_export_dataset_id" {
  value = google_bigquery_dataset.billing_export.dataset_id
}
