variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast3"
}

variable "common_labels" {
  description = "Common labels"
  type        = map(string)
}

variable "ingest_service_url" {
  description = "Cloud Run Ingest URL"
  type        = string
}

variable "query_service_url" {
  description = "Cloud Run Query URL"
  type        = string
}
