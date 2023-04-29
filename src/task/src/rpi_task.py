import asyncio
import sys
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import FileIO
from pathlib import Path
import time
from typing import *
from urllib import parse
import threading


import persistqueue
import psutil
import pykka
from rx.core.typing import Disposable
from rx.scheduler.eventloop import AsyncIOScheduler

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/read_site_config/src")
sys.path.append(parent_dir_path + "/src/system/src")
sys.path.append(parent_dir_path + "/src/task/src")
sys.path.append(parent_dir_path + "/src/database/src")

from rpi_FileIO import json2dict
from rpi_verbose import verbose

from rpi_database import (
    device_database,
    CONFIG_FILE_NAME,
    thread_database,
    MAPPING_FILE_NAME,
)

from rpi_task_read_modbus import thread_executive_sub_thread
from rpi_task_scanning import thread_identification_device_in_network
from rpi_task_recieve_data import thread_recieve_nats_data

event_loop_modbus = asyncio.new_event_loop()
event_loop_scan_network = asyncio.new_event_loop()
event_loop_sync_data = asyncio.new_event_loop()


def __thread_modbus_master(*args: Any, **kwargs: Any):
    asyncio.set_event_loop(event_loop_modbus)
    event_loop_modbus.create_task(thread_executive_sub_thread(args[0]))
    event_loop_modbus.run_forever()


def __thread_scan_network(*args: Any, **kwargs: Any):
    asyncio.set_event_loop(event_loop_scan_network)
    event_loop_scan_network.create_task(
        thread_identification_device_in_network(
            site_config_folder_direct=args[0]["site_config_folder_direct"],
            default_config_file_direct=args[0]["default_config_file_direct"],
        )
    )
    event_loop_scan_network.run_forever()


def __thread_sync_data(*args: Any, **kwargs: Any):
    asyncio.set_event_loop(event_loop_sync_data)
    event_loop_sync_data.create_task(thread_recieve_nats_data(args[0]))
    event_loop_sync_data.run_forever()


def __import_old_data(site_config_folder_direct: str) -> None:
    """__import_old_data import lastest json file

    Import lastest json file when it restart

    Args:
        site_config_folder_direct (str): site config folder direct
    """

    verbose("SYSTEM - Initialization", "Start import old file", "INFO")

    try:
        device_database.add_doctrine_device(
            json2dict(site_config_folder_direct + CONFIG_FILE_NAME)
        )
        device_database.add_new_device(
            json2dict(site_config_folder_direct + MAPPING_FILE_NAME)
        )
        verbose("SYSTEM - Initialization", "Import completed", "INFO")
    except:
        verbose("SYSTEM - Initialization", "Import error", "WARNING")


def thread_base(
    user_credentials_path: str,
    cert_file_path: str,
    key_file_path: str,
    rootCA_file_path: str,
    default_config_file_direct: str,
    site_config_folder_direct: str,
):
    init_data = {
        "site_config_folder_direct": site_config_folder_direct,
        "default_config_file_direct": default_config_file_direct,
        "user_credentials_path": user_credentials_path,
        "cert_file_path": cert_file_path,
        "key_file_path": key_file_path,
        "rootCA_file_path": rootCA_file_path,
    }

    __import_old_data(site_config_folder_direct)

    thread_database.add(
        thread_name="scan_thread",
        thread_function=__thread_scan_network,
        thread_init_data=init_data,
    )
    # time.sleep(100)
    thread_database.add(
        thread_name="Modbus_thread",
        thread_function=__thread_modbus_master,
        thread_init_data=init_data,
    )

    thread_database.add(
        thread_name="Modbus_thread",
        thread_function=__thread_sync_data,
        thread_init_data=init_data,
    )

    thread_database.join()
