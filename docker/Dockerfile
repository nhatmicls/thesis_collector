FROM python:3.9.16-alpine3.16 as main

WORKDIR /pecom

#Install python 3
RUN apk add --update --no-cache py3-pip

RUN apk add py3-virtualenv 
RUN apk add python3-dev build-base py3-numpy linux-headers py3-dbus

#Install requirement for snappy C
RUN apk add snappy-dev

#Install other platform requirement
RUN apk add libffi-dev

# Install utility
RUN apk update && \
    apk add git openssh-client sshpass openssh-server nano tmux pkgconfig &&\
    pip install -U setuptools wheel

RUN apk update && apk add iputils nmap iproute2

FROM main as dev

# Install utility
RUN apk update && \
    pip install -U black

ADD ./docker/requirements.txt /pecom/rpi-playground/

# Download and install pip package
RUN pip install --upgrade pip
RUN pip install -r /pecom/rpi-playground/requirements.txt

#Copy file
ADD ./ /pecom/rpi-playground/

WORKDIR /pecom/rpi-playground

FROM main as prod
ADD ./docker/requirements.txt /pecom/rpi-playground/

# Download and install pip package
RUN pip install --upgrade pip
RUN pip install -r /pecom/rpi-playground/requirements.txt

#Copy file
ADD ./ /pecom/rpi-playground/

WORKDIR /pecom/rpi-playground
ENTRYPOINT python -u run.py