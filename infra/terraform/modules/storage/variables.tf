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

variable "brand_ids" {
  description = "List of brand IDs to provision KMS keys for"
  type        = list(string)
  default     = []
}
