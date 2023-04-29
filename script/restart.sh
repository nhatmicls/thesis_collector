#!/usr/bin/env bash

#Default variable
name_file="rpiscadapecom.tar.*"

restart () {
    echo "Start restart docker at IP: $3"

    sshpass -p "$2" ssh "$1"@"$3" << DEPLOY
        sudo rm \$ConfigFolderPath/system_mapping_preset.json 2>/dev/null|| echo
        docker restart rpiprod
DEPLOY

    echo "Done"

}

echo "Input type update"
echo "1: Single target"
echo "2: All target"

read type_restart

echo "Input username device:"
read user
echo "Input password device:"
read pwds
if [[ "$type_restart" == "1" ]]; then
    echo "Input device IP:"
    read ip
fi

if [[ "$type_restart" == "1" ]]; then
    restart $user $pwds $ip
elif [[ "$type_restart" == "2" ]]; then
    restart $user $pwds "10.54.198.176"
    restart $user $pwds "10.54.198.137"
    restart $user $pwds "10.54.198.75"
    restart $user $pwds "10.54.198.175"
    restart $user $pwds "10.54.198.227"
    restart $user $pwds "10.54.198.26"
    restart $user $pwds "10.54.198.247"
    restart $user $pwds "10.54.198.148"
    restart $user $pwds "10.54.198.79"
    restart $user $pwds "10.54.198.183"
    restart $user $pwds "10.54.198.8"
    restart $user $pwds "10.54.198.40"
    restart $user $pwds "10.54.198.103"
    restart $user $pwds "10.54.198.186"
fi