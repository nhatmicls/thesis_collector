import os, re
import asyncio
import sys
from pathlib import Path
from typing import *

import pykka
from rx.scheduler.eventloop import AsyncIOScheduler

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/read_site_config/src")
sys.path.append(parent_dir_path + "/src/identify_device/src")
sys.path.append(parent_dir_path + "/src/system/src")
sys.path.append(parent_dir_path + "/src/database/src")
sys.path.append(parent_dir_path + "/src/task/src/task_exceptions")

from rpi_identify_device import identify_device_non_loop
from rpi_read_config import ConfigFile
from rpi_verbose import verbose
from rpi_database import device_database, CONFIG_FILE_NAME, MAPPING_FILE_NAME
from rpi_FileIO import json2dict, dict2json
from rpi_task_scan_exceptions import FileNotFound

_scan_interval = 300
_update_config_interval = 600


class DoctrineDevice(pykka.ThreadingActor):
    """DoctrineDevice Class handling read file config"""

    def __init__(
        self,
        site_config_folder_direct: str,
        scan_function: Callable[[str], None],
    ) -> None:
        """Create new thread handling read file config

        Args:
            site_config_folder_direct (str): site config folder direct
            scan_function (Callable[[str], None]): custom read config function
        """

        super().__init__()
        scheduler = AsyncIOScheduler(asyncio.get_event_loop())
        self._disposable = scheduler.schedule_periodic(
            _update_config_interval,
            lambda _: scan_function(
                site_config_folder_direct,
            ),
        )

    def on_stop(self) -> None:
        self._disposable.dispose()


class IdentificationDevice(pykka.ThreadingActor):
    """IdentificationDevice Class handling scan network and define device in network"""

    def __init__(
        self,
        site_config_folder_direct: str,
        default_config_file_direct: str,
        indentify_function: Callable[[str, str], None],
    ) -> None:
        """__init__ Create thread for identify device in network

        Args:
            site_config_folder_direct (str): site config folder direct
            default_config_file_direct (str): defaul config file direct
            indentify_function (Callable[[str, str], None]): custom function for identify device
        """
        super().__init__()
        scheduler = AsyncIOScheduler(asyncio.get_event_loop())
        self._disposable = scheduler.schedule_periodic(
            _scan_interval,
            lambda _: indentify_function(
                site_config_folder_direct,
                default_config_file_direct,
            ),
        )

    def on_stop(self) -> None:
        self._disposable.dispose()


def convert(match_obj: re.Match):
    string_data: str = match_obj.string[match_obj.regs[0][0] : match_obj.regs[0][1]]
    return string_data.replace(string_data, string_data[1])


def separate_mapping_file(site_mapping_direct: str) -> None:
    if os.path.isfile(site_mapping_direct) == True:
        mapping_data = json2dict(site_mapping_direct)
    else:
        return

    list_location: List[str] = list(
        dict.fromkeys(
            [
                mapping_data["mapping_SN_IP"][x]["location"]
                for x in list(mapping_data["mapping_SN_IP"].keys())
            ]
        )
    )

    for _location in list_location:
        site_mapping_by_location = {}
        location = re.sub("\s[A-Z]+", convert, _location)
        location = location.replace(" ", "_")
        _site_mapping_direct = site_mapping_direct.replace(
            MAPPING_FILE_NAME, "mapping_" + location + ".json"
        )
        _ = [
            site_mapping_by_location.update({x: mapping_data["mapping_SN_IP"][x]})
            for x in list(mapping_data["mapping_SN_IP"].keys())
            if mapping_data["mapping_SN_IP"][x]["location"] == _location
        ]

        dict2json(_site_mapping_direct, {"mapping_SN_IP": site_mapping_by_location})


