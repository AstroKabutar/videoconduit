#! /bin/bash

if [ "$1" == "launch" ]; then
    echo "Launching/Destroying dynamodb"
    cd dynamo-db
    bash launch.sh $2

    echo "# --------------------------------- #"

    echo "Launching/Destroying s3-storage bucket"
    cd ../s3-storage
    bash launch.sh $2

    echo "# --------------------------------- #"

    echo "Launching/Destroying lambda functions"
    cd ../lambda
    bash launch.sh $2

    echo "# --------------------------------- #"
    
    echo "Launching/Destroying eventbridge"
    cd ../event-bridge
    bash launch.sh $2

    echo "# --------------------------------- #"

    echo "Launching/Destroying frontend website"
    cd ../s3-frontend
    bash launch.sh $2

    echo "# --------------------------------- #"
    
    echo "Launching/Destroying lambda and api gateway for generating presigned post url"
    cd ../lambda-post
    bash launch.sh $2

    echo "${2} successfully completed"
fi

# aws s3api put-object --bucket my-bucket --key photos/