import json, sys
import re
from enum import Enum
import struct
from pathlib import Path
from typing import *

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/modbuslib/src/modules")
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_modbuslib_exceptions import (
    UnimplementedRegister,
    UnknownDataType,
    WrongInput,
    MissingInput,
)

from rpi_verbose import verbose

import serial

import modbus_tk.modbus_tcp as mbtcp
import modbus_tk.modbus_rtu as mbrtu  # type:ignore
import modbus_tk.defines as mbdefines

S = TypeVar("S")  # Generic output type for string_decoder
I = TypeVar("I")  # Generic output type for integer_decoder
SF = TypeVar("SF")  # Generic output type for scale_factor_decoder
F = TypeVar("F")  # Generic output type for float_decoder
E = TypeVar("E")  # Generic output type for enum_decoder
B = TypeVar("B")  # Generic output type for bitfield_decoder


class name_register_type(Enum):
    input_registers = mbdefines.READ_INPUT_REGISTERS
    holding_registers = mbdefines.READ_HOLDING_REGISTERS


T = TypeVar("T")  # Generic input type for PointContainer


class PointContainer(tuple, Generic[T]):
    value: T
    data_type: str
    unit: str

    def __new__(cls, value: T, data_type: str, unit: str):
        self = tuple.__new__(cls, (value, data_type, unit))
        self.value = value
        self.data_type = data_type
        self.unit = unit
        return self

    def __repr__(self) -> str:
        return f"Containers(value={self.value}, data_type={self.data_type}, unit={self.unit})"


class ModbusDecoder(Generic[S, I, F, SF, E, B]):

    """
    Wrap all decoder with generic
    """

    def __init__(
        self,
        string_decoder_func_pointer: Callable[
            [str, Tuple[int, ...], str, str, str, int], S
        ],
        int_decoder_func_pointer: Callable[
            [str, Tuple[int, ...], str, str, str, Union[SF, int], int], I
        ],
        float_decoder_func_pointer: Callable[
            [str, Tuple[int, ...], str, str, str, Union[SF, int], int], F
        ],
        sf_decoder_func_pointer: Callable[
            [str, Tuple[int, ...], str, str, str, int], SF
        ],
        enum_decoder_func_pointer: Callable[
            [str, Tuple[int, ...], str, str, str, Dict[str, str], int], E
        ],
        bitfield_decoder_func_pointer: Callable[
            [str, Tuple[int, ...], str, str, str, Dict[str, str], int], B
        ],
    ) -> None:
        """
        @brief      Define decoder function with generic
        @param      string_decoder_func_pointer             string decoder function
        @param      int_decoder_func_pointer                int decoder function
        @param      float_decoder_func_pointer              float decoder function
        @param      sf_decoder_func_pointer                 scale factor decoder function
        @param      enum_decoder_func_pointer               enum decoder function
        @param      bitfield_decoder_func_pointer           bitfield decoder function
        @retval     None
        """
        self.string_decoder_func = string_decoder_func_pointer
        self.int_decoder_func = int_decoder_func_pointer
        self.float_decoder_func = float_decoder_func_pointer
        self.sf_decoder_func = sf_decoder_func_pointer
        self.enum_decoder_func = enum_decoder_func_pointer
        self.bitfield_decoder_func = bitfield_decoder_func_pointer

        super().__init__()

    def string_decoder(
        self,
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        unimplement: int,
    ) -> S:
        return self.string_decoder_func(
            point, raw_value, data_type, byteOrder, wordOrder, unimplement
        )

    def integer_decoder(
        self,
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        scale_factor: Union[SF, int],
        unimplement: int,
    ) -> I:
        return self.int_decoder_func(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
            scale_factor,
            unimplement,
        )

    def float_decoder(
        self,
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        scale_factor: Union[SF, int],
        unimplement: int,
    ) -> F:
        return self.float_decoder_func(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
            scale_factor,
            unimplement,
        )

    def scale_factor_decoder(
        self,
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        unimplement: int,
    ) -> SF:
        return self.sf_decoder_func(
            point, raw_value, data_type, byteOrder, wordOrder, unimplement
        )

    def enum_decoder(
        self,
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        convert_dict: Dict[str, str],
        unimplement: int,
    ) -> E:
        return self.enum_decoder_func(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
            convert_dict,
            unimplement,
        )

    def bitfield_decoder(
        self,
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        convert_dict: Dict[str, str],
        unimplement: int,
    ) -> B:
        return self.bitfield_decoder_func(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
            convert_dict,
            unimplement,
        )

    class PreProcessDecoder:
        """Pre-process data"""

        def __init__(self) -> None:
            pass

        @staticmethod
        def process_registers(
            points: str, raw_values: Tuple[int, ...], data_type: str
        ) -> int:
            """
            @brief      Convert multi raw values from separate registers to single raw value
            @param      points          name of points
            @param      raw_values      raw value of points
            @param      data_type       data_type of variable, must be string
            @retval     raw data at data type
            """

            if "16" in data_type or "sunssf" in data_type:
                return_data = raw_values[0]
            elif "32" in data_type or "float" in data_type:
                return_data = raw_values[1] + raw_values[0] * 65536
            elif "64" in data_type:
                return_data = (
                    raw_values[3]
                    + raw_values[2] * 65536 ** 1
                    + raw_values[1] * 65536 ** 2
                    + raw_values[0] * 65536 ** 3
                )
            else:
                raise UnknownDataType(points, data_type)

            return return_data

        @staticmethod
        def LittleEndian_to_BigEndian(
            raw_value: Tuple[int, ...], type_order: str
        ) -> Tuple[int, ...]:
            """
            @brief      Convert Little Endian data to Big Endian data
            @param      raw_value           raw values of point
            @param      type_order          type of convert word order or byte order
            @retval     value after convert
            """

            return_data: Tuple[int, ...] = ()
            count = len(raw_value)
            if type_order == "wordOrder":
                for x in range(count - 1, -1, -1):
                    return_data += (raw_value[x],)
            elif type_order == "byteOrder":
                for x in range(count):
                    cache = int.to_bytes(raw_value[x], 2, "little")
                    cache = struct.unpack(">H", cache)[0]
                    return_data += (int(cache),)
            return return_data

        @staticmethod
        def pre_process(
            points: str,
            raw_values: Tuple[int, ...],
            data_type: str,
            byteOrder,
            wordOrder,
        ) -> int:
            """
            @brief      Preprocess data before decoder
            @param      points              name of points
            @param      data_type           data_type of variable, must be string
            @param      order               type of convert word order or byte order
            @param      raw_value           raw values of point
            @retval     value after preprocess
            """

            # Change from Little Endian to Big Endian
            if byteOrder == "Little_Endian":
                raw_values = ModbusDecoder.PreProcessDecoder.LittleEndian_to_BigEndian(
                    raw_values, "byteOrder"
                )
            if wordOrder == "Little_Endian":
                raw_values = ModbusDecoder.PreProcessDecoder.LittleEndian_to_BigEndian(
                    raw_values, "wordOrder"
                )

            return_data_int = ModbusDecoder.PreProcessDecoder.process_registers(
                points, raw_values, data_type
            )
            return return_data_int


