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
