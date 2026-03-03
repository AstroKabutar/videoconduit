#! /bin/bash

if [ "$1" == "plan" ]; then
    /home/shadow/terraform/terraform $1 -var-file=vars
    exit 1
fi

/home/shadow/terraform/terraform $1 -auto-approve -var-file=vars