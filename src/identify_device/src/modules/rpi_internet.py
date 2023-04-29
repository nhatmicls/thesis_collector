import sys
import socket
import struct
import subprocess
from typing import *

from pathlib import Path

parent_dir_path = str(Path(__file__).resolve().parents[4])
sys.path.append(parent_dir_path + "/src/identify_device/src/modules")
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_ssh_protocal import ssh_command
from rpi_verbose import verbose


def get_all_device_in_network(gateway: str, mode: int = 1) -> List[str]:
    """
    @brief      Read and process data from modbus device
    @param      gateway                 Default gateway of host device
    @param      mode                    Scanning mode (0: Very fast mode, 1: Fast mode, 2: Slow mode)
    @retval     List of device available in network
    """

    if mode == 0:
        return_data = _scan_very_fast_all_device_in_network(gateway=gateway)
    elif mode == 1:
        return_data = _scan_fast_all_device_in_network(gateway=gateway)
    elif mode == 2:
        return_data = _scan_all_device_in_network(gateway=gateway)
    return return_data


def _scan_all_device_in_network(gateway: str) -> List[str]:
    verbose("SYSTEM - Scan thread", "Scanning fully network", "INFO")

    return_data: List[str] = []

    gateway = gateway + "/24"

    # Ping every ip address x.x.x.0 - x.x.x.255
    stdout = subprocess.check_output(["nmap", gateway, "-sn", "-Pn"])

    # Scan device have port 502 open
    stdout = subprocess.check_output(["nmap", gateway, "-Pn", "-p", " 502", "--open"])

    # Process nmap output
    _stdout = stdout.decode("utf-8").splitlines()
    for line in _stdout:
        if len(line) > 0:
            field = line.strip().split()
            if field[0] == "Nmap" and field[1] == "scan":
                dot_count = field[4].split(".")
                if len(dot_count) == 4:
                    return_data.append(field[4])
                else:
                    output = field[5]
                    output = output.replace("(", "")
                    output = output.replace(")", "")
                    return_data.append(output)

    return return_data


def _scan_fast_all_device_in_network(gateway: str) -> List[str]:
    verbose("SYSTEM - Scan thread", "Fast scan network", "INFO")

    return_data: List[str] = []

    gateway = gateway + "/24"

    # Ping every ip address x.x.x.0 - x.x.x.255
    stdout = subprocess.check_output(["nmap", gateway, "-sn", "-Pn"])

    # Scan device have port 502 open
    stdout = subprocess.check_output(["nmap", gateway, "-sn"])

    # Process nmap output
    _stdout = stdout.decode("utf-8").splitlines()
    for line in _stdout:
        if len(line) > 0:
            field = line.strip().split()
            if field[0] == "Nmap" and field[1] == "scan":
                dot_count = field[4].split(".")
                if len(dot_count) == 4:
                    return_data.append(field[4])
                else:
                    output = field[5]
                    output = output.replace("(", "")
                    output = output.replace(")", "")
                    return_data.append(output)

    return return_data


def _scan_very_fast_all_device_in_network(gateway: str) -> List[str]:
    verbose("SYSTEM - Scan thread", "Very fast scan network", "INFO")

    return_data: List[str] = []
    gateway_attribution = gateway.split(".")

    for x in range(1, 255):
        strline = (
            str(gateway_attribution[0])
            + "."
            + str(gateway_attribution[1])
            + "."
            + str(gateway_attribution[2])
            + "."
            + str(x)
        )
        return_data.append(strline)

    return return_data


def get_default_gateway_linux() -> Union[str, None]:
    return_data: str = ""
    with open("/proc/net/route") as fh:
        for line in fh:
            fields = line.strip().split()
            if fields[1] != "00000000" or not int(fields[3], 16) & 2:
                continue

            return_data = socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))

    return return_data


def get_host_default_gateway(user: str, pwds: str) -> str:
    return_data: str = ""
    ssh_stdout = ssh_command(get_default_gateway_linux(), user, pwds, "ip route")

    for line in ssh_stdout:
        field = line.strip().split()
        if field[0] == "default":
            return_data = field[2]

    return return_data
