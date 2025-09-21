output "bucket_name" {
  description = "Name of the created S3 bucket"
  value       = aws_s3_bucket.terraform_state.bucket
}

output "bucket_region" {
  description = "Region of the S3 bucket"
  value       = var.aws_region
}