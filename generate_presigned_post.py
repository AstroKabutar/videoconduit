import os
import json
import time
import boto3
from botocore.config import Config

TTL_DAYS = 20

dynamodb = None

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
}


def response(status_code, body, headers=None):
    h = {**CORS_HEADERS, **(headers or {})}
    h.setdefault("Content-Type", "application/json")
    return {"statusCode": status_code, "headers": h, "body": json.dumps(body) if isinstance(body, dict) else body}


def get_dynamodb_table():
    global dynamodb
    if dynamodb is None:
        dynamodb = boto3.resource(
            "dynamodb",
            region_name=os.environ.get("REGION", os.environ.get("AWS_REGION", "ap-south-1")),
        )
    table_name = os.environ.get("TABLE_NAME")
    partition_key = os.environ.get("PARTITION_KEY", "email")
    sort_key = os.environ.get("SORT_KEY", "name")
    return dynamodb.Table(table_name), partition_key, sort_key


# S3 key prefix - constant for all uploads
UPLOAD_PREFIX = "upload"

# Separator between email-username prefix and filename in S3 keys
KEY_SEPARATOR = "__."


def extract_filename(key_or_path):
    """Extract filename from key (e.g. 'upload/Example.mp4' -> 'Example.mp4')."""
    return key_or_path.split("/")[-1] if "/" in key_or_path else key_or_path


def build_object_key(email, username, original_key, separator=KEY_SEPARATOR):
    """
    Build S3 object key: upload/<email-username__filename>
    e.g. upload/user-at-example.com-johndoe__Example.mp4
    """
    filename = extract_filename(original_key)
    safe_email = email.replace("@", "-at-")
    safe_username = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
    return f"{UPLOAD_PREFIX}/{safe_email}-{safe_username}{separator}{filename}"


def get_sort_key(object_key):
    """
    Extract DynamoDB sort key from full S3 object key.
    Sort key is only the part after upload/
    e.g. upload/name.format -> name.format
    """
    if object_key.startswith(UPLOAD_PREFIX + "/"):
        return object_key[len(UPLOAD_PREFIX) + 1:]
    return object_key


def generate_presigned_post(bucket_name, object_key, expiration=3600): # 1 hour validity
    """Generate a presigned POST URL for uploading to S3."""
    print(f"[presigned] generate_presigned_post: bucket={bucket_name}, key={object_key}")
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
        print(f"[presigned] Error generating presigned POST: {e}")
        raise


def handler(event, context):
    """API Gateway handler - expects GET with query params: key, email, username, format, status, geturl."""
    print(f"[presigned] handler invoked, httpMethod={event.get('httpMethod')}")

    if event.get("httpMethod") == "OPTIONS":
        return response(204, "")

    if event.get("httpMethod") != "GET":
        print(f"[presigned] rejected: method {event.get('httpMethod')} not allowed")
        return response(405, {"error": "Method not allowed"})

    params = event.get("queryStringParameters") or {}
    print(f"[presigned] query params: {params}")

    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        print("[presigned] error: BUCKET_NAME not configured")
        return response(500, {"error": "BUCKET_NAME not configured"})

    object_key = params.get("key")
    email = params.get("email")
    username = params.get("username")
    format_val = params.get("format")
    status_val = params.get("status", "PROCESSING")
    geturl = params.get("geturl", "")

    if not object_key or not email or not username or not format_val:
        print(f"[presigned] validation failed: key={object_key!r}, email={email!r}, username={username!r}, format={format_val!r}")
        return response(400, {"error": "Missing required fields: key, email, username, format"})

    # Original video filename (e.g. Example.mp4) - stored in video_name column
    video_name = extract_filename(object_key)

    # Transform key to upload/<email-username__filename>
    object_key = build_object_key(email, username, object_key)

    partition_key = os.environ.get("PARTITION_KEY", "email")
    sort_key_attr = os.environ.get("SORT_KEY", "name")
    dynamo_sort_key = get_sort_key(object_key)

    expiry_time = int(time.time()) + (TTL_DAYS * 24 * 60 * 60)
    print(f"[presigned] inserting into DynamoDB: {partition_key}={email}, {sort_key_attr}={dynamo_sort_key}, expiryTime={expiry_time}")
    try:
        table, _, _ = get_dynamodb_table()
        table.put_item(
            Item={
                partition_key: email,
                sort_key_attr: dynamo_sort_key,
                "video_name": video_name,
                "username": username,
                "format": format_val,
                "status": status_val.upper() if status_val else "PROCESSING",
                "geturl": geturl if geturl is not None else "",
                "expiryTime": expiry_time,
            }
        )
    except Exception as e:
        print(f"[presigned] DynamoDB put error: {e}")
        return response(500, {"error": f"DynamoDB insert failed: {str(e)}"})

    print(f"[presigned] generating presigned POST for bucket={bucket_name}, key={object_key}")
    try:
        presigned = generate_presigned_post(bucket_name, object_key)
        print(f"[presigned] success, url={presigned['url']}")
        return response(200, {"url": presigned["url"], "fields": presigned["fields"]})
    except Exception as e:
        print(f"[presigned] presigned POST error: {e}")
        return response(500, {"error": str(e)})
