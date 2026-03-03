#! /bin/bash

if [ "$1" == "plan" ]; then
    /home/shadow/terraform/terraform $1 -var-file=vars
    exit 1
fi

/home/shadow/terraform/terraform $1 -auto-approve -var-file=vars

if [ "$1" == "apply" ]; then
    echo "Creating /upload and /converted folders in the bucket"
    source vars && export bucket_name
    aws s3api put-object --bucket $bucket_name --key upload/
    aws s3api put-object --bucket $bucket_name --key converted/
fi