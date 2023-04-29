#!/usr/bin/env bash

#Default variable
name_file="rpiscadapecom.tar.*"

update () {
    echo "Transfer file to IP: $3"

    echo "Start transfer file"

    sshpass -p "$2" scp -r ./config/driver/ "$1"@"$3":~/config/
    echo "Completed transfer config file"
    sshpass -p "$2" scp ./script/update_image/update_image.sh  "$1"@"$3":~/pecom/
    echo "Completed transfer update_image.sh file"
    sshpass -p "$2" scp ./docker/docker-compose.yml "$1"@"$3":~/pecom/
    echo "Completed transfer docker-compose.yml file"
    sshpass -p "$2" scp ./output/rpiscadapecom.tar.* "$1"@"$3":~/pecom/
    echo "Completed transfer rpiscadapecom.tar file"

    echo "Transfer file completed"
    echo "Start updating"

    sshpass -p "$2" ssh "$1"@"$3" << DEPLOY
        cd ~/pecom
        ./update_image.sh
DEPLOY

    echo "Done"

}

echo "Input type update"
echo "1: Single target"
echo "2: All target"

read type_update

echo "Input password admin user:"
read admin_pwds
echo "Input username device:"
read user
echo "Input password device:"
read pwds
if [[ "$type_update" == "1" ]]; then
    echo "Input device IP:"
    read ip
fi

echo "Delete old file and create pack new file"
echo ${admin_pwds} | sudo -S rm ${name_file} 2>/dev/null|| echo
split -b 300M ./output/rpiscadapecom.tar "./output/rpiscadapecom.tar.part"

if [[ "$type_update" == "1" ]]; then
    update $user $pwds $ip
elif [[ "$type_update" == "2" ]]; then
    # update $user $pwds "10.54.198.176"
    # update $user $pwds "10.54.198.137"
    # update $user $pwds "10.54.198.75"
    # update $user $pwds "10.54.198.175"
    # update $user $pwds "10.54.198.227"
    # update $user $pwds "10.54.198.26"
    # update $user $pwds "10.54.198.247"
    update $user $pwds "10.54.198.148"
    # update $user $pwds "10.54.198.79"
    # update $user $pwds "10.54.198.183"
    update $user $pwds "10.54.198.8"
    # update $user $pwds "10.54.198.40"
    # update $user $pwds "10.54.198.103"
    # update $user $pwds "10.54.198.186"
fi