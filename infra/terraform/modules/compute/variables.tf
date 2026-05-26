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

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "asia-northeast3-a"
}

variable "common_labels" {
  description = "Common labels"
  type        = map(string)
}

variable "subnet_id" {
  description = "VPC Subnet ID"
  type        = string
}

variable "subnet_self_link" {
  description = "VPC Subnet self link"
  type        = string
}

variable "pubsub_topic_id" {
  description = "Pub/Sub topic ID"
  type        = string
}

variable "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}
