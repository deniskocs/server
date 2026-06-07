terraform {
  required_version = ">= 1.5.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.35"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.17"
    }
  }

  # Remote state — после bootstrap (server/infra/terraform), раскомментировать и подставить bucket:
  # backend "s3" {
  #   bucket = "server-terraform-state-<ACCOUNT_ID>"
  #   key    = "k8s/platform/terraform.tfstate"
  #   region = "us-east-1"
  # }
}
