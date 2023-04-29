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


class ModbusDevice(Generic[S, I, F, SF, E, B]):
    """
    @brief      Read and process data from modbus device
    @param      connection              Connect of device
    @param      client_ID               Client ID
    @param      decoder                 Decoder
    @param      json_file_direct        Config file directory
    @retval     None
    """

    def __init__(
        self,
        decoder: ModbusDecoder[S, I, F, SF, E, B],
        json_file_direct: str,
        client_ID: int,
        device_SN: str = "",
        IP: str = "",
        port: int = 502,
        serial_connect: serial.Serial = "",
        type_connect: str = "",
    ) -> None:
        super(ModbusDevice, self).__init__()
        self.device_SN = device_SN
        self.client_ID = client_ID
        self.decoder = decoder
        self.name_type_register: str = ""
        self.scale_factor: Dict[str, SF] = {}
        with open(json_file_direct, "r") as f:
            self.json_file = json.load(f)
        f.close()
        self.offset = self.json_file["offset"]
        self.modbus_client: Union[mbtcp.TcpMaster, mbrtu.RtuMaster] = None
        if type_connect == "RTU":
            self.modbus_client = mbrtu.RtuMaster(serial_connect)
        elif type_connect == "TCP":
            self.modbus_client = mbtcp.TcpMaster(host=IP, port=port, timeout_in_sec=0.5)

    """
    Wrap data to valid block data
    """

    def replace_spec_character(self, input: str) -> str:
        input = input.replace("(", "")
        input = input.replace(")", "")
        input = input.replace(" ", "_")
        input = input.replace("%", "per_")
        input = input.replace("-", "_")
        input = input.replace("/", "_")
        return input

    def wrap_return_data(self, point: str, result: T) -> Dict[str, PointContainer[T]]:
        """
        @brief      Pre-process multi point data to human readable data
        @param      point           name of point
        @param      result          value of point (human readable or raw value)
        @retval     Return value in specific type
        """

        data_type_json = self.json_file["points"][self.name_type_register][point][
            "datatype"
        ]

        try:
            unit = self.json_file["points"][self.name_type_register][point]["unit"]
        except:
            unit = ""

        # place data in right place
        return_data_value: PointContainer[T] = PointContainer(
            result, data_type_json, self.replace_spec_character(unit)
        )

        return_data = {self.replace_spec_character(point): return_data_value}

        return return_data

    """
    Process value to valid data type
    """

    def process_multi_data(
        self, point: List[str], raw_values: Dict[str, Tuple[int, ...]]
    ) -> Tuple[
        Dict[str, PointContainer[Union[S, I, F, SF, E, B]]], Dict[str, Exception]
    ]:
        """
        @brief      Process multi point data to human readable data
        @param      point               name of point
        @param      raw_values          raw values of point
        @retval     Multi human readable value
        """

        scale_factor: Dict[str, SF] = {}
        return_data = {}
        return_error = {}

        SF_matches = [x for x in raw_values.keys() if "SF" in x]

        # get scale factor value
        if len(SF_matches) > 0:
            for scale_factor_name in SF_matches:
                try:
                    scale_factor_int = self.decoder.scale_factor_decoder(
                        scale_factor_name,
                        raw_values[scale_factor_name],
                        self.json_file["points"][self.name_type_register][
                            scale_factor_name
                        ]["datatype"],
                        self.json_file["points"][self.name_type_register][
                            scale_factor_name
                        ]["byteOrder"],
                        self.json_file["points"][self.name_type_register][
                            scale_factor_name
                        ]["wordOrder"],
                        self.json_file["unimplemented"][
                            self.json_file["points"][self.name_type_register][
                                scale_factor_name
                            ]["datatype"]
                        ],
                    )
                    scale_factor = {scale_factor_name: scale_factor_int}
                    self.scale_factor.update(scale_factor)
                except Exception as error:
                    self.scale_factor.update(scale_factor)

        # process data
        for name_register in point:
            transmit_data: Tuple[int, ...] = raw_values[name_register]
            try:
                return_data.update(self.process_data(name_register, transmit_data))
            except Exception as error:
                return_error.update({name_register: error})

        return (return_data, return_error)

    def process_data(
        self, point: str, raw_values: Tuple[int, ...]
    ) -> Dict[str, PointContainer[Union[S, I, F, SF, E, B]]]:
        """
        @brief      Process single register data to human readable data
        @param      register        name of register
        @param      raw_values      raw values of register
        @retval     Single human readable value
        """

        points_featured = self.json_file["points"][self.name_type_register][point]
        data_type = points_featured["datatype"]
        byteOrder = points_featured["byteOrder"]
        wordOrder = points_featured["wordOrder"]
        scale_factor: Union[SF, int] = 0

        # Check that pointer need scalefactor, if no it will skip
        try:
            if "int" in data_type or "float" in data_type or "acc" in data_type:
                points_SF = points_featured["scaleFactor"]
                if isinstance(points_SF, str):
                    scale_factor = self.scale_factor[points_SF]
                elif isinstance(points_SF, int):
                    scale_factor = points_SF
        except:
            scale_factor = 0

        if "enum" in data_type:  # if data is enum
            dict = self.json_file["constants"][data_type][point]
            data_enum = self.decoder.enum_decoder(
                point,
                raw_values,
                data_type,
                byteOrder,
                wordOrder,
                dict,
                self.json_file["unimplemented"][data_type],
            )
            return self.wrap_return_data(point, data_enum)
        elif "bitfield" in data_type:  # if data is bitfield
            dict = self.json_file["constants"][data_type][point]
            data_bitfield = self.decoder.bitfield_decoder(
                point,
                raw_values,
                data_type,
                byteOrder,
                wordOrder,
                dict,
                self.json_file["unimplemented"][data_type],
            )
            return self.wrap_return_data(point, data_bitfield)
        elif data_type == "string" or data_type == "UTF-8":  # if data is string
            data_string = self.decoder.string_decoder(
                point,
                raw_values,
                data_type,
                byteOrder,
                wordOrder,
                self.json_file["unimplemented"][data_type],
            )
            return self.wrap_return_data(point, data_string)
        elif (
            "int" in data_type or "uint" in data_type or "acc" in data_type
        ):  # if data is int16/uint16/acc16/int32/uint32/acc32/int64/acc64
            data_int = self.decoder.integer_decoder(
                point,
                raw_values,
                data_type,
                byteOrder,
                wordOrder,
                scale_factor,
                self.json_file["unimplemented"][data_type],
            )
            return self.wrap_return_data(point, data_int)
        elif data_type == "float":
            data_float = self.decoder.float_decoder(
                point,
                raw_values,
                data_type,
                byteOrder,
                wordOrder,
                scale_factor,
                self.json_file["unimplemented"][data_type],
            )
            return self.wrap_return_data(point, data_float)
        elif data_type == "sunssf":
            data_ssf = self.decoder.scale_factor_decoder(
                point,
                raw_values,
                data_type,
                byteOrder,
                wordOrder,
                self.json_file["unimplemented"][data_type],
            )
            return self.wrap_return_data(point, data_ssf)
        else:
            raise UnknownDataType(point, data_type)

    """
    Read value from device fuction
    """

    def read_raw_values(
        self, points_input: Tuple[str, ...], type_function: mbdefines
    ) -> Dict[str, Tuple[int, ...]]:
        """
        @brief      Read multi points
        @param      points_input      multi name of points
        @param      type_function   where is points locate
        @retval     Multi name of points and multi raw value of points
        """

        length_data_preprocess = []
        start_point_preprocess = []
        result: Tuple[int, ...] = ()
        register_name_list = []
        return_data: Dict[str, Tuple[int, ...]] = {}

        counter = 0
        cache = 0
        start_register = 0

        # Make points immutable list
        points: List[str] = list(points_input)

        for point_name in points_input:
            if "SF" in point_name:
                continue
            try:
                points_SF = self.json_file["points"][self.name_type_register][
                    point_name
                ]["scaleFactor"]
                if isinstance(points_SF, str):
                    if not points_SF in points:
                        points.append(points_SF)
                elif isinstance(points_SF, int):
                    pass
            except Exception as e:
                # verbose("MODBUS - " + self.device_SN, str(e), "ERROR")
                pass

        # Divide multi register to multi block of 120 register or less
        for point_name in (self.json_file["points"][self.name_type_register]).items():
            if point_name[0] in points:
                if counter == 0:
                    start_register = self.json_file["points"][self.name_type_register][
                        point_name[0]
                    ]["registerAddr"]
                    start_register_cache = start_register
                    counter = 1
                else:
                    counter += 1

                if counter > 0:
                    register_addr = self.json_file["points"][self.name_type_register][
                        point_name[0]
                    ]["registerAddr"]
                    reg_len = self.json_file["points"][self.name_type_register][
                        point_name[0]
                    ]["count"]
                    delta_length = register_addr - start_register_cache + reg_len
                    if counter == len(points) and delta_length <= 120:
                        length_data_preprocess.append(delta_length)
                        start_point_preprocess.append(start_register_cache)
                        register_name_list.append(point_name[0])
                        break
                    elif counter == len(points) and delta_length > 120:
                        length_data_preprocess.append(cache)
                        start_point_preprocess.append(start_register_cache)
                        delta_length += start_register_cache
                        delta_length -= register_addr
                        length_data_preprocess.append(delta_length)
                        start_point_preprocess.append(register_addr)
                        register_name_list.append(point_name[0])
                        break
                    elif delta_length > 120:
                        length_data_preprocess.append(cache)
                        start_point_preprocess.append(start_register_cache)
                        delta_length += start_register_cache
                        start_register_cache = register_addr
                        delta_length -= start_register_cache
                        register_name_list.append(point_name[0])
                        cache = delta_length
                    else:
                        cache = delta_length
                        register_name_list.append(point_name[0])

        # Get raw data from 120-registers block
        for x in range(len(start_point_preprocess)):
            process_value: Tuple[int, ...] = ()
            result = self.read_raw_value(
                start_point_preprocess[x], type_function, length_data_preprocess[x]
            )

            for point_name in register_name_list:
                try:
                    reg_address = self.json_file["points"][self.name_type_register][
                        point_name
                    ]["registerAddr"]
                    reg_len = self.json_file["points"][self.name_type_register][
                        point_name
                    ]["count"]
                    mapping_reg = reg_address - start_point_preprocess[x]
                    process_value = tuple(
                        list(result)[mapping_reg : mapping_reg + reg_len]
                    )
                    if mapping_reg + reg_len > len(result):
                        raise

                    return_data.update({point_name: process_value})
                except:
                    reg_index = register_name_list.index(point_name)
                    del register_name_list[0:reg_index]
                    break

        return return_data

    def read_raw_value(
        self, register: Union[str, int], type_function: mbdefines, length: int = 0
    ) -> Tuple[int, ...]:
        """
        @brief      Read register
        @param      register        name of register or register address
        @param      type_register   where is points locate
        @param      length          how many register should be read
        @retval     Raw value of single/multi register
        """

        if isinstance(register, str):
            if length == 0:
                length = self.json_file["points"][self.name_type_register][register][
                    "count"
                ]
            register_int = self.json_file["points"][self.name_type_register][register][
                "registerAddr"
            ]
        else:
            register_int = register

        if self.modbus_client._do_open == False:
            self.modbus_client.open()

        result = self.modbus_client.execute(
            slave=self.client_ID,
            function_code=type_function,
            starting_address=register_int - self.offset,
            quantity_of_x=length,
        )

        if self.modbus_client._is_opened == True:
            self.modbus_client.close()

        return result

    def read_values(
        self, registers: List[str], type_function: mbdefines
    ) -> Tuple[
        Dict[str, PointContainer[Union[S, I, F, SF, E, B]]], Dict[str, Exception]
    ]:
        """
        @brief      Read value
        @param      registers       list name of points
        @param      type_register   where is points locate
        @retval     Block of data after process
        """

        if not isinstance(registers, list):
            raise WrongInput(self.read_values.__name__, "points", "list")

        self.name_type_register = name_register_type(type_function).name

        if len(registers) > 0:
            value_dict = self.read_raw_values(tuple(registers), type_function)
            return_data = self.process_multi_data(registers, value_dict)
            return return_data
        else:
            raise MissingInput(self.read_values.__name__, "points")

    """
    Write value to device fuction
    """

    def write_raw_value(
        self,
        register: int,
        type_function: mbdefines,
        input_value: Union[int, List[int]],
    ) -> Tuple[int, ...]:
        if isinstance(register, str):
            if length == 0:
                length = self.json_file["points"][self.name_type_register][register][
                    "count"
                ]
            register_int = self.json_file["points"][self.name_type_register][register][
                "registerAddr"
            ]
        else:
            register_int = register

        if self.modbus_client._is_opened == False:
            self.modbus_client.open()

        result = self.modbus_client.execute(
            slave=self.client_ID,
            function_code=type_function,
            starting_address=register_int - self.offset,
            output_value=input_value,
        )

        if self.modbus_client._is_opened == True:
            self.modbus_client.close()

        return result

    """
    Connect function
    """

    def close_modbus(self):
        self.modbus_client.close()
