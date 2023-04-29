#!/bin/bash

echo "Starting update"

#Combine file
cat rpiscadapecom.tar.* > rpiscadapecom.tar

#Default value
formatNameContainer="rpiprod"

#Stop exist container
echo "Stop container"

docker compose -p pecom_scada down

echo "Remove old imager"

docker image rm -f rpiscadapecom 2>/dev/null|| echo

echo "Extract file"

docker load < rpiscadapecom.tar

echo "Start new container"

docker compose -p pecom_scada --profile prod up -d

echo "Stop all crontab"

sudo crontab -r

echo "Delete all unuse image"

docker image prune -f

echo "Exit"