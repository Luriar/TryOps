/**
 * Networking Module
 * 
 * VPC + Subnet + Firewall 규칙
 * Compute Engine·Cloud Run 등에 격리된 네트워크 환경 제공.
 */

locals {
  module_labels = merge(var.common_labels, {
    module      = "networking"
    cost_center = "core"
  })
}

# VPC
resource "google_compute_network" "main" {
  project                 = var.project_id
  name                    = "tryops-${var.environment}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  
  # GCP는 VPC 자체에 labels 부착 불가, 대신 description으로 추적
  description = jsonencode(local.module_labels)
}

# Subnet — Compute Engine·Cloud Run용
resource "google_compute_subnetwork" "private" {
  project       = var.project_id
  name          = "tryops-${var.environment}-private-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.main.id
  
  private_ip_google_access = true  # GCP API 호출 시 internet 우회
  
  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud NAT — Compute Engine outbound (외부 API·apt 등)
resource "google_compute_router" "nat_router" {
  project = var.project_id
  name    = "tryops-${var.environment}-nat-router"
  network = google_compute_network.main.id
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = "tryops-${var.environment}-nat"
  router                             = google_compute_router.nat_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Firewall — 매장 게이트웨이 IP 화이트리스트 (Cloud Run은 IAM 기반이므로 firewall 불요)
resource "google_compute_firewall" "allow_internal" {
  project = var.project_id
  name    = "tryops-${var.environment}-allow-internal"
  network = google_compute_network.main.name
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  allow {
    protocol = "icmp"
  }
  
  source_ranges = ["10.0.0.0/24"]
  
  description = "Allow internal VPC traffic"
}

# Firewall — SSH 차단 (security_design.md 대응 1 - 매장 게이트웨이는 별도 VPN)
resource "google_compute_firewall" "deny_ssh_external" {
  project = var.project_id
  name    = "tryops-${var.environment}-deny-ssh"
  network = google_compute_network.main.name
  
  deny {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  source_ranges = ["0.0.0.0/0"]
  priority      = 1000
  
  description = "Deny external SSH (use IAP tunnel)"
}

# IAP Tunnel용 firewall — Cloud Identity-Aware Proxy 통한 안전한 SSH
resource "google_compute_firewall" "allow_iap_ssh" {
  project = var.project_id
  name    = "tryops-${var.environment}-allow-iap-ssh"
  network = google_compute_network.main.name
  
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  source_ranges = ["35.235.240.0/20"]  # IAP IP 범위
  priority      = 900
  
  description = "Allow SSH via IAP only"
}

# Outputs
