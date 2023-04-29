import sys, threading, os
from time import sleep

from typing import *
from pathlib import Path

import modbus_tk.modbus_tcp as mbtcp
import modbus_tk.defines as mbdefines
import modbus_tk.modbus_rtu as mbrtu
from modbus_tk.exceptions import ModbusError

parent_dir_path = str(Path(__file__).resolve().parents[4])
sys.path.append(parent_dir_path + "/src/identify_device/src/modules")
sys.path.append(parent_dir_path + "/src/modbuslib/src")
sys.path.append(parent_dir_path + "/src/natsio/src")
sys.path.append(parent_dir_path + "/src/system/src")
sys.path.append(parent_dir_path + "/src/database/src")

from rpi_identify_device_exception import DeviceNotSupported
from rpi_internet import get_host_default_gateway, get_all_device_in_network
from rpi_modbus import *
from rpi_system import *
from rpi_IO import connect_serial, get_port_RS485
from rpi_mapping import Map
from rpi_modbus_protocal import read_RTU_device, read_TCP_device
from rpi_verbose import verbose
from rpi_database import device_database

range_device_id_SMA_75 = [126, 167]
range_device_id_RTU = [1, 255]
mapping = Map()

device_count = 0


def filter_undiscovery_device(
    device_doctrine_dict: Dict[str, Any], device_discoveryed_dict: Dict[str, Any]
) -> str:
    return_data = ""

    _known_device_dict = list(device_database.get_known_device().keys())
    device_doctrine_list = list(device_doctrine_dict.keys())
    device_discoveryed_list = list(device_discoveryed_dict.keys())

    for x in device_discoveryed_list:
        if x in device_doctrine_list:
            device_doctrine_list.remove(x)

    for x in _known_device_dict:
        if x in device_doctrine_list:
            device_doctrine_list.remove(x)

    for x in device_doctrine_list:
        return_data += x + ", "

    return return_data


def filter_discovery_device(list_IP_available: List[str]) -> List[str]:
    return_data = list_IP_available
    _known_device_dict = device_database.get_known_device()

    _known_device_host_list = [
        _known_device_dict[x]["host"] for x in list(_known_device_dict.keys())
    ]

    for x in _known_device_host_list:
        if x in return_data:
            return_data.remove(x)

    return return_data


def run_check(total_device: int, minimum_requirement: float = 0.95) -> int:
    global device_count

    if device_count < total_device:
        verbose("SYSTEM - Scan thread", "Missing some device", "ERROR")
        if (device_count / total_device) <= minimum_requirement:
            verbose(
                "SYSTEM - Scan thread",
                "Not meet minimum requirement. Restart scanning",
                "ERROR",
            )
            return 1
        else:
            verbose(
                "SYSTEM - Scan thread", "Able to get all inverter in network", "INFO"
            )
            return 0
    else:
        verbose("SYSTEM - Scan thread", "Able to get all inverter in network", "INFO")
        return 0


def scan_non_standlone_TCP_device(
    current_IP: str,
    total_device: int,
    list_slave_device_type: list,
    support_device: Dict[str, Any],
    master_device_SN: str,
    site_info: Dict[str, Any],
    port: int = 502,
) -> Tuple[Dict[str, str], int]:
    device_count = 0
    for slave_device_type in list_slave_device_type:
        master_device_type = support_device[slave_device_type]["master_device_name"]
        range_clientID = [
            support_device[master_device_type]["min_range_slave"],
            support_device[master_device_type]["max_range_slave"],
        ]
        device_type = support_device[master_device_type]["device_type"]
        path_relative_driver_file = support_device[device_type][
            "path_relative_driver_file"
        ]
        return_data: Dict[str, str] = {}

        for client_ID in range(range_clientID[0], range_clientID[1], 1):
            try:
                result = read_TCP_device(
                    host=current_IP,
                    port=port,
                    client_ID=client_ID,
                    path_driver_file=path_relative_driver_file,
                )
                if result[0]["Md"][0] in slave_device_type:
                    result_mapping = mapping.mapping_SN(
                        device_SN=result[0]["SN"][0],
                        device_type=result[0]["Md"][0],
                        client_ID=client_ID,
                        host=current_IP,
                        port=port,
                        site_config_data=site_info,
                        master_device_SN=master_device_SN,
                    )
                    return_data.update(result_mapping)
                    if len(result_mapping) > 0:
                        device_count += 1
                        if device_count == total_device:
                            return return_data, device_count
            except Exception as e:
                pass

    return return_data, device_count


