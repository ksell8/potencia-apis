output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = "${aws_api_gateway_stage.prod.invoke_url}"
}

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_api_gateway_rest_api.main.id
}

output "lambda_authorizer_function_name" {
  description = "Name of the Lambda authorizer function"
  value       = aws_lambda_function.authorizer.function_name
}

output "lambda_main_function_name" {
  description = "Name of the main Lambda function"
  value       = aws_lambda_function.main.function_name
}

output "authorizer_secret_name" {
  description = "Name of the authorizer secret in Secrets Manager"
  value       = var.api_key_secret_name
}

output "airtable_secret_name" {
  description = "Name of the Airtable secret in Secrets Manager"
  value       = var.airtable_secret_name
}