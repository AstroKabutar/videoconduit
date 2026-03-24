#! /bin/bash

# with full path example 'css/index.css'
files=("index.html")

for file in ${files[@]}; do
    echo "Deploying $file"
    aws s3 cp $file $BUCKET_NAME/$file
done