def scan_standlone_TCP_device(
    list_IP_available: List[str],
    total_device: int,
    driver_default_config: Dict[str, Any],
    site_config_data: Dict[str, Any],
    list_type_device: List[str],
    port: int = 502,
) -> Dict[str, str]:
    device_count = 0
    return_data: Dict[str, str] = {}

    _support_device = driver_default_config["support_device"]

    for current_IP in list_IP_available:
        try:
            confirm_device: bool = False
            for device_type in list_type_device:
                path_relative_driver_file = _support_device[device_type][
                    "path_relative_driver_file"
                ]

                client_ID = _support_device[device_type]["device_id_default"]

                try:
                    result = read_TCP_device(
                        host=current_IP,
                        port=port,
                        client_ID=client_ID,
                        path_driver_file=path_relative_driver_file,
                    )

                    if result[0]["Md"][0] in list(_support_device.keys()):
                        confirm_device = True
                        break

                except ModbusError as e:
                    verbose(
                        "SYSTEM - Scan thread",
                        "Error at " + current_IP + " Error code: " + str(e),
                        "ERROR",
                    )
                    continue
                except Exception as e:
                    verbose(
                        "SYSTEM - Scan thread",
                        "Error at " + current_IP + " Error code: " + str(e),
                        "ERROR",
                    )
                    raise e

            if confirm_device == False:
                raise

            result_mapping = mapping.mapping_SN(
                device_SN=result[0]["SN"][0],
                device_type=result[0]["Md"][0],
                client_ID=client_ID,
                host=current_IP,
                port=port,
                site_config_data=site_config_data,
            )
            return_data.update(result_mapping)
            if len(result_mapping) > 0:
                device_count += 1
                _master_device = _support_device[device_type]["master_device"]

                if _master_device == "TRUE":
                    slave_device_type = [
                        x
                        for x in list(_support_device.keys())
                        if _support_device[x]["slave_device"] == "TRUE"
                    ]

                    total_device_in_site = len(
                        [
                            x
                            for x in list(site_config_data.keys())
                            if result[0]["SN"][0]
                            == site_config_data[x]["master_device_SN"]
                        ]
                    )

                    if set(slave_device_type) & set(list_type_device):
                        data, slave_device_count = scan_non_standlone_TCP_device(
                            current_IP=current_IP,
                            total_device=total_device_in_site - 1,
                            list_slave_device_type=slave_device_type,
                            support_device=_support_device,
                            master_device_SN=result[0]["SN"][0],
                            site_info=site_config_data,
                        )
                        device_count += slave_device_count
                    return_data.update(data)
                if device_count == total_device:
                    verbose("SYSTEM - Scan thread", "Scan TCP - Full", "INFO")
                    return return_data
        except Exception as e:
            # print(e)
            pass

    undiscovery_device_list = filter_undiscovery_device(
        device_doctrine_dict=site_config_data, device_discoveryed_dict=return_data
    )

    _device_found = device_count + len(device_database.get_known_device())
    verbose(
        "SYSTEM - Scan thread",
        "Scan TCP - Missing (" + str(_device_found) + "/" + str(total_device) + ")",
        "INFO",
    )
    verbose(
        "SYSTEM - Scan thread",
        "List device not detect: " + undiscovery_device_list,
        "INFO",
    )

    return return_data


