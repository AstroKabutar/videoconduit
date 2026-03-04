terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
  }
}

provider "aws" {
  region = var.region
}

# ------------------- Lambda that generates presigned POST url for s3 upload ------------------- #

resource "aws_iam_role" "urlpost_lambda_role" {
  name = "${var.lambda_name}-role"

  tags = {
    Purpose = "IAM role for presigned POST URL Lambda"
    Project = "videoconduit"
  }

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "urlpost_lambda_s3_put" {
  name   = "${var.lambda_name}-s3-put"
  role   = aws_iam_role.urlpost_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${var.bucket_arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "urlpost_lambda_dynamodb" {
  name   = "${var.lambda_name}-dynamodb-put"
  role   = aws_iam_role.urlpost_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = "arn:aws:dynamodb:${var.region}:*:table/${var.table_name}"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "urlpost_lambda_basic_execution" {
  role       = aws_iam_role.urlpost_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "urlpost_lambda" {
  function_name = var.lambda_name
  role          = aws_iam_role.urlpost_lambda_role.arn
  handler       = "generate_presigned_post.handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  filename      = "generate_presigned_post.zip"

  memory_size = 1024
  timeout    = 30

  ephemeral_storage {
    size = 512
  }

  environment {
    variables = {
      BUCKET_NAME  = var.bucket_name
      TABLE_NAME   = var.table_name
      PARTITION_KEY = var.partition_key
      SORT_KEY     = var.sort_key
      REGION       = var.region
    }
  }


  tags = {
    Purpose = "presigned POST url for s3 upload"
    Project = "videoconduit"
  }
}

resource "aws_cloudwatch_log_group" "lambda_urlpost" {
  name              = "/aws/lambda/${var.lambda_name}"
  retention_in_days = 90

  tags = {
    Purpose = "generate presigned POST url logs"
    Project = "videoconduit"
  }
}

# ------------------- Lambda for SES identity creation and validation ------------------- #

resource "aws_iam_role" "ses_lambda_role" {
  name = "${var.lambda_ses_name}-role"

  tags = {
    Purpose = "IAM role for SES identity creation Lambda"
    Project = "videoconduit"
  }

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ses_lambda_ses" {
  name   = "${var.lambda_ses_name}-ses"
  role   = aws_iam_role.ses_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ses:CreateEmailIdentity", "ses:GetEmailIdentity"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ses_lambda_basic_execution" {
  role       = aws_iam_role.ses_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "ses_lambda" {
  function_name = var.lambda_ses_name
  role          = aws_iam_role.ses_lambda_role.arn
  handler       = "create_ses_identity.handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  filename      = "create_ses_identity.zip"

  memory_size = 256
  timeout     = 30

  ephemeral_storage {
    size = 512
  }

  environment {
    variables = {
      REGION = var.region
    }
  }

  tags = {
    Purpose = "SES identity creation and validation"
    Project = "videoconduit"
  }
}

resource "aws_cloudwatch_log_group" "lambda_ses" {
  name              = "/aws/lambda/${var.lambda_ses_name}"
  retention_in_days = 90

  tags = {
    Purpose = "SES identity creation logs"
    Project = "videoconduit"
  }
}

# ------------------- API Gateway ------------------- #

resource "aws_api_gateway_rest_api" "triggerlambdaurlpost" {
  name        = var.api_gateway_name
  description = "API Gateway to trigger presigned POST URL generation"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Purpose = "trigger lambda for presigned POST"
    Project = "videoconduit"
  }
}

resource "aws_api_gateway_resource" "presigned" {
  rest_api_id = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  parent_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.root_resource_id
  path_part   = "presigned"
}

resource "aws_api_gateway_resource" "email" {
  rest_api_id = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  parent_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.root_resource_id
  path_part   = "email"
}

resource "aws_api_gateway_method" "get_presigned" {
  rest_api_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id   = aws_api_gateway_resource.presigned.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "options_presigned" {
  rest_api_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id   = aws_api_gateway_resource.presigned.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id             = aws_api_gateway_resource.presigned.id
  http_method             = aws_api_gateway_method.get_presigned.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.urlpost_lambda.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_options" {
  rest_api_id             = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id             = aws_api_gateway_resource.presigned.id
  http_method             = aws_api_gateway_method.options_presigned.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.urlpost_lambda.invoke_arn
}

# ------------------- /email resource (SES identity creation) ------------------- #

resource "aws_api_gateway_method" "email_post" {
  rest_api_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id   = aws_api_gateway_resource.email.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "email_get" {
  rest_api_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id   = aws_api_gateway_resource.email.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "email_options" {
  rest_api_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id   = aws_api_gateway_resource.email.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "email_post" {
  rest_api_id             = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id             = aws_api_gateway_resource.email.id
  http_method             = aws_api_gateway_method.email_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ses_lambda.invoke_arn
}

resource "aws_api_gateway_integration" "email_get" {
  rest_api_id             = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id             = aws_api_gateway_resource.email.id
  http_method             = aws_api_gateway_method.email_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ses_lambda.invoke_arn
}

resource "aws_api_gateway_integration" "email_options" {
  rest_api_id             = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  resource_id             = aws_api_gateway_resource.email.id
  http_method             = aws_api_gateway_method.email_options.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ses_lambda.invoke_arn
}

resource "aws_lambda_permission" "api_gateway_ses" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ses_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.triggerlambdaurlpost.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.urlpost_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.triggerlambdaurlpost.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.triggerlambdaurlpost.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.presigned.id,
      aws_api_gateway_resource.email.id,
      aws_api_gateway_method.get_presigned.id,
      aws_api_gateway_method.options_presigned.id,
      aws_api_gateway_method.email_post.id,
      aws_api_gateway_method.email_get.id,
      aws_api_gateway_method.email_options.id,
      aws_api_gateway_integration.lambda.id,
      aws_api_gateway_integration.lambda_options.id,
      aws_api_gateway_integration.email_post.id,
      aws_api_gateway_integration.email_get.id,
      aws_api_gateway_integration.email_options.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_method.get_presigned,
    aws_api_gateway_method.options_presigned,
    aws_api_gateway_method.email_post,
    aws_api_gateway_method.email_get,
    aws_api_gateway_method.email_options,
    aws_api_gateway_integration.lambda,
    aws_api_gateway_integration.lambda_options,
    aws_api_gateway_integration.email_post,
    aws_api_gateway_integration.email_get,
    aws_api_gateway_integration.email_options,
  ]
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.triggerlambdaurlpost.id
  stage_name   = "prod"

  tags = {
    Purpose = "API Gateway prod stage for presigned POST"
    Project = "videoconduit"
  }
}
