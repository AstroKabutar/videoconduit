import boto3
import os

UPLOAD_PREFIX = "upload"
KEY_SEPARATOR = "__."


def _log(msg, **kwargs):
    """Print log line for CloudWatch; kwargs are appended as key=value."""
    parts = [f"[submitjob] {msg}"]
    for k, v in kwargs.items():
        parts.append(f"{k}={v!r}")
    print(" ".join(parts))


def parse_s3_key(key):
    """
    Reverse build_object_key from generate_presigned_post.py.
    Key format: upload/{safe_email}-{safe_username}__.filename
    Returns (email, username, filename).
    """
    if not key.startswith(UPLOAD_PREFIX + "/"):
        _log("parse_s3_key invalid prefix", key=key)
        raise ValueError(f"Key must start with {UPLOAD_PREFIX}/, got {key!r}")
    rest = key[len(UPLOAD_PREFIX) + 1 :]
    if KEY_SEPARATOR not in rest:
        _log("parse_s3_key missing separator", key=key)
        raise ValueError(f"Key missing separator {KEY_SEPARATOR!r}")
    prefix, filename = rest.split(KEY_SEPARATOR, 1)
    if "-at-" not in prefix:
        _log("parse_s3_key no -at- in prefix", prefix=prefix)
        raise ValueError(f"Invalid key prefix (no -at-): {prefix!r}")
    local_part, domain_username = prefix.split("-at-", 1)
    # domain_username = "example.com-johndoe" or "example.com-john-doe"
    # Find last "-" such that part after has no "." (username)
    domain, username = domain_username, ""
    for i in range(len(domain_username) - 1, -1, -1):
        if domain_username[i] == "-":
            cand_domain = domain_username[:i]
            cand_username = domain_username[i + 1 :]
            if "." not in cand_username:
                domain, username = cand_domain, cand_username
                break
    if not username:
        _log("parse_s3_key could not parse domain/username", domain_username=domain_username)
        raise ValueError(f"Could not parse domain/username from {domain_username!r}")
    email = f"{local_part}@{domain}"
    return email, username, filename


REGION = os.environ.get("REGION")
STORAGE_CLASS = os.environ.get("STORAGE_CLASS")
OUTPUT_GROUP_NAME = os.environ.get("OUTPUT_GROUP_NAME")


# Output templates aligned with AWS MediaConvert Basic tier pricing:
# - MP3 audio only: 0.4x normalized minutes
# - AVC SD (480p): 1x, HD (720p/1080p): 2x at <=30fps, single-pass speed optimized
# See https://aws.amazon.com/mediaconvert/pricing/
OUTPUT_TEMPLATES = {
    "mp3": {
        "NameModifier": "_mp3",
        "ContainerSettings": {"Container": "RAW"},
        "AudioDescriptions": [
            {
                "AudioSourceName": "Audio Selector 1",
                "CodecSettings": {
                    "Codec": "MP3",
                    "Mp3Settings": {
                        "Bitrate": 128000,
                        "Channels": 2,
                        "RateControlMode": "CBR",
                        "SampleRate": 48000,
                    },
                },
            }
        ],
    },
    "1080p": {
        "NameModifier": "_1080p",
        "VideoDescription": {
            "Width": 1920,
            "Height": 1080,
            "ScalingBehavior": "DEFAULT",
            "AntiAlias": "ENABLED",
            "Sharpness": 50,
            "CodecSettings": {
                "Codec": "H_264",
                "H264Settings": {
                    "CodecProfile": "HIGH",
                    "CodecLevel": "LEVEL_4_1",
                    "RateControlMode": "QVBR",
                    "MaxBitrate": 8500000,
                    "QvbrSettings": {
                        "QvbrQualityLevel": 8,
                        "QvbrQualityLevelFineTune": 0,
                    },
                },
            },
        },
        "ContainerSettings": {"Container": "MP4"},
        "AudioDescriptions": [
            {
                "AudioSourceName": "Audio Selector 1",
                "CodecSettings": {
                    "Codec": "AAC",
                    "AacSettings": {
                        "Bitrate": 128000,
                        "CodingMode": "CODING_MODE_2_0",
                        "RateControlMode": "CBR",
                        "SampleRate": 48000,
                    },
                },
            }
        ],
    },
    "720p": {
        "NameModifier": "_720p",
        "VideoDescription": {
            "Width": 1280,
            "Height": 720,
            "ScalingBehavior": "DEFAULT",
            "AntiAlias": "ENABLED",
            "Sharpness": 50,
            "CodecSettings": {
                "Codec": "H_264",
                "H264Settings": {
                    "CodecProfile": "HIGH",
                    "CodecLevel": "LEVEL_4_1",
                    "RateControlMode": "QVBR",
                    "MaxBitrate": 6000000,
                    "QvbrSettings": {
                        "QvbrQualityLevel": 8,
                        "QvbrQualityLevelFineTune": 0,
                    },
                },
            },
        },
        "ContainerSettings": {"Container": "MP4"},
        "AudioDescriptions": [
            {
                "AudioSourceName": "Audio Selector 1",
                "CodecSettings": {
                    "Codec": "AAC",
                    "AacSettings": {
                        "Bitrate": 128000,
                        "CodingMode": "CODING_MODE_2_0",
                        "RateControlMode": "CBR",
                        "SampleRate": 48000,
                    },
                },
            }
        ],
    },
    "480p": {
        "NameModifier": "_480p",
        "VideoDescription": {
            "Width": 854,
            "Height": 480,
            "ScalingBehavior": "DEFAULT",
            "AntiAlias": "ENABLED",
            "Sharpness": 50,
            "CodecSettings": {
                "Codec": "H_264",
                "H264Settings": {
                    "CodecProfile": "HIGH",
                    "CodecLevel": "LEVEL_4_1",
                    "RateControlMode": "CBR",
                    "Bitrate": 2000000,
                },
            },
        },
        "ContainerSettings": {"Container": "MP4"},
        "AudioDescriptions": [
            {
                "AudioSourceName": "Audio Selector 1",
                "CodecSettings": {
                    "Codec": "AAC",
                    "AacSettings": {
                        "Bitrate": 128000,
                        "CodingMode": "CODING_MODE_2_0",
                        "RateControlMode": "CBR",
                        "SampleRate": 48000,
                    },
                },
            }
        ],
    },
}

