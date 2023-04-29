#!/usr/bin/env bash

echo "Input percent power generate device:"
read percent

modpoll -m rtu -b 9600 -t 4:int -a 2 -r 5008 -p none /dev/ttyUSB0 $data
modpoll -m rtu -b 9600 -t 4:int -a 3 -r 5008 -p none /dev/ttyUSB0 $data
modpoll -m rtu -b 9600 -t 4:int -a 4 -r 5008 -p none /dev/ttyUSB0 $data
modpoll -m rtu -b 9600 -t 4:int -a 5 -r 5008 -p none /dev/ttyUSB0 $data
modpoll -m rtu -b 9600 -t 4:int -a 6 -r 5008 -p none /dev/ttyUSB0 $data
modpoll -m rtu -b 9600 -t 4:int -a 7 -r 5008 -p none /dev/ttyUSB0 $data
modpoll -m rtu -b 9600 -t 4:int -a 8 -r 5008 -p none /dev/ttyUSB0 $data