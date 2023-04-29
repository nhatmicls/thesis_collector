#!/usr/bin/env bash

echo "Job ID"
echo "1: Build"
echo "2: Update image"
echo "3: Update config"
echo "4: Deploy"

read type_update

if [[ "$type_update" == "1" ]]; then
    /bin/bash ./script/build_image.sh
elif [[ "$type_update" == "2" ]]; then
    /bin/bash ./script/update_image/update_rpi.sh
elif [[ "$type_update" == "3" ]]; then
    /bin/bash ./script/update_config/update_config.sh
elif [[ "$type_update" == "4" ]]; then
    /bin/bash ./script/deploy/deploy_rpi.sh
fi

