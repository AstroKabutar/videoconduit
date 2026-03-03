import boto3
import os

REGION = os.environ.get("REGION")
STORAGE_CLASS = os.environ.get("STORAGE_CLASS")
OUTPUT_GROUP_NAME = os.environ.get("OUTPUT_GROUP_NAME")


class JobTemplate:
    """Stores MediaConvert output templates and returns filled job settings."""

    TEMPLATES = {
        "mp3": {
            "output": {
                "NameModifier": "",
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
        },
        "4k": {
            "output": {
                "NameModifier": "_4k",
                "VideoDescription": {
                    "Width": 3840,
                    "Height": 2160,
                    "ScalingBehavior": "DEFAULT",
                    "AntiAlias": "ENABLED",
                    "Sharpness": 50,
                    "CodecSettings": {
                        "Codec": "H_264",
                        "H264Settings": {
                            "CodecProfile": "HIGH",
                            "CodecLevel": "LEVEL_4_1",
                            "RateControlMode": "QVBR",
                            "MaxBitrate": 15000000,
                            "QvbrSettings": {
                                "QvbrQualityLevel": 9,
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
        },
        "1080p": {
            "output": {
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
        },
        "720p": {
            "output": {
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
        },
        "480p": {
            "output": {
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
        },
    }

    def __init__(self, selector):
        self.selector = selector

    def get_job_settings(self, input_s3_url, destination_base, mediaconvert_role):
        """Return filled MediaConvert job settings for create_job."""
        s3_settings = {"DestinationSettings": {"S3Settings": {"StorageClass": STORAGE_CLASS}}}
        out = self.TEMPLATES[self.selector]["output"].copy()
        video_outputs = [out] if "VideoDescription" in out else []
        mp3_outputs = [] if "VideoDescription" in out else [out]

        output_groups = []
        if video_outputs:
            output_groups.append({
                "Name": f"{OUTPUT_GROUP_NAME}",
                "OutputGroupSettings": {
                    "Type": "FILE_GROUP_SETTINGS",
                    "FileGroupSettings": {
                        "Destination": destination_base,
                        **s3_settings,
                    },
                },
                "Outputs": video_outputs,
            })
        if mp3_outputs:
            output_groups.append({
                "Name": f"{OUTPUT_GROUP_NAME}",
                "OutputGroupSettings": {
                    "Type": "FILE_GROUP_SETTINGS",
                    "FileGroupSettings": {
                        "Destination": destination_base,
                        **s3_settings,
                    },
                },
                "Outputs": mp3_outputs,
            })

        return {
            "Role": mediaconvert_role,
            "Settings": {
                "Inputs": [
                    {
                        "FileInput": input_s3_url,
                        "AudioSelectors": {"Audio Selector 1": {"DefaultSelection": "DEFAULT"}},
                    }
                ],
                "OutputGroups": output_groups,
            },
        }


def submitjob(event, context):
    bucket_name = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]
    selector = "4k"
    mediaconvert_role = os.environ.get("MEDIACONVERT_ROLE")

    mediaconvert = boto3.client("mediaconvert", region_name=REGION)
    endpoint = mediaconvert.describe_endpoints()["Endpoints"][0]["Url"]
    mediaconvert = boto3.client("mediaconvert", endpoint_url=endpoint, region_name=REGION)

    input_s3_url = f"s3://{bucket_name}/{key}"
    destination_base = f"s3://{bucket_name}/converted/"

    template = JobTemplate(selector)
    job_settings = template.get_job_settings(input_s3_url, destination_base, mediaconvert_role)
    response = mediaconvert.create_job(**job_settings)
    print("MediaConvert job created:", response["Job"]["Id"])
    return response
