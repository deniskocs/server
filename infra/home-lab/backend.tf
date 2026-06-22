terraform {
  backend "s3" {
    bucket = "deniskocs-terraform-states"
    key    = "home-lab/terraform.tfstate"
    region = "us-east-1"
  }
}
