import os
import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
}


def response(status_code, body, headers=None):
    h = {**CORS_HEADERS, **(headers or {})}
    h.setdefault("Content-Type", "application/json")
    return {"statusCode": status_code, "headers": h, "body": json.dumps(body) if isinstance(body, dict) else body}


def handler(event, context):
    """API Gateway handler - expects GET/POST with query or body param: emailaddress."""
    logger.info("create_ses_identity invoked", extra={"httpMethod": event.get("httpMethod"), "requestId": context.aws_request_id})

    if event.get("httpMethod") == "OPTIONS":
        return response(204, "")

    if event.get("httpMethod") not in ("GET", "POST"):
        logger.warning("Method not allowed", extra={"httpMethod": event.get("httpMethod")})
        return response(405, {"error": "Method not allowed"})

    # Support emailaddress from query string or JSON body
    params = event.get("queryStringParameters") or {}
    emailaddress = params.get("emailaddress")

    if not emailaddress and event.get("body"):
        try:
            body = json.loads(event["body"])
            emailaddress = body.get("emailaddress")
        except (json.JSONDecodeError, TypeError):
            pass

    if not emailaddress:
        logger.warning("Missing required parameter: emailaddress")
        return response(400, {"error": "Missing required parameter: emailaddress"})

    emailaddress = emailaddress.strip()
    if "@" not in emailaddress:
        logger.warning("Invalid email address", extra={"emailaddress": emailaddress})
        return response(400, {"error": "Invalid email address"})

    region = os.environ.get("REGION", os.environ.get("AWS_REGION", "ap-south-1"))
    try:
        ses = boto3.client("sesv2", region_name=region)
        ses.create_email_identity(EmailIdentity=emailaddress)
        logger.info("SES identity created, verification email sent", extra={"emailaddress": emailaddress, "region": region})
        return response(200, {
            "message": "Verification email sent",
            "emailaddress": emailaddress,
        })
    except Exception as e:
        err_code = ""
        if hasattr(e, "response") and isinstance(getattr(e, "response"), dict):
            err_code = e.response.get("Error", {}).get("Code", "")
        if err_code in ("AlreadyExistsException", "ConflictException"):
            logger.info("SES identity already exists or verification pending", extra={"emailaddress": emailaddress})
            return response(200, {
                "message": "Identity already exists or verification pending",
                "emailaddress": emailaddress,
            })
        logger.exception("SES create_email_identity failed", extra={"emailaddress": emailaddress, "errorCode": err_code})
        return response(500, {"error": str(e)})
