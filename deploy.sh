#! /bin/bash

# Files to be depployed marked as 1
create_ses_identity=0
generate_presigned_url=0
generate_presigned_post=0
submitjob=1

if [ $create_ses_identity -eq 1 ]; then
    echo "Deploying create_ses_identity"
    zip -r create_ses_identity.zip create_ses_identity.py
    aws lambda update-function-code --function-name "${{ secrets.CREATE_SES_IDENTITY_FUNCTION_NAME }}" --zip-file fileb://create_ses_identity.zip
fi

if [ $generate_presigned_url -eq 1 ]; then
    echo "Deploying generate_presigned_url"
    zip -r finisher.zip generate_presigned_url.py
    aws lambda update-function-code --function-name "${{ secrets.GENERATE_PRESIGNED_URL_FUNCTION_NAME }}" --zip-file fileb://finisher.zip
fi

if [ $generate_presigned_post -eq 1 ]; then
    echo "Deploying generate_presigned_post"
    zip -r generate_presigned_post.zip generate_presigned_post.py
    aws lambda update-function-code --function-name "${{ secrets.GENERATE_PRESIGNED_POST_FUNCTION_NAME }}"--zip-file fileb://generate_presigned_post.zip
fi

if [ $submitjob -eq 1 ]; then
    echo "Deploying submitjob"
    zip -r submitjob.zip submitjob.py
    aws lambda update-function-code --function-name "${{ secrets.SUBMITJOB_FUNCTION_NAME }}" --zip-file fileb://submitjob.zip
fi

echo "Deployment complete"