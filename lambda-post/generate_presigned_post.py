import os
import json
import boto3
from botocore.config import Config


def generate_presigned_post(bucket_name, object_key, expiration=3600):
    """Generate a presigned POST URL for uploading to S3."""
    try:
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )
        s3 = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_REGION", "ap-south-1"),
            config=config,
        )

        response = s3.generate_presigned_post(
            Bucket=bucket_name,
            Key=object_key,
            ExpiresIn=expiration,
        )
        return response
    except Exception as e:
        print(f"Error generating presigned POST: {e}")
        raise


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
}


def handler(event, context):
    """API Gateway handler - expects query param 'key' for the S3 object key."""
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
            "body": "",
        }

    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        return {
            "statusCode": 500,
            "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
            "body": json.dumps({"error": "BUCKET_NAME not configured"}),
        }

    query_params = event.get("queryStringParameters") or {}
    object_key = query_params.get("key")

    if not object_key:
        return {
            "statusCode": 400,
            "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing required query parameter: key"}),
        }

    try:
        presigned = generate_presigned_post(bucket_name, object_key)
        return {
            "statusCode": 200,
            "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "url": presigned["url"],
                    "fields": presigned["fields"],
                }
            ),
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
