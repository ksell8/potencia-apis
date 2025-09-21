variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Base name for the S3 bucket (random suffix will be added)"
  type        = string
  default     = "potencia-terraform-state"
}