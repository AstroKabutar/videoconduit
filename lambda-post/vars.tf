variable "region" {
  type = string
}

variable "bucket_name" {
  type = string
}

variable "bucket_arn" {
  type = string
}

variable "lambda_name" {
  type = string
}

variable "api_gateway_name" {
  type = string
}

variable "table_name" {
  type    = string
  default = "videoconduit_database"
}

variable "partition_key" {
  type    = string
  default = "email"
}

variable "sort_key" {
  type    = string
  default = "name"
}

# ------------------- SES Lambda (email identity creation) ------------------- #

variable "lambda_ses_name" {
  type        = string
  description = "Lambda function name for SES identity creation"
}
