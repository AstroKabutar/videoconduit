variable "region" {
  type = string
}

variable "trigger_media_convert_job_name" {
  type = string
}

variable "table_name" {
  type = string
}

variable "mediaconvertrole" {
  type = string
}

variable "bucket_arn" {
  type = string
}

variable "geturllambda" {
  type = string
}

variable "ses_sender_email" {
  type        = string
  description = "Verified SES identity to send download link emails from"
}
