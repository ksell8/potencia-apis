# Data sources
data "aws_caller_identity" "current" {}

# Read OpenAPI spec and replace variables
locals {
  openapi_spec = templatefile("${path.module}/openapi.yaml", {
    authorizer_uri = aws_lambda_function.authorizer.invoke_arn
    lambda_uri     = aws_lambda_function.verifier.invoke_arn
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

# IAM policy for main Lambda to access Airtable secret and DynamoDB
resource "aws_iam_role_policy" "lambda_main_policy" {
  name = "${var.api_name}-main-policy"
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
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.matches.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.matches.arn
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
  role             = aws_iam_role.lambda_authorizer_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.14"
  timeout          = 30
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

# IAM role for verifier Lambda function
resource "aws_iam_role" "lambda_verifier_role" {
  name = "${var.api_name}-verifier-role"

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

# IAM policy for verifier Lambda to access SQS and DynamoDB
resource "aws_iam_role_policy" "lambda_verifier_policy" {
  name = "${var.api_name}-verifier-policy"
  role = aws_iam_role.lambda_verifier_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.matches.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
        ]
        Resource = aws_dynamodb_table.matches.arn
      }
    ]
  })
}

# Attach basic execution role to verifier Lambda
resource "aws_iam_role_policy_attachment" "lambda_verifier_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_verifier_role.name
}

# Verifier Lambda function
resource "aws_lambda_function" "verifier" {
  filename         = "verifier.zip"
  function_name    = "${var.api_name}-verifier"
  role             = aws_iam_role.lambda_verifier_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.14"
  timeout          = 30
  source_code_hash = filebase64sha256("verifier.zip")

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.matches.url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_verifier_basic_execution,
    aws_cloudwatch_log_group.verifier_logs,
  ]
}

# Main Lambda function
resource "aws_lambda_function" "main" {
  filename         = "main.zip"
  function_name    = "${var.api_name}-main"
  role             = aws_iam_role.lambda_main_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.14"
  timeout          = 30
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

resource "aws_cloudwatch_log_group" "verifier_logs" {
  name              = "/aws/lambda/${var.api_name}-verifier"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "main_logs" {
  name              = "/aws/lambda/${var.api_name}-main"
  retention_in_days = 14
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
resource "aws_lambda_permission" "api_gateway_authorizer" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/authorizers/*"
}


resource "aws_lambda_permission" "api_gateway_verifier" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verifier.function_name
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
resource "aws_api_gateway_stage" "potencia" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = "potencia"
}

# SQS Queue for Creating Match
resource "aws_sqs_queue" "matches" {
  name                      = "matches"
  delay_seconds             = 90
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.matches_dlq.arn
    maxReceiveCount     = 4
  })
}

resource "aws_sqs_queue" "matches_dlq" {
  name = "matches-dlq"
}

resource "aws_lambda_event_source_mapping" "matches" {
  event_source_arn = aws_sqs_queue.matches.arn
  function_name    = aws_lambda_function.main.arn
}

resource "aws_dynamodb_table" "matches" {
  name         = "matches-queue"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "MatchComboId"

  attribute {
    name = "MatchComboId"
    type = "S"
  }

  ttl {
    attribute_name = "MatchRequestExpiry"
    enabled        = true
  }
}
