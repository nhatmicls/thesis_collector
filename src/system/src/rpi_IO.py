import sys

from typing import *
from pathlib import Path

import modbus_tk.modbus_tcp as mbtcp
import modbus_tk.defines as mbdefines
import modbus_tk.modbus_rtu as mbrtu

import serial
import serial.tools.list_ports


def connect_serial(COM: str, time_out_rtu: int) -> mbrtu.RtuMaster:
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
    return_port.set_timeout(time_out_rtu)
    return_port.set_verbose(True)
    return return_port


def get_port_RS485() -> Union[str, None]:
    allports = [tuple(p) for p in list(serial.tools.list_ports.comports())]
    for currentport in allports:
        if "UART" in currentport[1]:
            return currentport[0]
        else:
            return None
    return None
