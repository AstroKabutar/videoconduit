import boto3
import logging
import os
import urllib.parse
from boto3.dynamodb.conditions import Key
from botocore.config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VALID_FORMATS = frozenset({"mp3", "1080p", "720p", "480p"})
UPLOAD_PREFIX = "upload"
KEY_SEPARATOR = "__."


def parse_converted_key(key):
    """
    Parse converted key: converted/{safe_email}-{safe_username}__.{basename}_{format}.{ext}
    Uses KEY_SEPARATOR to avoid splitting on dots in email domains (e.g. gapple.com).
    Also supports legacy format (prefix.basename) by splitting on last '.' before format suffix.
    Returns (email, username, video_filename).
    """
    logger.info("parse_converted_key: input key=%r", key)
    if not key.startswith("converted/"):
        raise ValueError(f"Key must start with converted/, got {key!r}")
    rest = key[len("converted/"):]
    if KEY_SEPARATOR in rest:
        prefix, suffix = rest.split(KEY_SEPARATOR, 1)
    else:
        # Legacy format: prefix.basename_format.ext - split on last '.' before _format
        for fmt in VALID_FORMATS:
            marker = f"_{fmt}."
            if marker in rest:
                before_format = rest[: rest.index(marker)]
                if "." in before_format:
                    idx = before_format.rfind(".")
                    prefix, suffix = before_format[:idx], before_format[idx + 1 :] + rest[rest.index(marker) :]
                    break
                else:
                    raise ValueError(f"Invalid converted key (no prefix): {key!r}")
        else:
            raise ValueError(f"Invalid converted key (unknown format): {key!r}")
    if "-at-" not in prefix:
        raise ValueError(f"Invalid key prefix (no -at-): {prefix!r}")

    local_part, domain_username = prefix.split("-at-", 1)
    domain, username = domain_username, ""
    for i in range(len(domain_username) - 1, -1, -1):
        if domain_username[i] == "-":
            cand_domain = domain_username[:i]
            cand_username = domain_username[i + 1:]
            if "." not in cand_username:
                domain, username = cand_domain, cand_username
                break
    if not username:
        raise ValueError(f"Could not parse domain/username from {domain_username!r}")
    email = f"{local_part}@{domain}"

    parts = suffix.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid suffix (no extension): {suffix!r}")
    basename_format, ext = parts
    for fmt in VALID_FORMATS:
        if basename_format.endswith(f"_{fmt}"):
            basename = basename_format[: -len(fmt) - 1]
            video_filename = f"{basename}.{ext}"
            logger.info("parse_converted_key: parsed email=%r username=%r video_filename=%r format=%s", email, username, video_filename, fmt)
            return email, username, video_filename
    raise ValueError(f"Unknown format in suffix: {suffix!r}")


def build_object_key(email, username, filename):
    """Build S3 object key: upload/<email-username__filename> (matches generate_presigned_post)."""
    safe_email = email.replace("@", "-at-")
    safe_username = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
    key = f"{UPLOAD_PREFIX}/{safe_email}-{safe_username}{KEY_SEPARATOR}{filename}"
    logger.info("build_object_key: email=%r username=%r filename=%r -> key=%r", email, username, filename, key)
    return key


def get_sort_key(object_key):
    """
    Extract DynamoDB sort key from full S3 object key.
    Sort key is only the part after upload/
    e.g. upload/name.format -> name.format
    """
    if object_key.startswith(UPLOAD_PREFIX + "/"):
        return object_key[len(UPLOAD_PREFIX) + 1:]
    return object_key


def update_dynamodb_status_completed(email, prefix, basename):
    """
    Update DynamoDB item status to COMPLETED.
    The DynamoDB item was created with the ORIGINAL upload filename (e.g. video.mp4),
    but the converted output has a different extension (e.g. video.mp3 for mp3).
    We query by sort_key begins_with '{prefix}__.{basename}.' to find the original item.
    """
    table_name = os.environ.get("TABLE_NAME")
    partition_key = os.environ.get("PARTITION_KEY", "email")
    sort_key_attr = os.environ.get("SORT_KEY", "name")
    sort_key_prefix = f"{prefix}{KEY_SEPARATOR}{basename}."
    logger.info("update_dynamodb_status_completed: table=%r query pk=%r sk_begins=%r", table_name, email, sort_key_prefix)
    if not table_name:
        logger.warning("TABLE_NAME not configured, skipping DynamoDB update")
        return
    try:
        dynamodb = boto3.resource(
            "dynamodb",
            region_name=os.environ.get("REGION", os.environ.get("AWS_REGION", "ap-south-1")),
        )
        table = dynamodb.Table(table_name)
        resp = table.query(
            KeyConditionExpression=Key(partition_key).eq(email) & Key(sort_key_attr).begins_with(sort_key_prefix),
            Limit=1,
        )
        items = resp.get("Items", [])
        if not items:
            logger.warning("No DynamoDB item found for email=%r sort_key_prefix=%r", email, sort_key_prefix)
            return
        dynamo_sort_key = items[0][sort_key_attr]
        table.update_item(
            Key={partition_key: email, sort_key_attr: dynamo_sort_key},
            UpdateExpression="SET #s = :status",
            ConditionExpression="attribute_exists(#pk) AND attribute_exists(#sk)",
            ExpressionAttributeNames={"#s": "status", "#pk": partition_key, "#sk": sort_key_attr},
            ExpressionAttributeValues={":status": "COMPLETED"},
        )
        logger.info("Updated DynamoDB status to COMPLETED for email=%r sort_key=%r", email, dynamo_sort_key)
    except Exception as e:
        logger.exception("DynamoDB status update failed: %s", e)


