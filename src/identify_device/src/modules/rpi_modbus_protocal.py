import sys

from typing import *
from pathlib import Path

import modbus_tk.modbus_tcp as mbtcp
import modbus_tk.defines as mbdefines
import modbus_tk.modbus_rtu as mbrtu

parent_dir_path = str(Path(__file__).resolve().parents[4])
sys.path.append(parent_dir_path + "/src/modbuslib/src")

from rpi_modbus import ModbusDevice, DefaultDecoder


def read_TCP_device(
    host: str, port: int, client_ID: int, path_driver_file: str, device_SN: str = ""
):
    connection = mbtcp.TcpMaster(host, port, timeout_in_sec=0.5)
    device = ModbusDevice[str, int, float, int, int, int](
        connection=connection,
        device_SN=device_SN,
        client_ID=client_ID,
        decoder=DefaultDecoder(),
        json_file_direct=path_driver_file,
    )

    result = device.read_values(
        registers=["SN", "Md"],
        type_function=mbdefines.READ_HOLDING_REGISTERS,
    )

    device.close_modbus()
    return result


def read_RTU_device(
    connection: mbrtu, client_ID: int, path_driver_file: str, device_SN: str = ""
):
    device = ModbusDevice[str, int, float, int, int, int](
        connection=connection,
        device_SN=device_SN,
        client_ID=client_ID,
        decoder=DefaultDecoder(),
        json_file_direct=path_driver_file,
    )

    result = device.read_values(
        registers=["SN", "Md"],
        type_function=mbdefines.READ_INPUT_REGISTERS,
    )

    device.close_modbus()
    return result
