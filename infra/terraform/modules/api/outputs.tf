output "identity_platform_config_name" {
  value = google_identity_platform_config.auth.name
}

output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}"
}
