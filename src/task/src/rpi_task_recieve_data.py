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
sys.path.append(parent_dir_path + "/src/connection/src")
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
from rpi_natsio_connect import init_natsio

event_loop_get_natsio_event = asyncio.new_event_loop()
recv_trigger = 0


async def recieve_nats_data_init(
    default_config_file_direct: str = "",
    direct_config_file: str = "",
    site_config_folder_direct: str = "",
    user_credentials_path: str = "",
    cert_file_path: str = "",
    key_file_path: str = "",
    rootCA_file_path: str = "",
):
    topic = "thesis.hcmut.data-download.>"

    system_config = ConfigFile(
        driver_default_config_file_direct=default_config_file_direct,
        site_config_file_direct=direct_config_file,
        site_mapping_data={"mapping_SN_IP": {}},
    )

    site_mapping_direct = site_config_folder_direct + MAPPING_FILE_NAME

    nc = await init_natsio(
        server=system_config.get_NATS_server(),
        time_out=system_config.get_time_out(),
        user_credentials_path=user_credentials_path,
        cert_file_path=cert_file_path,
        key_file_path=key_file_path,
        rootCA_file_path=rootCA_file_path,
        tls=True,
    )

    async def messeage_handle(msg):
        msg_data = msg.data
        snappy_msg = snappy.decompress(msg_data)

        recv_data: Dict[str, Any] = json.loads(snappy_msg)

        system_config = ConfigFile(
            driver_default_config_file_direct=default_config_file_direct,
            site_config_file_direct=direct_config_file,
            site_mapping_data=json2dict(site_mapping_direct),
        )

        SN = recv_data["data"]["SN"]

        device_API = system_config.get_all_device_API()

        path_driver_file = (
            str(parent_dir_path) + "/" + str(device_API[SN].get_driver_location())
        )

        device_config = json2dict(device_API[SN]._Inverter__driver_location)

        if int(recv_data["data"]["type_register"]) == 1:
            type_function = mbdefines.WRITE_SINGLE_COIL
        elif int(recv_data["data"]["type_register"]) == 4:
            type_function = mbdefines.WRITE_SINGLE_REGISTER
            register = device_config["points"]["holding_registers"][
                recv_data["data"]["register"]
            ]["registerAddr"]

        device = ModbusDevice[str, int, float, int, int, int](
            connection=mbtcp.TcpMaster(
                device_API[SN].get_IP(), device_API[SN].get_port()
            ),
            device_SN=device_API[SN].get_SN(),
            client_ID=device_API[SN].get_ID(),
            decoder=DatabaseDecoder(),
            json_file_direct=path_driver_file,
        )

        print(
            device.write_raw_value(
                type_function=type_function,
                register=register,
                input_value=int(recv_data["data"]["new_data"]),
            )
        )

        data = snappy.compress(data="ok")
        await nc.publish(msg.reply, data)

        device.close_modbus()

    await nc.subscribe(topic, cb=messeage_handle)


def thread_recieve_nats_data(*args: Any, **kwargs: Any):
    site_config_folder_direct = args[0]["site_config_folder_direct"]
    default_config_file_direct = args[0]["default_config_file_direct"]
    user_credentials_path = args[0]["user_credentials_path"]
    cert_file_path = args[0]["cert_file_path"]
    key_file_path = args[0]["key_file_path"]
    rootCA_file_path = args[0]["rootCA_file_path"]

    list_config_file = [
        name
        for name in os.listdir(site_config_folder_direct)
        if "config" in name and "system" not in name
    ]

    for config_site in list_config_file:
        direct_config_file = site_config_folder_direct + config_site

        # Make dict for site (dict_device_in_site)

        asyncio.set_event_loop(event_loop_get_natsio_event)
        event_loop_get_natsio_event.create_task(
            recieve_nats_data_init(
                default_config_file_direct=default_config_file_direct,
                direct_config_file=direct_config_file,
                site_config_folder_direct=site_config_folder_direct,
                user_credentials_path=user_credentials_path,
                cert_file_path=cert_file_path,
                key_file_path=key_file_path,
                rootCA_file_path=rootCA_file_path,
            )
        )

    event_loop_get_natsio_event.run_forever()
