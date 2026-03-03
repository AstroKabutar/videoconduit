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

# -------------- Event Bridge ---------------- #

resource "aws_cloudwatch_event_rule" "s3_object_created_converted" {
  name        = "s3-object-created-storage-converted"
  description = "EventBridge rule for S3 object created in videoconduit storage bucket (converted prefix)"

  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = {
        name = [var.bucket_name]
      }
      object = {
        key = [
          {
            prefix = "converted"
          }
        ]
      }
    }
  })

  tags = {
    Purpose = "get notifications based on object created"
    Project = "videoconduit"
  }
}

resource "aws_cloudwatch_event_rule" "s3_object_created" {
  name        = "s3-object-created-storage"
  description = "EventBridge rule for S3 object created in videoconduit storage bucket"

  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = {
        name = [var.bucket_name]
      }
      object = {
        key = [
          {
            prefix = "upload"
          }
        ]
      }
    }
  })

  tags = {
    Purpose = "get notifications based on object created"
    Project = "videoconduit"
  }
}

resource "aws_cloudwatch_event_target" "s3_object_created_to_logs_upload" {
  rule = aws_cloudwatch_event_rule.s3_object_created.name
  arn  = aws_cloudwatch_log_group.s3_event_upload.arn

  depends_on = [ aws_cloudwatch_event_rule.s3_object_created, aws_cloudwatch_log_group.s3_event_upload ]
}

resource "aws_cloudwatch_event_target" "s3_event_trigger_converted_to_logs" {
  rule = aws_cloudwatch_event_rule.s3_object_created_converted.name
  arn  = aws_cloudwatch_log_group.s3_event_converted.arn

  depends_on = [
    aws_cloudwatch_event_rule.s3_object_created_converted,
    aws_cloudwatch_log_group.s3_event_converted,
    aws_cloudwatch_log_resource_policy.eventbridge_to_cw_logs_converted
  ]
}

# --------------- Lambda trigger generate presigned url ------------- #

resource "aws_cloudwatch_event_target" "s3_event_trigger_converted_to_lambda" {
  rule     = aws_cloudwatch_event_rule.s3_object_created_converted.name
  arn      = var.get_presigned_url_lambda_arn
  role_arn = aws_iam_role.eventbridge_geturl_lambda_trigger.arn

  depends_on = [
    aws_cloudwatch_event_rule.s3_object_created_converted,
    aws_iam_role.eventbridge_geturl_lambda_trigger,
    aws_iam_role_policy.eventbridge_geturl_lambda_invoke_policy
  ]
}

# --------------- Lambda trigger convertion job and DB update ------------- #
# Grant EventBridge permission to assume role and allow Lambda invoke

data "aws_iam_policy_document" "lambda_eventbridge_assume_role" {
  statement {
    sid     = "TrustEventBridgeService"
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = ["446636301131"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = ["arn:aws:events:ap-south-1:446636301131:rule/s3-object-created-storage"]
    }
  }
}

data "aws_iam_policy_document" "lambda_eventbridge_invoke_policy" {
  statement {
    sid    = "AllowLambdaInvokeFunction"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = [
      "arn:aws:lambda:ap-south-1:446636301131:function:convert_media"
    ]
  }
}

data "aws_iam_policy_document" "geturl_lambda_eventbridge_assume_role" {
  statement {
    sid    = "TrustEventBridgeService"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.s3_object_created_converted.arn]
    }
  }
}

data "aws_iam_policy_document" "geturl_lambda_eventbridge_invoke_policy" {
  statement {
    sid    = "AllowLambdaInvokeFunction"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = [
      var.get_presigned_url_lambda_arn
    ]
  }
}

resource "aws_iam_role" "eventbridge_geturl_lambda_trigger" {
  name               = "eventbridge-geturl-lambda-trigger-role"
  assume_role_policy = data.aws_iam_policy_document.geturl_lambda_eventbridge_assume_role.json
}

resource "aws_iam_role_policy" "eventbridge_geturl_lambda_invoke_policy" {
  name   = "eventbridge_geturl_lambda_invoke_policy"
  role   = aws_iam_role.eventbridge_geturl_lambda_trigger.id
  policy = data.aws_iam_policy_document.geturl_lambda_eventbridge_invoke_policy.json
}

resource "aws_iam_role" "eventbridge_lambda_trigger" {
  name               = "eventbridge-lambda-trigger-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_eventbridge_assume_role.json
}

resource "aws_iam_role_policy" "eventbridge_lambda_invoke_policy" {
  name   = "eventbridge_lambda_invoke_policy"
  role   = aws_iam_role.eventbridge_lambda_trigger.id
  policy = data.aws_iam_policy_document.lambda_eventbridge_invoke_policy.json
}

resource "aws_cloudwatch_event_target" "s3_object_created_to_lambda" {
  rule      = aws_cloudwatch_event_rule.s3_object_created.name
  arn       = var.submit_job_lambda_arn

  role_arn  = aws_iam_role.eventbridge_lambda_trigger.arn

  depends_on = [
    aws_cloudwatch_event_rule.s3_object_created,
    aws_iam_role.eventbridge_lambda_trigger,
    aws_iam_role_policy.eventbridge_lambda_invoke_policy
  ]
}

# --------------- Cloudwatch ----------------- #

resource "aws_cloudwatch_log_group" "s3_event_upload" {
  name = "/aws/events/s3-event-upload"

  tags = {
    Purpose = "keep logs for object creation in s3"
    Project = "videoconduit"
  }
}

resource "aws_cloudwatch_log_group" "s3_event_converted" {
  name = "/aws/events/s3-event-converted"

  tags = {
    Purpose = "keep logs for object creation in s3"
    Project = "videoconduit"
  }
}


data "aws_iam_policy_document" "eventbridge_to_cw_logs" {
  statement {
    sid    = "EventBridgeToCloudWatchLogs"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.s3_event_upload.arn}:*"]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.s3_object_created.arn]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "eventbridge_to_cw_logs" {
  policy_name     = "eventbridge-to-cw-logs-s3-object-created-storage"
  policy_document = data.aws_iam_policy_document.eventbridge_to_cw_logs.json
}

data "aws_iam_policy_document" "eventbridge_to_cw_logs_converted" {
  statement {
    sid    = "EventBridgeToCloudWatchLogs"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.s3_event_converted.arn}:*"]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.s3_object_created_converted.arn]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "eventbridge_to_cw_logs_converted" {
  policy_name     = "eventbridge-to-cw-logs-s3-object-created-storage-converted"
  policy_document = data.aws_iam_policy_document.eventbridge_to_cw_logs_converted.json
}
