#!/usr/bin/env bash

#Default variable

update () {
    echo "Transfer file to IP: $3"

    echo "Start transfer file"

    sshpass -p "$2" scp -r ./config/driver/ "$1"@"$3":~/config/
    echo "Completed transfer config file"

    echo "Transfer file completed"
    echo "Start updating"

    sshpass -p "$2" ssh "$1"@"$3" << DEPLOY
        docker restart rpiprod
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

if [[ "$type_update" == "1" ]]; then
    update $user $pwds $ip
elif [[ "$type_update" == "2" ]]; then
    update $user $pwds "10.54.198.176"
    update $user $pwds "10.54.198.137"
    update $user $pwds "10.54.198.75"
    update $user $pwds "10.54.198.175"
    update $user $pwds "10.54.198.227"
    update $user $pwds "10.54.198.26"
    update $user $pwds "10.54.198.247"
    update $user $pwds "10.54.198.148"
    update $user $pwds "10.54.198.79"
    update $user $pwds "10.54.198.183"
    update $user $pwds "10.54.198.8"
    update $user $pwds "10.54.198.40"
    update $user $pwds "10.54.198.103"
    update $user $pwds "10.54.198.186"
fi