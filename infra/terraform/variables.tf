variable "bucket_name" {
  description = "Имя S3 bucket. По умолчанию server-terraform-state-<account_id> (глобально уникально)."
  type        = string
  default     = null
}
