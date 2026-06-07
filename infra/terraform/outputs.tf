output "state_bucket_name" {
  description = "S3 bucket для remote Terraform state."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN bucket state."
  value       = aws_s3_bucket.terraform_state.arn
}

output "backend_config_example" {
  description = "Фрагмент backend для других стеков (подставьте key на стек)."
  value       = <<-EOT
    terraform {
      backend "s3" {
        bucket = "${aws_s3_bucket.terraform_state.id}"
        key    = "<stack>/terraform.tfstate"
        region = "us-east-1"
      }
    }
  EOT
}
