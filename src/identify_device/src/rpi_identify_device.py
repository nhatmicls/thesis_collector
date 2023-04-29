import sys, threading, os
import json, re

from typing import *
from pathlib import Path

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/identify_device/src/modules")
sys.path.append(parent_dir_path + "/src/modbuslib/src")
sys.path.append(parent_dir_path + "/src/database/src")
sys.path.append(parent_dir_path + "/src/natsio/src")
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_scan import scan_device_non_loop
from rpi_identify_device_exception import *
from rpi_internet import *
from rpi_modbus import *
from rpi_system import *
from rpi_FileIO import dict2json, json2dict
from rpi_verbose import verbose
from rpi_database import MAPPING_FILE_NAME


def seperate_static_dynamic(site_config_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    static_dict = {}
    dynamic_dict = {}

    for config in list(site_config_data.keys()):
        if "host" in site_config_data[config]:
            cache = site_config_data[config]
            cache.update({"device_type": site_config_data[config]["Md"]})
            static_dict.update({config: cache})
        else:
            dynamic_dict.update({config: site_config_data[config]})

    return (static_dict, dynamic_dict)


def identify_device_non_loop(
    site_config_data: Dict[str, Any],
    site_mapping_direct: str,
    driver_default_config_file_direct: str,
) -> Dict[str, Any]:
    data = {}

    # Read file
    try:
        site_mapping_data = json2dict(site_mapping_direct)
    except:
        site_mapping_data = {
            "keepDataAfterPowerLoss": "TRUE",
            "mapping_SN_IP": {},
        }
        dict2json(site_mapping_direct, site_mapping_data)
        site_mapping_data = json2dict(site_mapping_direct)
    driver_default_config_file = json2dict(driver_default_config_file_direct)
    # Scan and mapping
    verbose("SYSTEM - Scan thread", "Start scanning device", "INFO")

    static_dict, dynamic_dict = seperate_static_dynamic(site_config_data)

    if len(dynamic_dict) > 0:
        data = scan_device_non_loop(
            driver_default_config=driver_default_config_file,
            site_config_data=dynamic_dict,
        )

    site_mapping_data["keepDataAfterPowerLoss"] = "TRUE"
    site_mapping_data["mapping_SN_IP"].update(data)
    site_mapping_data["mapping_SN_IP"].update(static_dict)
    dict2json(site_mapping_direct, site_mapping_data)
    return site_mapping_data
