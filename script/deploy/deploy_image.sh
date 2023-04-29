#!/usr/bin/env bash

usage () { echo "./deploy_image.sh -u user -l location -p password"; }

flags=':u:l:p:h'
while getopts $flags flag
do
    case "${flag}" in
        u) user=${OPTARG};;
        l) locate=${OPTARG};;
        p) pwds=${OPTARG};;
        h) usage; exit;;
    esac
done

if [ ${user} = "" ]
then
    echo "User must be included" >&2
    exit 1
fi

if [ ${locate} = "" ]
then
    echo "Location must be included" >&2
    exit 1
fi

if [ ${pwds} = "" ]
then
    echo "Password must be included" >&2
    exit 1
fi

echo "Prepare for deploy docker in raspberry"

config_path="/config/${locate}/config.json"
creds_path="/creds/${user}.creds"
export ConfigFile=${config_path}
export UserCredentials=${creds_path}
export UserPwds=${pwds}

echo ${pwds} | sudo dhclient eth0 || true

echo "Starting installing docker & docker compose"

echo ${pwds} | sudo apt-get -y update

echo ${pwds} | sudo apt-get -y install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    wpasupplicant \
    wireless-tools \
    net-tools

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo ${pwds} | sudo apt-get -y update

echo ${pwds} | sudo apt-get -y install docker-ce docker-ce-cli containerd.io

echo ${pwds} | sudo docker run --rm hello-world
 
if grep -q "docker" /etc/group
then
  echo "Group exists"
else
  echo ${pwds} | sudo groupadd docker
fi

echo ${pwds} | sudo usermod -aG docker ubuntu

sleep 1s

newgrp docker<<EONG
EONG

echo ${pwds} | sudo systemctl restart docker

sleep 1s

docker run --rm hello-world

echo ${pwds} | sudo systemctl enable docker.service
echo ${pwds} | sudo systemctl enable containerd.service

mkdir -p ~/.docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/download/v2.2.2/docker-compose-linux-aarch64 -o ~/.docker/cli-plugins/docker-compose

chmod +x ~/.docker/cli-plugins/docker-compose
docker compose version

echo "Done installing docker & docker compose"
echo "Add env"

echo "export ConfigFile=${config_path}" | sudo tee /etc/profile.d/rpi_env.sh > /dev/null
echo "export UserCredentials=${creds_path}" | sudo tee -a /etc/profile.d/rpi_env.sh > /dev/null
echo "export UserPwds=${pwds}" | sudo tee -a /etc/profile.d/rpi_env.sh > /dev/null

echo "Starting cloning image"

docker load < rpiscadapecom.tar

echo "Done cloning image"