output "api_url" {
  description = "API Gateway URL to get presigned POST (append ?key=upload/filename.mp4)"
  value       = "${aws_api_gateway_stage.main.invoke_url}"
}

output "email_endpoint" {
  description = "API Gateway URL for SES identity creation (GET/POST ?emailaddress=user@example.com)"
  value       = "${aws_api_gateway_stage.main.invoke_url}/email"
}
