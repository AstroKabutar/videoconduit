#! /bin/bash

if [ "$1" == "plan" ]; then
    /home/shadow/terraform/terraform $1 -var-file=vars
    exit 1
fi

/home/shadow/terraform/terraform $1 -auto-approve -var-file=vars
if [ "$1" == "apply" ]; then
    source vars && export bucket_name
    aws s3 cp index.html s3://$bucket_name/index.html
    aws s3 cp error.html s3://$bucket_name/error.html
    aws cloudfront create-invalidation --distribution-id E2HPVM2VSILBFL --paths "/*"
fi