class DatabaseDecoder(ModbusDecoder[str, int, float, int, int, int]):
    """
    Decode raw data to data can store in database
    """

    def __init__(self) -> None:
        super(DatabaseDecoder, self).__init__(
            DefaultDecoder.string_decoder,
            DefaultDecoder.integer_decoder,
            DefaultDecoder.float_decoder,
            DefaultDecoder.scale_factor_decoder,
            DatabaseDecoder.enum_decoder,
            DatabaseDecoder.bitfield_decoder,
        )

    @staticmethod
    def enum_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        convert_dict: Dict[str, str],
        unimplement: int,
    ) -> int:
        """
        @brief      Convert raw enum data to int value
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      convert_dict        human readable data for convert
        @param      unimplement         unimplement value of points
        @retval     Value as numbers
        """

        pre_process_value = ModbusDecoder.PreProcessDecoder.pre_process(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
        )

        if pre_process_value == unimplement:
            raise UnimplementedRegister(point)

        return pre_process_value

    @staticmethod
    def bitfield_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        convert_dict: Dict[str, str],
        unimplement: int,
    ) -> int:
        """
        @brief      Convert raw bitfiled data to int value
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      convert_dict        human readable data for convert
        @param      unimplement         unimplement value of points
        @retval     Value as numbers
        """

        pre_process_value = ModbusDecoder.PreProcessDecoder.pre_process(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
        )

        if pre_process_value == unimplement:
            raise UnimplementedRegister(point)

        return pre_process_value


