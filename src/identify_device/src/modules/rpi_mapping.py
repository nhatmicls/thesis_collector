from re import M
import sys, threading, os
import json

from typing import *
from pathlib import Path


class define:
    _device_type = "device_type"
    _protocol = "protocol"
    _host = "host"
    _port = "port"
    _client_ID = "client_ID"
    _tenant = "tenant"
    _location = "location"
    _master_device_SN = "master_device_SN"
    _Natsio_servers_addr = "Natsio_servers_addr"
    _topic = "topic"

    # Type protocol
    _TCP = "TCP"
    _RTU = "RTU"


class Map:
    def __init__(self) -> None:
        self.list_device_SN: List[str] = []

    def get_list_device_SN(self, list_device_SN: List[str]) -> None:
        self.list_device_SN = list_device_SN

    def mapping_SN(
        self,
        device_SN: str,
        device_type: str,
        client_ID: int,
        site_config_data: Dict[str, Any],
        master_device_SN: str = "",
        host: str = "",
        port: int = 0,
    ):
        connection_type = site_config_data[device_SN]["protocol"]
        return_data: Dict[str, Any] = {}
        if device_SN in self.list_device_SN:
            if connection_type == define._TCP:
                return_data = {
                    device_SN: {
                        define._device_type: device_type,
                        define._protocol: connection_type,
                        define._host: host,
                        define._port: port,
                        define._client_ID: client_ID,
                        define._tenant: site_config_data[device_SN]["tenant"],
                        define._location: site_config_data[device_SN]["location"],
                        define._master_device_SN: master_device_SN,
                    }
                }
            elif connection_type == define._RTU:
                return_data = {
                    device_SN: {
                        define._device_type: device_type,
                        define._protocol: connection_type,
                        define._client_ID: client_ID,
                        define._tenant: site_config_data[device_SN]["tenant"],
                        define._location: site_config_data[device_SN]["location"],
                    }
                }
        else:
            pass
        return return_data
