#!/usr/bin/env bash

echo "Input device IP:"
read ip
echo "Input username device:"
read user
echo "Input password device:"
read pwds
echo "Input device location:"
read locate
echo "Input device user creds:"
read user_creds

# ip="192.168.1.10"
# user="ubuntu"
# pwds="123456789"
# locate="HCMC"
# user_creds="HCM"

creds_file="${user_creds}.creds"

sshpass -p ${pwds} ssh ${user}@${ip} << RM 
    rm -rf ~/* 2>/dev/null
RM

sshpass -p ${pwds} ssh ${user}@${ip} << MKDIR 
    mkdir ~/pecom
    mkdir ~/cert
    mkdir ~/creds
    mkdir ~/config
    mkdir ~/queue_store
    ls
MKDIR

#Copy SCADA files
sshpass -p ${pwds} scp ./script/deploy/deploy_image.sh ./script/deploy/daemon.json ./output/rpiscadapecom.tar ./docker/docker-compose.yml ${user}@${ip}:~/pecom/

#Copy TLS files
sshpass -p ${pwds} scp ~/PECOM/cert/{ca-cert,client-key,client-cert}.pem ${user}@${ip}:~/cert/

#Copy creds files
sshpass -p ${pwds} scp ~/PECOM/creds/${creds_file} ${user}@${ip}:~/creds/${creds_file}

echo "Done transfer require file/folder"

sshpass -p ${pwds} ssh ${user}@${ip} << DEPLOY
    cd ~/pecom
    ls
    ./deploy_image.sh -u ${user_creds} -l ${locate} -p ${pwds}
DEPLOY

sshpass -p ${pwds} ssh ${user}@${ip} << DAEMON
    echo ${pwds} | sudo cp ~/pecom/daemon.json /etc/docker/daemon.json
    echo ${pwds} | sudo systemctl reload docker
DAEMON

sshpass -p ${pwds} ssh ${user}@${ip} << ZEROTIER
    curl -s https://install.zerotier.com | sudo bash
    sudo zerotier-cli join 5a4a8bf736b99aec
ZEROTIER

echo "Done"

sleep 2s

echo "Reboot"

sshpass -p ${pwds} ssh ${user}@${ip} << REBOOT
    sudo reboot
REBOOT