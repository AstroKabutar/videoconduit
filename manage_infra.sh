#! /bin/bash

optional_command="/home/shadow/terraform/terraform init"
#optional_command=""

if [ "$1" == "launch" ]; then
    echo "Launching/Destroying dynamodb"
    cd dynamo-db
    eval "$optional_command"
    bash launch.sh $2

    echo "# --------------------------------- #"

    echo "Launching/Destroying s3-storage bucket"
    cd ../s3-storage
    eval "$optional_command"
    bash launch.sh $2

    echo "# --------------------------------- #"

    echo "Launching/Destroying lambda functions"
    cd ../lambda
    eval "$optional_command"
    bash launch.sh $2

    echo "# --------------------------------- #"
    
    echo "Launching/Destroying eventbridge"
    cd ../event-bridge
    eval "$optional_command"
    bash launch.sh $2

    if [ "$2" == "destroy" ]; then
        echo "# --------------------------------- #"

        echo "Launching/Destroying frontend website"
        cd ../s3-frontend
        eval "$optional_command"
        bash launch.sh $2
    fi

    echo "# --------------------------------- #"
    
    echo "Launching/Destroying lambda and api gateway for generating presigned post url"
    cd ../lambda-post
    eval "$optional_command"
    bash launch.sh $2

    echo "${2} successfully completed"
fi

# aws s3api put-object --bucket my-bucket --key photos/