def __reformat_config_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """__reformat_config_data Change format dict of site config

    Add topic and Nats server to unit

    Args:
        data (Dict[str, Any]): site config each location

    Returns:
        Dict[str, Any]: site config after reformat
    """

    return_data = {}
    device_info: Dict[str, Any] = data["device_SN"]
    site_info: Dict[str, Any] = data["Site_info"]
    for device_keys in list(device_info.keys()):
        cache = device_info[device_keys]
        cache.update(site_info)
        cache.update({"topic": data["topic"]})
        cache.update({"Natsio_servers_addr": data["Natsio_servers_addr"]})
        return_data.update({cache["SN"]: cache})
    return return_data


def __combine_file_config(site_config_folder_direct: str) -> None:
    """__combine_file_config combine site config into one file

    Args:
        site_config_folder_direct (str): site config folder direct

    Raises:
        FileNotFound: Raise when it can not find any config file
    """

    config_file_list = os.listdir(site_config_folder_direct)
    old_combine_site_data = device_database.get_doctrine_device()
    new_combine_site_data = {}

    verbose("SYSTEM - Scan thread", "Start read and combine config file", "INFO")

    for file_name in [
        name
        for name in os.listdir(site_config_folder_direct)
        if "config" in name and "system" not in name
    ]:
        cache = json2dict(site_config_folder_direct + file_name)
        cache = __reformat_config_data(cache)
        new_combine_site_data.update(cache)

    if new_combine_site_data == {}:
        raise FileNotFound

    if len(new_combine_site_data) > len(old_combine_site_data):
        verbose("SYSTEM - Scan thread", "New device detected", "INFO")
    elif len(new_combine_site_data) < len(old_combine_site_data):
        verbose("SYSTEM - Scan thread", "Remove device detected", "INFO")

    dict2json(site_config_folder_direct + CONFIG_FILE_NAME, new_combine_site_data)
    device_database.add_doctrine_device(new_combine_site_data)


def __identification_device(
    site_config_folder_direct: str,
    default_config_file_direct: str = "./config/driver/default_config.json",
) -> None:
    """__identification_device function to identify device in network

    Args:
        site_config_folder_direct (str): site config folder direct
        default_config_file_direct (str, optional): default config file direct. Defaults to "./config/driver/default_config.json".
    """
    combine_site_data = device_database.get_doctrine_device()
    number_device_defined = len(device_database.get_new_device()) + len(
        device_database.get_known_device()
    )
    site_mapping_direct = site_config_folder_direct + MAPPING_FILE_NAME
    separate_mapping_file(site_mapping_direct)

    if (
        len(combine_site_data) == number_device_defined
        and device_database.modifine_state == False
    ):
        verbose(
            "SYSTEM - Scan thread", "Device number is good no need to rescan", "INFO"
        )
        return

    verbose("SYSTEM - Scan thread", "Start scan task", "INFO")

    site_detail_data = identify_device_non_loop(
        site_config_data=combine_site_data,
        site_mapping_direct=site_mapping_direct,
        driver_default_config_file_direct=default_config_file_direct,
    )
    list_known_device = list(device_database.get_known_device().keys())
    list_new_device = list(device_database.get_new_device().keys())

    try:
        _ = [site_detail_data["mapping_SN_IP"].pop(x) for x in list_known_device]
        _ = [site_detail_data["mapping_SN_IP"].pop(x) for x in list_new_device]
    except Exception as e:
        verbose("SYSTEM - Scan thread", e, "ERROR")
    device_database.add_new_device(site_detail_data)


async def thread_identification_device_in_network(
    site_config_folder_direct: str,
    default_config_file_direct: str,
):
    thread_name = "Scan thread"
    __combine_file_config(site_config_folder_direct)
    __identification_device(
        site_config_folder_direct,
        default_config_file_direct,
    )
    DoctrineDevice.start(site_config_folder_direct, __combine_file_config).proxy()
    IdentificationDevice.start(
        site_config_folder_direct,
        default_config_file_direct,
        __identification_device,
    ).proxy()