def _build_content_disposition(filename):
    """
    Build Content-Disposition value for S3 presigned URLs.
    S3 requires ISO-8859-1 for the basic filename parameter.
    For non-ASCII filenames, use RFC 5987 (filename*=UTF-8''...) encoding.
    """
    # ASCII fallback: replace non-ASCII with underscore for basic filename param
    ascii_fallback = "".join(c if ord(c) < 128 else "_" for c in filename)
    if not ascii_fallback.strip():
        ascii_fallback = "download"
    if all(ord(c) < 128 for c in filename):
        return f'attachment; filename="{filename}"'
    # RFC 5987: filename*=UTF-8''percent-encoded
    encoded = urllib.parse.quote(filename, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'


def generate_presigned_get_url(bucket_name, object_key, response_filename=None, expiration=21600):
    try:
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )
        s3 = boto3.client(
            "s3",
            region_name="ap-south-1",
            config=config,
            endpoint_url="https://s3.ap-south-1.amazonaws.com",
        )

        params = {
            "Bucket": bucket_name,
            "Key": object_key,
        }
        if response_filename:
            params["ResponseContentDisposition"] = _build_content_disposition(response_filename)

        logger.info("generate_presigned_get_url: params=%s expiration=%s", params, expiration)

        response = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=expiration,
        )
        logger.info("generate_presigned_get_url: success url_len=%d", len(response) if response else 0)
        return response
    except Exception as e:
        logger.exception("Error generating presigned URL: %s", e)
        return None


def finisher(event, context):
    bucket_name = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]

    logger.info("finisher: bucket=%r key=%r", bucket_name, key)

    email, username, video_filename = parse_converted_key(key)
    url = generate_presigned_get_url(bucket_name, key, response_filename=video_filename)

    safe_email = email.replace("@", "-at-")
    safe_username = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
    prefix = f"{safe_email}-{safe_username}"
    basename = video_filename.rsplit(".", 1)[0] if "." in video_filename else video_filename
    logger.info("finisher: updating DynamoDB for email=%r prefix=%r basename=%r", email, prefix, basename)
    update_dynamodb_status_completed(email, prefix, basename)

    body = f"""hey {username},
Your file is ready to be downloaded.
Below is the url. Paste it in the browser and download it. This url will be valid for 6 hours.
{url}"""

    logger.info("finisher: body ready for email to %r", email)

    region = os.environ.get("REGION", os.environ.get("AWS_REGION", "ap-south-1"))
    sender = os.environ.get("SES_SENDER_EMAIL")
    if sender and url:
        try:
            ses = boto3.client("sesv2", region_name=region)
            ses.send_email(
                FromEmailAddress=sender,
                Destination={"ToAddresses": [email]},
                Content={
                    "Simple": {
                        "Subject": {"Data": "Your file is ready - Video Conduit"},
                        "Body": {"Text": {"Data": body}},
                    }
                },
            )
            logger.info("finisher: email sent to %r from %r", email, sender)
        except Exception as e:
            logger.exception("finisher: failed to send email: %s", e)

    try:
        ses = boto3.client("sesv2", region_name=region)
        ses.delete_email_identity(EmailIdentity=email)
        logger.info("finisher: deleted SES identity for %r", email)
    except Exception as e:
        logger.exception("finisher: failed to delete SES identity (non-fatal): %s", e)

    return {
        "statusCode": 200,
    }


#bucket_name = "446636301131-videoconduit-storage"
#key = "converted/Run Free.mp3"
#url = generate_presigned_get_url(bucket_name, key)
#print(url)
