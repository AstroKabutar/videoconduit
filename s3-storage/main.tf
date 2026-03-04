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

resource "aws_s3_bucket" "main" {
  bucket        = var.bucket_name
  force_destroy = true

    tags = {
        "Purpose" = "videoconduit storage",
        "Project" = "videoconduit"
    }
}

resource "aws_s3_bucket_cors_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["POST", "PUT"]
    allowed_origins = ["*"]
    expose_headers  = []
  }
}

resource "aws_s3_bucket_notification" "main" {
  bucket      = aws_s3_bucket.main.id
  eventbridge = true
}

# S3 lifecycle minimum expiration is 1 day (6 hours not supported).
# For 6-hour TTL, use S3 Event Notifications + Lambda instead.
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    id     = "delete-upload-after-1-day"
    status = "Enabled"

    filter {
      prefix = "upload/"
    }

    expiration {
      days = 1
    }
  }

  rule {
    id     = "delete-converted-after-1-day"
    status = "Enabled"

    filter {
      prefix = "converted/"
    }

    expiration {
      days = 1
    }
  }
}