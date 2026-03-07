#! /bin/bash

if [ "$1" == "plan" ]; then
    /home/shadow/terraform/terraform $1 -var-file=vars
    exit 1
fi

#zip -r submitjob.zip submitjob.py
#zip -r finisher.zip generate_presigned_url.py
/home/shadow/terraform/terraform $1 -auto-approve -var-file=vars

#aws lambda update-function-code --function-name convert_media --zip-file fileb://submitjob.zip