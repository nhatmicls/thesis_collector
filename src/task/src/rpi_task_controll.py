import argparse
import asyncio
import multiprocessing
import socket
import ssl
import sys
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import FileIO
from pathlib import Path
from typing import *
from urllib import parse

import persistqueue
import psutil
import pykka
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrNoServers, ErrTimeout
from rx.core.typing import Disposable
from rx.scheduler.eventloop import AsyncIOScheduler

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/modbuslib/src")
sys.path.append(parent_dir_path + "/src/read_site_config/src")
sys.path.append(parent_dir_path + "/src/natsio/src")
sys.path.append(parent_dir_path + "/src/identify_device/src")
sys.path.append(parent_dir_path + "/src/system/src")
sys.path.append(parent_dir_path + "/src/database/src")
sys.path.append(parent_dir_path + "/src/task/src")

import serial
import serial.tools.list_ports
from rpi_compress_data import *
from rpi_IO import *
from rpi_modbus import *
from rpi_natsio_client import NatsioSink, ProcessorActor, Source
from rpi_identify_device import *
from rpi_queue import clientQueue
from rpi_read_config import ConfigFile, Inverter
from rpi_system import *
from rpi_verbose import verbose
from rpi_watchdog import Watchdog
from rpi_database import *


def thread_recieve_controll(*args: Any, **kwargs: Any) -> None:
    thread_name = "NATS reciever"
