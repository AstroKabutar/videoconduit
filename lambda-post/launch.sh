#! /bin/bash

if [ "$1" == "plan" ]; then
    /home/shadow/terraform/terraform $1 -var-file=vars
    exit 1
fi

#zip -r generate_presigned_post.zip generate_presigned_post.py
#zip -r create_ses_identity.zip create_ses_identity.py
/home/shadow/terraform/terraform $1 -auto-approve -var-file=vars
#aws lambda update-function-code --function-name generatepresignedurlpost --zip-file fileb://generate_presigned_post.zip