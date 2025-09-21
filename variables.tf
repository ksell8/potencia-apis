variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "api_name" {
  description = "Name of the API Gateway"
  type        = string
  default     = "custom-api"
}

variable "api_key_secret_name" {
  description = "Name of the Secrets Manager secret containing the API key"
  type        = string
  default     = "/api/token"
}

variable "airtable_secret_name" {
  description = "Name of the Secrets Manager secret containing the Airtable API key"
  type        = string
  default     = "/api/token/airtable"
}