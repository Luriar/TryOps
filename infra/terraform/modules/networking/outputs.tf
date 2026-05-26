output "vpc_id" {
  value = google_compute_network.main.id
}

output "vpc_name" {
  value = google_compute_network.main.name
}

output "subnet_id" {
  value = google_compute_subnetwork.private.id
}

output "subnet_self_link" {
  value = google_compute_subnetwork.private.self_link
}
