import boto3
import os

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


def get_output_template(output_format):
    """Return the single output template for the given format (mp3, 1080p, 720p, 480p)."""
    if output_format not in VALID_FORMATS:
        raise ValueError(f"output_format must be one of {sorted(VALID_FORMATS)}, got {output_format!r}")
    return OUTPUT_TEMPLATES[output_format].copy()


def submitjob(event, context):
    bucket_name = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]
    mediaconvert_role = os.environ.get("MEDIACONVERT_ROLE")

    # Accept output format from event: mp3, 1080p, 720p, or 480p
    output_format = "mp3"

    mediaconvert = boto3.client("mediaconvert", region_name=REGION)
    endpoint = mediaconvert.describe_endpoints()["Endpoints"][0]["Url"]
    mediaconvert = boto3.client("mediaconvert", endpoint_url=endpoint, region_name=REGION)

    input_s3_url = f"s3://{bucket_name}/{key}"
    destination_base = f"s3://{bucket_name}/converted/"
    template = get_output_template(output_format)

    job_settings = {
        "Role": mediaconvert_role,
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
    print("MediaConvert job created:", response["Job"]["Id"])
    return 200