def scan_standlone_RTU_device(
    connection: mbrtu,
    range_clientID: List[int],
    total_device: int,
    list_type_device: List[str],
    site_config_data: Dict[str, Any],
    driver_default_config: Dict[str, Any],
) -> Dict[str, str]:
    return_data: Dict[str, str] = {}
    global device_count

    _support_device = driver_default_config["support_device"]
    for client_ID in range(range_clientID[0], range_clientID[1], 1):
        try:
            for device_type in list_type_device:
                path_relative_driver_file = _support_device[device_type][
                    "path_relative_driver_file"
                ]
                result = read_RTU_device(
                    connection=connection,
                    client_ID=client_ID,
                    path_driver_file=path_relative_driver_file,
                )
                if result[0]["Md"][0] in list(_support_device.keys()):
                    break

            result_mapping = mapping.mapping_SN(
                device_SN=result[0]["SN"][0],
                device_type=result[0]["Md"][0],
                client_ID=client_ID,
                site_config_data=site_config_data,
            )
            return_data.update(result_mapping)
            if len(result_mapping) > 0:
                device_count += 1
                if device_count == total_device:
                    verbose("SYSTEM - Scan thread", "Scan RTU - Full", "INFO")
                    return return_data
        except Exception as e:
            # print(e)
            pass

    undiscovery_device_list = filter_undiscovery_device(
        device_doctrine_dict=site_config_data, device_discoveryed_dict=return_data
    )

    _device_found = device_count + len(device_database.get_known_device())
    verbose(
        "SYSTEM - Scan thread",
        "Scan TCP - Missing (" + str(_device_found) + "/" + str(total_device) + ")",
        "INFO",
    )
    verbose(
        "SYSTEM - Scan thread",
        "List device not detect: " + undiscovery_device_list,
        "INFO",
    )
    return return_data


def scan_device_non_loop(
    driver_default_config: Dict[str, Any],
    site_config_data: Dict[str, Any],
) -> Dict[str, str]:
    # Global variable
    global device_count, mapping

    # Local variable
    return_data: Dict[str, str] = {}
    gateway_IP: str = ""
    list_IP_available: List[str] = []
    list_TCP_device: Dict[str, Any] = {}
    list_RTU_device: Dict[str, Any] = {}

    # Get data from default config
    _support_device = driver_default_config["support_device"]
    list_device_SN = list(site_config_data.keys())
    list_TCP_type_device = list(
        dict.fromkeys(
            [
                site_config_data[x]["Md"]
                for x in list(site_config_data.keys())
                if site_config_data[x]["protocol"] == "TCP"
            ]
        )
    )
    list_RTU_type_device = list(
        dict.fromkeys(
            [
                site_config_data[x]["Md"]
                for x in list(site_config_data.keys())
                if site_config_data[x]["protocol"] == "RTU"
            ]
        )
    )
    list_type_protocol = list(
        dict.fromkeys(
            [site_config_data[x]["protocol"] for x in list(site_config_data.keys())]
        )
    )

    mapping.get_list_device_SN(list_device_SN=list_device_SN)
    device_count = 0

    # check connect protocol
    if "TCP" in list_type_protocol:
        gateway_IP = get_host_default_gateway(
            user=os.getenv("USER"), pwds=os.getenv("UserPwds")
        )
        list_IP_available = get_all_device_in_network(gateway=gateway_IP, mode=2)
        list_IP_after_filter = filter_discovery_device(
            list_IP_available=list_IP_available
        )
    if "RTU" in list_type_protocol:
        USB_port_RS485 = get_port_RS485()
        RTU_connection = connect_serial(USB_port_RS485, 0.5)

    # Separate TCP list and RTU list if it in same site
    for device_info in list(site_config_data.keys()):
        if site_config_data[device_info]["Md"] not in list(_support_device.keys()):
            raise DeviceNotSupported(site_config_data[device_info]["Md"])
        if site_config_data[device_info]["protocol"] == "TCP":
            list_TCP_device.update({device_info: site_config_data[device_info]})
        elif site_config_data[device_info]["protocol"] == "RTU":
            list_RTU_device.update({device_info: site_config_data[device_info]})

    # start scanning and mapping device
    if "TCP" in list_type_protocol:
        verbose("SYSTEM - Scan thread", "Scan TCP - Start", "INFO")
        return_data.update(
            scan_standlone_TCP_device(
                list_IP_available=list_IP_after_filter,
                total_device=len(list_TCP_device),
                list_type_device=list_TCP_type_device,
                driver_default_config=driver_default_config,
                site_config_data=list_TCP_device,
            )
        )
        verbose("SYSTEM - Scan thread", "Scan TCP - Done", "INFO")
    if "RTU" in list_type_protocol:
        verbose("SYSTEM - Scan thread", "Scan RTU - Start", "INFO")
        return_data.update(
            scan_standlone_RTU_device(
                connection=RTU_connection,
                range_clientID=range_device_id_RTU,
                total_device=len(list_RTU_device),
                list_type_device=list_RTU_type_device,
                driver_default_config=driver_default_config,
                site_config_data=list_RTU_device,
            )
        )
        verbose("SYSTEM - Scan thread", "Scan RTU - Done", "INFO")

    return return_data