class DefaultDecoder(ModbusDecoder[str, int, float, int, str, List[str]]):
    """
    Default decoder raw data to human readable
    """

    def __init__(self) -> None:
        super(DefaultDecoder, self).__init__(
            DefaultDecoder.string_decoder,
            DefaultDecoder.integer_decoder,
            DefaultDecoder.float_decoder,
            DefaultDecoder.scale_factor_decoder,
            DefaultDecoder.enum_decoder,
            DefaultDecoder.bitfield_decoder,
        )

    @staticmethod
    def enum_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        convert_dict: Dict[str, str],
        unimplement: int,
    ) -> str:
        """
        @brief      Convert raw enum data to human readable value
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      convert_dict        human readable data for convert
        @param      unimplement         unimplement value of points
        @retval     human readable value as string
        """

        pre_process_value = ModbusDecoder.PreProcessDecoder.pre_process(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
        )

        if pre_process_value == unimplement:
            raise UnimplementedRegister(point)

        return convert_dict[str(pre_process_value)]

    @staticmethod
    def bitfield_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        convert_dict: Dict[str, str],
        unimplement: int,
    ) -> List[str]:
        """
        @brief      Convert raw bitfiled data to human readable value
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      convert_dict        human readable data for convert
        @param      unimplement         unimplement value of points
        @retval     human readable value as list
        """

        return_data = []

        pre_process_value = ModbusDecoder.PreProcessDecoder.pre_process(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
        )

        if pre_process_value == unimplement:
            raise UnimplementedRegister(point)

        # detect every event
        for x in list(convert_dict.keys()):
            cache = pre_process_value & int(x)
            if cache == int(x):
                return_data.append(convert_dict[str(x)])

        return return_data

    @staticmethod
    def string_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        unimplement: int,
    ) -> str:
        """
        @brief      Convert raw string data to string
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      unimplement         unimplement value of points
        @retval     human readable value as string
        """

        data = []
        pre_process_value = raw_value
        zero_charater = 0
        count = len(raw_value)

        if byteOrder == "Little_Endian":
            pre_process_value = (
                ModbusDecoder.PreProcessDecoder.LittleEndian_to_BigEndian(
                    pre_process_value, "byteOrder"
                )
            )
        if wordOrder == "Little_Endian":
            pre_process_value = (
                ModbusDecoder.PreProcessDecoder.LittleEndian_to_BigEndian(
                    pre_process_value, "wordOrder"
                )
            )

        if raw_value[0] == unimplement:
            raise UnimplementedRegister(point)

        # int to hex and remove "0x"
        for index in range(count):
            cache = hex(pre_process_value[index]).replace("0x", "")
            if cache != "0":
                data.append(cache)

        data_str = "".join(data)

        # hex to string
        data_str = bytes.fromhex(data_str).decode("utf-8")

        # remove un-ascii character
        return_data = re.sub("\u0000", "", data_str)

        return return_data

    @staticmethod
    def scale_factor_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        unimplement: int,
    ) -> int:
        """
        @brief      Convert sunssf data to real number
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      unimplement         unimplement value of points
        @retval     human readable value as numbers
        """
        return_data: int = 0

        pre_process_value = ModbusDecoder.PreProcessDecoder.pre_process(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
        )

        if pre_process_value == unimplement:
            raise UnimplementedRegister(point)

        if pre_process_value > 32767:
            return_data = pre_process_value - 65536
        else:
            return_data = pre_process_value

        return return_data

    @staticmethod
    def integer_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        scale_factor: int,
        unimplement: int,
    ) -> int:
        """
        @brief      Convert raw data to real number
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      scale_factor        scale factor for convert to real value
        @param      unimplement         unimplement value of points
        @retval     human readable value as numbers
        """

        pre_process_value = ModbusDecoder.PreProcessDecoder.pre_process(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
        )

        if pre_process_value == unimplement:
            raise UnimplementedRegister(point)

        # if it sign number change to int ctype
        if (
            data_type == "int16" or data_type == "sunssf"
        ) and pre_process_value > 32767:
            pre_process_value -= 65536
        elif data_type == "int32" and pre_process_value > 2147483647:
            pre_process_value -= 4294967296
        elif data_type == "int64" and pre_process_value > 9223372036854775807:
            pre_process_value -= 18446744073709551616

        return_data = pre_process_value * 10 ** scale_factor

        return round(return_data, 5)

    @staticmethod
    def float_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str,
        byteOrder: str,
        wordOrder: str,
        scale_factor: int,
        unimplement: int,
    ) -> float:
        """
        @brief      Convert raw data to float number
        @param      point               name of point
        @param      raw_value           raw values of points
        @param      data_type           data_type of variable
        @param      byteOrder           byteOrder of variable
        @param      wordOrder           wordOrder of variable
        @param      scale_factor        scale factor for convert to real value
        @param      unimplement         unimplement value of points
        @retval     human readable value as numbers
        """

        pre_process_value = ModbusDecoder.PreProcessDecoder.pre_process(
            point,
            raw_value,
            data_type,
            byteOrder,
            wordOrder,
        )

        if pre_process_value == unimplement:
            raise UnimplementedRegister(point)
        data = int.to_bytes(pre_process_value, 4, "big")
        data = struct.unpack(">f", data)[0]
        float_value: float = data * 10 ** scale_factor

        return round(float_value, 5)

    @staticmethod
    def nop_decoder(
        point: str,
        raw_value: Tuple[int, ...],
        data_type: str = None,
        byteOrder: str = None,
        wordOrder: str = None,
        convert_dict: Dict[str, str] = None,
        unimplement: int = None,
    ) -> Tuple[int, ...]:
        return raw_value
