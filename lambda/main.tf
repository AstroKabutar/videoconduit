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

# ------------------- Lambda that generates presigned get url for s3 object /converted ------------------- #

resource "aws_iam_role" "geturl_lambda_role" {
  name = "${var.geturllambda}-role"

  tags = {
    Purpose = "IAM role for presigned GET URL Lambda"
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

resource "aws_iam_role_policy" "geturl_lambda_s3_get" {
  name   = "${var.geturllambda}-s3-get"
  role   = aws_iam_role.geturl_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${var.bucket_arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "geturl_lambda_basic_execution" {
  role       = aws_iam_role.geturl_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "geturl_lambda_ses" {
  name   = "${var.geturllambda}-ses"
  role   = aws_iam_role.geturl_lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ses:SendEmail", "ses:DeleteEmailIdentity"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "geturl_lambda" {
  function_name = var.geturllambda
  role          = aws_iam_role.geturl_lambda_role.arn
  handler       = "generate_presigned_url.finisher"
  runtime       = "python3.12"
  architectures = ["arm64"]
  filename      = "finisher.zip"

  memory_size   = 1024
  timeout       = 120

  ephemeral_storage {
    size = 512
  }

  environment {
    variables = {
      TABLE_NAME        = var.table_name
      PARTITION_KEY     = "email"
      SORT_KEY          = "name"
      REGION            = var.region
      SES_SENDER_EMAIL  = var.ses_sender_email
    }
  }

  tags = {
    Purpose = "presigned get url for s3 object"
    Project = "videoconduit"
  }
}

# ------------------ Create media convert role for iam:PassRole ----------------- #
resource "aws_iam_role" "mediaconvert_role" {
  name = var.mediaconvertrole

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "MediaConvertRoletobeAssumed"
        Effect = "Allow"
        Principal = {
          Service = "mediaconvert.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Purpose = "This role is to be assumed by media convert as passed from lambda to let the job run"
    Project = "videoconduit"
  }
}

resource "aws_iam_policy" "mediaconvert_policy" {
  name = "${var.mediaconvertrole}_policy"

  tags = {
    Purpose = "S3 read/write policy for MediaConvert jobs"
    Project = "videoconduit"
  }

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::446636301131-videoconduit-storage/upload/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::446636301131-videoconduit-storage/converted/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "mediaconvert_role_attach" {
  role       = aws_iam_role.mediaconvert_role.name
  policy_arn = aws_iam_policy.mediaconvert_policy.arn
}

resource "aws_iam_policy" "lambda_mediaconvert_policy" {
  name        = "lambda_mediaconvert_policy"
  description = "Policy for Lambda to access MediaConvert and PassRole for MediaConvert jobs"

  tags = {
    Purpose = "Lambda MediaConvert and PassRole access"
    Project = "videoconduit"
  }

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "MediaConvertAccess",
        Effect = "Allow",
        Action = [
          "mediaconvert:DescribeEndpoints",
          "mediaconvert:CreateJob"
        ],
        Resource = "*"
      },
      {
        Sid = "PassMediaConvertRole",
        Effect = "Allow",
        Action = "iam:PassRole",
        Resource = aws_iam_role.mediaconvert_role.arn,
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "mediaconvert.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_mediaconvert_policy_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_mediaconvert_policy.arn
}


# ------------------- Cloudwatch logs lambda ------------------- #

resource "aws_cloudwatch_log_group" "lambda_conversion" {
  name              = "/aws/lambda/${var.trigger_media_convert_job_name}"
  retention_in_days = 90

  tags = {
    Purpose = "convert media lambda logs"
    Project = "videoconduit"
  }
}

resource "aws_cloudwatch_log_group" "lambda_generate_presigned_url" {
  name              = "/aws/lambda/${var.geturllambda}"
  retention_in_days = 90

  tags = {
    Purpose = "generate presigned url logs"
    Project = "videoconduit"
  }
}

# ------------------- Lambda function that submits job ------------ #
resource "aws_lambda_function" "conversion_lambda" {
  function_name = var.trigger_media_convert_job_name
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "submitjob.submitjob"
  runtime       = "python3.12"
  architectures = ["arm64"]

  memory_size   = 1024
  timeout       = 120

  ephemeral_storage {
    size = 512
  }

  package_type = "Zip"
  filename     = "submitjob.zip"

  environment {
    variables = {
      TABLE_NAME = "videoconduit_database",
      PARTITION_KEY = "email",
      SORT_KEY = "name",
      MEDIACONVERT_ROLE = "arn:aws:iam::446636301131:role/ToBePassedFromLambda",
      REGION = "ap-south-1",
      STORAGE_CLASS = "ONEZONE_IA",
      OUTPUT_GROUP_NAME = "Converted Video",
    }
  }

  tags = {
    Purpose = "submit jobs to convert media"
    Project = "videoconduit"
  }
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Purpose = "lambda ${var.trigger_media_convert_job_name} role"
    Project = "videoconduit"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ------------------------ IAM Role lambda insert in dynamo db ---------------- #
data "aws_iam_policy_document" "lambda_dynamodb_insert" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:GetItem",
      "dynamodb:Query"
    ]
    resources = [
      "arn:aws:dynamodb:${var.region}:*:table/${var.table_name}"
    ]
    effect = "Allow"
  }
}

resource "aws_iam_policy" "lambda_dynamodb_insert" {
  name        = "lambda_dynamodb_insert_policy"
  description = "Allow Lambda to put items only in the specified DynamoDB table"
  policy      = data.aws_iam_policy_document.lambda_dynamodb_insert.json

  tags = {
    Purpose = "Lambda DynamoDB PutItem/UpdateItem/GetItem/Query"
    Project = "videoconduit"
  }
}

resource "aws_iam_policy_attachment" "lambda_dynamodb_insert" {
  name       = "lambda_dynamodb_insert_attachment"
  roles      = [aws_iam_role.lambda_exec_role.name, aws_iam_role.geturl_lambda_role.name]
  policy_arn = aws_iam_policy.lambda_dynamodb_insert.arn
}