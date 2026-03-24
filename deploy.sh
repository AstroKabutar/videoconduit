#! /bin/bash

# with full path example 'css/index.css'
files-to-be-deployed=(
    "index.html"
)

for file in ${files-to-be-deployed[@]}; do
    echo "Deploying $file"
    aws s3 cp $file $bucket_name/$file
done