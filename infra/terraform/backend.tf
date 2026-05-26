terraform {
  backend "gcs" {
    # The bucket name should be provided via init arguments:
    # terraform init -backend-config="bucket=tryops-tf-state-YOUR-ENV" -backend-config="prefix=terraform/state"
    # bucket = "..."
    # prefix = "terraform/state"
  }
}