VALID_FORMATS = frozenset(OUTPUT_TEMPLATES)

_dynamodb = None


def get_dynamodb_table():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource(
            "dynamodb",
            region_name=os.environ.get("REGION", os.environ.get("AWS_REGION", "ap-south-1")),
        )
    table_name = os.environ.get("TABLE_NAME")
    return _dynamodb.Table(table_name)


def get_sort_key(object_key):
    """
    Extract DynamoDB sort key from full S3 object key.
    Sort key is only the part after upload/
    e.g. upload/name.format -> name.format
    """
    if object_key.startswith(UPLOAD_PREFIX + "/"):
        return object_key[len(UPLOAD_PREFIX) + 1:]
    return object_key


def get_format_from_dynamodb(email, object_key):
    """Look up format for (email, object_key) in DynamoDB. Sort key stores only the part after upload/."""
    table = get_dynamodb_table()
    pk = os.environ.get("PARTITION_KEY", "email")
    sk = os.environ.get("SORT_KEY", "name")
    dynamo_sort_key = get_sort_key(object_key)
    resp = table.get_item(Key={pk: email, sk: dynamo_sort_key})
    item = resp.get("Item")
    if not item:
        _log("DynamoDB miss", email=email, object_key=object_key, sort_key=dynamo_sort_key)
        raise ValueError(f"No DynamoDB item for email={email!r}, key={object_key!r}")
    fmt = item.get("format")
    if not fmt:
        _log("DynamoDB item missing format", item=item)
        raise ValueError(f"DynamoDB item has no format: {item}")
    return fmt


def build_destination_base(bucket_name, safe_prefix, filename):
    """
    Build destination prefix for converted output.
    Uses KEY_SEPARATOR (__.) to avoid ambiguity with dots in email domains (e.g. gapple.com).
    Output: converted/{safe_prefix}__.{basename} (template adds _format.ext)
    e.g. converted/user-at-example.com-johndoe__.Example -> ...Example_720p.mp4
    """
    basename = filename.rsplit(".", 1)[0] if "." in filename else filename
    return f"s3://{bucket_name}/converted/{safe_prefix}{KEY_SEPARATOR}{basename}"


def get_output_template(output_format):
    """Return the single output template for the given format (mp3, 1080p, 720p, 480p)."""
    if output_format not in VALID_FORMATS:
        raise ValueError(f"output_format must be one of {sorted(VALID_FORMATS)}, got {output_format!r}")
    return OUTPUT_TEMPLATES[output_format].copy()


def submitjob(event, context):
    bucket_name = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]
    _log("invoked", bucket=bucket_name, key=key)

    email, username, filename = parse_s3_key(key)
    _log("parsed key", email=email, username=username, filename=filename)

    safe_email = email.replace("@", "-at-")
    safe_username = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
    safe_prefix = f"{safe_email}-{safe_username}"

    output_format = get_format_from_dynamodb(email, key)
    if isinstance(output_format, str):
        output_format = output_format.lower()
    if output_format not in VALID_FORMATS:
        _log("invalid format", output_format=output_format, valid=tuple(sorted(VALID_FORMATS)))
        raise ValueError(f"DynamoDB format {output_format!r} not in {sorted(VALID_FORMATS)}")
    _log("format from DynamoDB", output_format=output_format)

    destination_base = build_destination_base(bucket_name, safe_prefix, filename)
    input_s3_url = f"s3://{bucket_name}/{key}"
    _log("paths", input=input_s3_url, destination=destination_base)

    mediaconvert = boto3.client("mediaconvert", region_name=REGION)
    endpoint = mediaconvert.describe_endpoints()["Endpoints"][0]["Url"]
    mediaconvert = boto3.client("mediaconvert", endpoint_url=endpoint, region_name=REGION)

    template = get_output_template(output_format)
    job_settings = {
        "Role": os.environ.get("MEDIACONVERT_ROLE"),
        "Settings": {
            "Inputs": [
                {
                    "FileInput": input_s3_url,
                    "AudioSelectors": {"Audio Selector 1": {"DefaultSelection": "DEFAULT"}},
                }
            ],
            "OutputGroups": [
                {
                    "Name": OUTPUT_GROUP_NAME,
                    "OutputGroupSettings": {
                        "Type": "FILE_GROUP_SETTINGS",
                        "FileGroupSettings": {
                            "Destination": destination_base,
                            "DestinationSettings": {"S3Settings": {"StorageClass": STORAGE_CLASS}},
                        },
                    },
                    "Outputs": [template],
                }
            ],
        },
    }

    response = mediaconvert.create_job(**job_settings)
    job_id = response["Job"]["Id"]
    _log("MediaConvert job created", job_id=job_id)
    return 200
