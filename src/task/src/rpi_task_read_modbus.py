import asyncio
import threading
import sys
import os
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
import modbus_tk.modbus_tcp as mbtcp
import modbus_tk.modbus_rtu as mbrtu  # type:ignore
import modbus_tk.defines as mbdefines

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/modbuslib/src")
sys.path.append(parent_dir_path + "/src/read_site_config/src")
sys.path.append(parent_dir_path + "/src/natsio/src")
sys.path.append(parent_dir_path + "/src/identify_device/src")
sys.path.append(parent_dir_path + "/src/system/src")
sys.path.append(parent_dir_path + "/src/database/src")
sys.path.append(parent_dir_path + "/src/task/src")
sys.path.append(parent_dir_path + "/src/connection/src")

import serial
import serial.tools.list_ports
from rpi_compress_data import *
from rpi_IO import *
from rpi_FileIO import json2dict
from rpi_modbus import (
    ModbusDevice,
    DatabaseDecoder,
    S,
    F,
    I,
    F,
    SF,
    E,
    B,
    PointContainer,
)
from rpi_natsio_client import NatsioSink, ProcessorActor, Source
from rpi_identify_device import *
from rpi_queue import clientQueue
from rpi_read_config import ConfigFile
from rpi_system import *
from rpi_verbose import verbose
from rpi_watchdog import Watchdog
from rpi_database import (
    device_database,
    actor_database,
    actor_error_database,
    thread_database,
    thread_error_database,
)
from rpi_natsio_connect import init_natsio

# Default number
LOOP_TIME: int = 5
TIMEOUT_RTU: int = 5
MAX_ERROR: int = 10

event_loop_read_modbus = asyncio.new_event_loop()
lock = threading.Lock()


def watchdog_timer_handle():
    verbose("WATCHDOG", "Time up", "INFO")


watchdog_Timer = Watchdog(300, watchdog_timer_handle)


def producer(
    serial_number: str,
    device: ModbusDevice,
    input_registers: List[str],
    holding_registers: List[str],
    protocol: str,
) -> Tuple[Dict[str, PointContainer[Union[S, I, F, SF, E, B]]], Dict[str, Exception]]:
    """producer function get data from modbus fuction

    Args:
        serial_number (str): serial number device
        device (ModbusDevice): Modbus connection
        input_registers (List[str]): data need to get in input register block
        holding_registers (List[str]): data need to get in holding register
        protocol (str): type of protocol to get data

    Returns:
        Tuple[Dict[str, PointContainer[Union[S, I, F, SF, E, B]]], Dict[str, Exception]]: Data get from modbus device
    """
    global watchdog_Timer
    modbus_error_list = [
        "No route to host",
        "timed out",
        "Host is unreachable",
        "Connection refused",
        "Network unreachable",
        "Modbus Error",
    ]

    def _kill_process_error_USB(error):
        if "Input/output error" in str(error):
            p = psutil.Process(psutil.Process().pid)
            p.kill()

    def _read(_read_register, _read_type_register, serial_number):
        if protocol == "RTU":
            with lock:
                data_recieve_holding = device.read_values(
                    _read_register, _read_type_register
                )
        else:
            data_recieve_holding = device.read_values(
                _read_register, _read_type_register
            )
        data_recieve_non_error.update(data_recieve_holding[0])
        data_recieve_error.update(data_recieve_holding[1])
        if serial_number in actor_error_database.get_list():
            actor_error_database.remove_from_list(SN=serial_number)

    def _error_process(error):
        error_name = str(error)
        for x in modbus_error_list:
            if x in error_name:
                if time_now > 6.5 and time_now < 18:
                    actor_error_database.add(SN=serial_number)
                    break
        verbose("MODB - Thread " + serial_number, error_name, "ERROR")
        _kill_process_error_USB(error)

    data_recieve_non_error: Dict[str, Any] = {}
    data_recieve_error: Dict[str, Any] = {}

    now = datetime.now()
    time_now = int(now.strftime("%H")) + 7 + int(now.strftime("%M")) / 60
    if time_now > 24:
        time_now -= 24

    if len(input_registers) > 0:
        try:
            _read(input_registers, mbdefines.READ_INPUT_REGISTERS, serial_number)
        except Exception as error:
            _error_process(error=error)

    if len(holding_registers) > 0:
        try:
            _read(holding_registers, mbdefines.READ_HOLDING_REGISTERS, serial_number)
        except Exception as error:
            _error_process(error=error)

    # watchdog_Timer.reset()
    return (data_recieve_non_error, data_recieve_error)


