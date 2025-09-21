# Data sources
data "aws_caller_identity" "current" {}

# Read OpenAPI spec and replace variables
locals {
  openapi_spec = templatefile("${path.module}/openapi.yaml", {
    authorizer_uri         = aws_lambda_function.authorizer.invoke_arn
    authorizer_credentials = aws_iam_role.api_gateway_invocation_role.arn
    lambda_uri            = aws_lambda_function.main.invoke_arn
  })
}

# IAM role for Lambda authorizer
resource "aws_iam_role" "lambda_authorizer_role" {
  name = "${var.api_name}-authorizer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Lambda authorizer to access Secrets Manager
resource "aws_iam_role_policy" "lambda_authorizer_secrets_policy" {
  name = "${var.api_name}-authorizer-secrets-policy"
  role = aws_iam_role.lambda_authorizer_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.api_key_secret_name}*"
      }
    ]
  })
}

# Attach basic execution role to authorizer
resource "aws_iam_role_policy_attachment" "lambda_authorizer_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_authorizer_role.name
}

# IAM role for main Lambda function
resource "aws_iam_role" "lambda_main_role" {
  name = "${var.api_name}-main-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for main Lambda to access Airtable secret
resource "aws_iam_role_policy" "lambda_main_secrets_policy" {
  name = "${var.api_name}-main-secrets-policy"
  role = aws_iam_role.lambda_main_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.airtable_secret_name}*"
      }
    ]
  })
}

# Attach basic execution role to main Lambda
resource "aws_iam_role_policy_attachment" "lambda_main_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_main_role.name
}

# Lambda authorizer function
resource "aws_lambda_function" "authorizer" {
  filename         = "authorizer.zip"
  function_name    = "${var.api_name}-authorizer"
  role            = aws_iam_role.lambda_authorizer_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.13"
  timeout         = 30
  source_code_hash = filebase64sha256("authorizer.zip")

  environment {
    variables = {
      SECRET_NAME = var.api_key_secret_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_authorizer_basic_execution,
    aws_cloudwatch_log_group.authorizer_logs,
  ]
}

# Main Lambda function
resource "aws_lambda_function" "main" {
  filename         = "main.zip"
  function_name    = "${var.api_name}-main"
  role            = aws_iam_role.lambda_main_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.13"
  timeout         = 30
  source_code_hash = filebase64sha256("main.zip")

  environment {
    variables = {
      AIRTABLE_SECRET_NAME = var.airtable_secret_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_main_basic_execution,
    aws_cloudwatch_log_group.main_logs,
  ]
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "authorizer_logs" {
  name              = "/aws/lambda/${var.api_name}-authorizer"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "main_logs" {
  name              = "/aws/lambda/${var.api_name}-main"
  retention_in_days = 14
}

# IAM role for API Gateway to invoke Lambda authorizer
resource "aws_iam_role" "api_gateway_invocation_role" {
  name = "${var.api_name}-api-gateway-auth-invocation"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "api_gateway_invocation_policy" {
  name = "${var.api_name}-api-gateway-auth-invocation"
  role = aws_iam_role.api_gateway_invocation_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "lambda:InvokeFunction"
        Effect   = "Allow"
        Resource = aws_lambda_function.authorizer.arn
      }
    ]
  })
}

# API Gateway REST API with OpenAPI specification
resource "aws_api_gateway_rest_api" "main" {
  name        = var.api_name
  description = "API Gateway for Airtable operations with custom authorization"
  body        = local.openapi_spec

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway_main" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.main.body))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = "prod"
}