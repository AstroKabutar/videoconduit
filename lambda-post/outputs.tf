output "api_url" {
  description = "API Gateway URL to get presigned POST (append ?key=upload/filename.mp4)"
  value       = "${aws_api_gateway_stage.main.invoke_url}"
}
