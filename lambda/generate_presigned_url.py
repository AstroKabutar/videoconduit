import boto3
from botocore.config import Config

def generate_presigned_get_url(bucket_name, object_key, expiration=3600):
    try:
        # Path-style addressing so the signed Host header stays consistent when the URL is used
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

        response = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key,
            },
            ExpiresIn=expiration,
        )
        return response
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None


def finisher(event, context):
    bucket_name = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]  

    print(f"Bucket name: {bucket_name}")
    print(f"Key: {key}")

    url = generate_presigned_get_url(bucket_name, key)
    print(url)
    return {
        'statusCode': 200,
    }



#bucket_name = "446636301131-videoconduit-storage"
#key = "converted/Run Free.mp3"
#url = generate_presigned_get_url(bucket_name, key)
#print(url)