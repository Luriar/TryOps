# TryOps Terraform Infrastructure

This directory contains the Terraform IaC (Infrastructure as Code) for the TryOps GCP environment.

## Prerequisites

Before running Terraform, ensure the following manual steps are completed in your GCP Project:
1. **Enable Billing Export**: 
   - Terraform *cannot* fully automate the creation of GCP Billing Export to BigQuery.
   - Go to GCP Console -> Billing -> Billing export -> BigQuery export.
   - Edit settings and point it to the project and `billing_export` dataset created by Terraform (you may need to run Terraform once to create the dataset, or manually create it first).
2. **GCS State Bucket**:
   - Create a GCS bucket to store Terraform state (e.g. `tryops-tf-state-dev`).
3. **IAM Permissions**:
   - The Service Account running Terraform requires Owner or Editor + Security Admin.

## Deployment

To deploy, initialize Terraform pointing to your state bucket:

```bash
cd environments/dev
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init -backend-config="bucket=tryops-tf-state-dev" -backend-config="prefix=terraform/state/dev"
terraform plan
terraform apply
```

## Structure
- `modules/`: Reusable Terraform modules.
- `environments/`: Environment-specific configurations (`dev`, `staging`, `production`).