# Connect to RS485
async def init_serial():
    COM = get_port_RS485()
    if COM != None:
        return_port = mbrtu.RtuMaster(
            serial.Serial(
                port=COM,
                baudrate=9600,
                bytesize=8,
                parity="N",
                stopbits=1,
                xonxoff=0,
            )
        )
        return_port.set_timeout(TIMEOUT_RTU)
        return_port.set_verbose(True)
    else:
        return_port = None

    return return_port


async def nats_error_verify(location: str) -> bool:
    __thread_error_database = thread_error_database.get_list()

    if len(__thread_error_database) > 0:
        for thread_error_name in list(__thread_error_database.keys()):
            if location in thread_error_name:
                if "NATS" in list(__thread_error_database[thread_error_name].keys()):
                    if __thread_error_database[thread_error_name]["NATS"] > MAX_ERROR:
                        thread_error_database.remove_from_list(
                            "NATS", thread_error_name
                        )
                        return True
    return False


# Site subthread
async def read_modbus_init(
    default_config_file_direct: str = "",
    direct_config_file: str = "",
    user_credentials_path: str = "",
    cert_file_path: str = "",
    key_file_path: str = "",
    rootCA_file_path: str = "",
) -> None:
    global watchdog_Timer
    system_config = ConfigFile(
        driver_default_config_file_direct=default_config_file_direct,
        site_config_file_direct=direct_config_file,
        site_mapping_data={"mapping_SN_IP": {}},
    )
    tls = True

    metric_submission_init_data = system_config.get_metric_submission()
    topic = system_config.get_topic()
    maxsize_mem_ram = system_config.get_buffer_length()

    # Create temp folder if not exist
    dir = str(parent_dir_path) + "/queue_store"
    _location: str = metric_submission_init_data["location"]
    loc_dir = _location.replace(" ", "_")
    site_dir = (
        dir + "/push_queue_" + metric_submission_init_data["tenant"] + "_" + loc_dir
    )
    temp_dir = dir + "/temp"

    if not os.path.isdir(dir):
        os.mkdir(dir)
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    if cert_file_path == "":
        tls = False

    nc = NATS()

    # Check USB RS485 Adapter connect
    connection = await init_serial()

    queue = clientQueue(
        path=site_dir, tempdir=temp_dir, maxsize_mem_ram=maxsize_mem_ram
    )
    sink = NatsioSink.start(topic, queue, _location, nc).proxy()
    process = ProcessorActor.start(sink).proxy()

    while 1:
        # Get data from database
        dict_new_device_in_site = {}

        new_device_list = device_database.get_new_device()
        __actor_error_database = actor_error_database.get_list()
        __thread_error_database = thread_error_database.get_list()

        interval_time = 30

        nats_restart = await nats_error_verify(location=_location)
        if nats_restart == True:
            await nc.close()
            if sink.actor_ref.ask(nc) == "True":
                verbose("SYSTEM - " + _location, "NATS disconnected", "INFO")

        # Retry connect to NATS when device can't connect to server in first time
        if nc.is_connected == False:
            system_config = ConfigFile(
                driver_default_config_file_direct=default_config_file_direct,
                site_config_file_direct=direct_config_file,
                site_mapping_data={"mapping_SN_IP": {}},
            )

            nc = await init_natsio(
                server=system_config.get_NATS_server(),
                time_out=system_config.get_time_out(),
                user_credentials_path=user_credentials_path,
                cert_file_path=cert_file_path,
                key_file_path=key_file_path,
                rootCA_file_path=rootCA_file_path,
                thread_name=_location,
                tls=tls,
            )

            if nc.is_connected == True:
                if sink.actor_ref.ask(nc) == "True":
                    verbose("SYSTEM - " + _location, "NATS connected", "INFO")
                else:
                    verbose("SYSTEM - " + _location, "NATS import error", "ERROR")
            else:
                verbose("SYSTEM - " + _location, "NATS connect fail", "ERROR")

        site_name = json2dict(direct_path=direct_config_file)["Site_info"]["location"]

        # Check new device
        if len(new_device_list) > 0:
            _ = [
                dict_new_device_in_site.update({device_SN: new_device_list[device_SN]})
                for device_SN in [device for device in new_device_list]
                if new_device_list[device_SN]["location"] == site_name
            ]

        # Check error device
        if len(__actor_error_database) > 0:
            for actor_error_name in list(__actor_error_database.keys()):
                if __actor_error_database[actor_error_name] > MAX_ERROR:
                    actor_database.remove_actor(actor_error_name)
                    device_database.remove_known_device(actor_error_name)
                    actor_error_database.remove_from_list(actor_error_name)

        # Process new device
        if len(dict_new_device_in_site) > 0:
            system_config = ConfigFile(
                driver_default_config_file_direct=default_config_file_direct,
                site_config_file_direct=direct_config_file,
                site_mapping_data={"mapping_SN_IP": dict_new_device_in_site},
            )

            device_API = system_config.get_all_device_API()

            for i in device_API:
                path_driver_file = (
                    str(parent_dir_path)
                    + "/"
                    + str(device_API[i].get_driver_location())
                )
                input = device_API[i].get_points()

                if device_API[i].get_protocol() == "TCP":
                    device = ModbusDevice[str, int, float, int, int, int](
                        connection=mbtcp.TcpMaster(
                            device_API[i].get_IP(), device_API[i].get_port()
                        ),
                        device_SN=device_API[i].get_SN(),
                        client_ID=device_API[i].get_ID(),
                        decoder=DatabaseDecoder(),
                        json_file_direct=path_driver_file,
                    )
                elif device_API[i].get_protocol() == "RTU" and connection != None:
                    device = ModbusDevice[str, int, float, int, int, int](
                        connection=connection,
                        device_SN=device_API[i].get_SN(),
                        client_ID=device_API[i].get_ID(),
                        decoder=DatabaseDecoder(),
                        json_file_direct=path_driver_file,
                    )
                else:
                    raise

                # watchdog_Timer.start()
                actor_database.add(
                    serial_number=device_API[i].get_SN(),
                    source=Source.start(
                        device_API[i].get_SN(),
                        process,
                        producer,
                        device,
                        metric_submission_init_data,
                        device_API[i].get_metrics_group(),
                        device_API[i].get_protocol(),
                        list(input["input_registers"]),
                        list(input["holding_registers"]),
                    ).proxy(),
                )

                device_database.accept(device_API[i].get_SN())
                verbose(
                    "SYSTEM - " + metric_submission_init_data["location"],
                    "Added device " + device_API[i].get_SN(),
                    "INFO",
                )

        if len(dict_new_device_in_site) > 0:
            if nc.is_connected == True:
                interval_time = 300
            else:
                interval_time = 30

        await asyncio.sleep(interval_time)


# Thread manager
def thread_check_heath_modbus_device():
    pass


def generate_sub_modbus_device_thread(*args: Any, **kwargs: Any):
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

        asyncio.set_event_loop(event_loop_read_modbus)
        event_loop_read_modbus.create_task(
            read_modbus_init(
                default_config_file_direct=default_config_file_direct,
                direct_config_file=direct_config_file,
                user_credentials_path=user_credentials_path,
                cert_file_path=cert_file_path,
                key_file_path=key_file_path,
                rootCA_file_path=rootCA_file_path,
            )
        )

    event_loop_read_modbus.run_forever()


def thread_executive_sub_thread(*args: Any, **kwargs: Any) -> None:
    thread_name = "Read device thread"
    verbose("SYSTEM - Main modbus thread", "Start reading thread", "INFO")

    thread_database.add(
        "Main modbus thread", generate_sub_modbus_device_thread, args[0]
    )
    thread_database.join()
