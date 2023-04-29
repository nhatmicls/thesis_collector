FROM --platform=linux/amd64 ubuntu:20.04
WORKDIR /pecom

# Install python3.9
RUN apt update && \
    apt -y install software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    apt -y install python3.9 && \
    apt -y install libcairo2-dev

# Set default python3.9
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# Install ssh, git, pip, venv, sshpass, nano
RUN apt update && \
    apt-get -y install git openssh-client python3-pip python3.9-dev python3.9-venv sshpass openssh-server nano tmux &&\
    pip install -U black

# Install ping
RUN apt-get update && apt-get install -y iputils-ping && apt-get install -y nmap && apt-get install -y iproute2

# Create virtual environments
ADD ./requirements.txt /pecom/rpi-playground/
RUN pip install --upgrade pip
RUN pip install -r /pecom/rpi-playground/requirements.txt

WORKDIR /pecom/rpi-playground