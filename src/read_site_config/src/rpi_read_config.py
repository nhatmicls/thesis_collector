import sys, os, copy
import re

from typing import *
from pathlib import Path

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/read_site_config/src/modules")
sys.path.append(parent_dir_path + "/src/startup/src/modules")
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_FileIO import json2dict
from read_site_config_exception import (
    InValidPathError,
    UnRecognizeRegisterNameError,
    UnRecognizeDataTypeError,
    UnAcceptedConfigTypeError,
    UnAcceptedValueError,
    InvalidPointError,
    LackConditionError,
    MissingDevicePropertyError,
    MissingPropertyError,
    ReadPointsError,
)
from rpi_mapping import define as mapping_define


class ConfigFile:
    """
    This class contains all the infomation read from config file and from which this class
    reads information from corresponding driver to return list of registers from each type of
    register (input registers và holding registers) of the device
    """

    def __init__(
        self,
        driver_default_config_file_direct: str,
        site_config_file_direct: str,
        site_mapping_file_direct: str = "",
        site_mapping_data: Dict[str, Any] = {},
    ) -> None:
        self.__DEVICE_LIST: list = []
        self.__device_API: dict = {}
        self.__device_name: dict = {}

        self.__driver_default_config_file = json2dict(driver_default_config_file_direct)
        self.__site_config_file = json2dict(site_config_file_direct)
        if site_mapping_file_direct == "" and site_mapping_data != {}:
            self.__site_mapping_data = site_mapping_data
        elif site_mapping_file_direct != "" and site_mapping_data == {}:
            self.__site_mapping_data = json2dict(site_mapping_file_direct)

        self.read_site_config_file()
        self.read_device_config_file(self.__site_mapping_data)

    def read_site_config_file(self):
        try:
            self.__metric_submission = self.__read_site_config_file(key="Site_info")
            self.__NATS_server = self.__read_site_config_file(key="Natsio_servers_addr")
            self.__message_buffer = self.__read_site_config_file(key="message_buffer")
            self.__buffer_length = self.__message_buffer["memory_length"]
            self.__time_out = self.__read_site_config_file(key="time_out")
            self.__topic = self.__read_site_config_file(key="topic")
        except Exception as err:
            print(err)
            raise Exception(
                "Read config file fails because of error: {err}".format(err=err)
            )

    def read_device_config_file(self, site_mapping_data):
        for SN_number, device_property in site_mapping_data["mapping_SN_IP"].items():
            try:
                # Get general data
                protocol = self.__read_device_property(
                    device_property=device_property, key=mapping_define._protocol
                )
                device_id = self.__read_device_property(
                    device_property=device_property, key=mapping_define._client_ID
                )
                device_type = self.__read_device_property(
                    device_property=device_property, key=mapping_define._device_type
                )
                driver_location = self.__read_default_config_file(
                    device_type=device_type, key="path_relative_driver_file"
                )
                data_collect_path = self.__read_default_config_file(
                    device_type=device_type, key="data_collect_file"
                )

                # Get TCP property if it using TCP
                if protocol == mapping_define._TCP:
                    ip_address = self.__read_device_property(
                        device_property=device_property, key=mapping_define._host
                    )
                    port = self.__read_device_property(
                        device_property=device_property, key=mapping_define._port
                    )
                else:
                    ip_address = ""
                    port = 502

                # Get list data nedd to get
                if data_collect_path == "":
                    continue
                else:
                    data_collect_file = json2dict(data_collect_path)

                points_prop = self.__read_device_property(
                    device_property=data_collect_file, key="points"
                )
            except Exception as err:
                print(err)
                raise Exception(
                    "Read config file fails at model '{model}', device '{device}': {err}".format(
                        model=device_type, device=SN_number, err=err
                    )
                )

            # Get driver file
            try:
                driver = json2dict(driver_location)
            except Exception as err:
                print(err)
                message = "Error in config file, model '{model}'.\nCan't find file with directory: '{direct_path}'".format(
                    model=device_type, direct_path=driver_location
                )
                raise InValidPathError(message)

            metrics_group = self._set_metrics_group(
                device_type=device_type,
                driver=driver,
                device_id=device_id,
                SN_number=SN_number,
            )

            try:
                points, message = self.__get_points(points=points_prop, driver=driver)
            except ReadPointsError as err:
                print(err)
                msg = "Config file error at model '{model}' device '{device}'".format(
                    model=device_type, device=SN_number
                )
                raise InvalidPointError(msg)
            if message is not None:
                print(
                    "Config file warning at model '{model}' device '{device}': {message}".format(
                        model=device_type, device=SN_number, message=message
                    )
                )
            inverter = Inverter(
                model=device_type,
                metrics_group=metrics_group,
                IP=ip_address,
                ID=device_id,
                port=port,
                SN=SN_number,
                driver_location=driver_location,
                points=points,
                protocol=protocol,
            )
            self.__DEVICE_LIST.append(inverter)
            self.__device_API.update({SN_number: copy.deepcopy(inverter)})

    def _set_metrics_group(
        self, device_type: str, driver: Dict[str, Any], device_id: int, SN_number: str
    ) -> Dict[str, Any]:
        metrics_group = self.__driver_default_config_file.get("metrics_group")
        metrics_group["model"] = device_type
        metrics_group["version"] = driver["version"]
        metrics_group["manufacturer"] = driver["manufacturer"]
        metrics_group["serial_number"] = SN_number
        metrics_group["device_id"] = device_id
        return metrics_group

    def __read_site_config_file(self, key):
        """
        @brief: read config's property value from key
        @param:
                key: keyword of property
        @retval:
                property_value: config property's value
        """
        property_value = self.__site_config_file.get(key)
        if property_value is None:
            raise MissingPropertyError("Missing property: '{key}'".format(key=key))
        else:
            return property_value

    def __read_default_config_file(self, device_type, key):
        """
        @brief: read config's property value from key
        @param:
                key: keyword of property
        @retval:
                property_value: config property's value
        """
        driver_default_config_value = self.__driver_default_config_file[
            "support_device"
        ][device_type][key]
        if driver_default_config_value is None:
            raise MissingPropertyError("Missing property: '{key}'".format(key=key))
        else:
            return driver_default_config_value

    def __read_device_property(self, device_property, key):
        """
        @brief: read device's property value from key
        @param:
                device: device property in config file
                key: keyword of property
        @retval:
                property_value: device's property value
        """
        property_value = device_property.get(key)
        if property_value is None:
            message = "Missing '{key}' property".format(key=key)
            raise MissingDevicePropertyError(message)
        return property_value

    def __get_points(self, points: dict, driver: Dict[str, Any]):
        """
        @brief: get all the points from config file's request
        @param:
                points: config file's request to get points
                driver: driver's content of the device
        @retval:
                points: list of needed points to be read in dict of list form
                message: notify return if there is warning
        """
        message = None
        dtype_list: List[Any] = list(driver.get("unimplemented"))
        input_registers: Dict[str, Union[str, Dict[str, str]]] = driver.get(
            "points"
        ).get("input_registers")
        holding_registers: Dict[str, Union[str, Dict[str, str]]] = driver.get(
            "points"
        ).get("holding_registers")
        if "input_registers" in points.keys():
            input_regs_prop = points.get("input_registers")
            try:
                input_regs_list = self.__get_regs_list(
                    regs_prop=input_regs_prop,
                    regs_dict=input_registers,
                    dtype_list=dtype_list,
                )
            except LackConditionError as err:
                input_regs_list = []
                print(err)
                print(
                    "Warning: read input registers has not been executed because of missing property"
                )
                message = "reading input registers has not been executed"
            except Exception as err:
                print(err)
                raise ReadPointsError("Read input registers fails")
        else:
            input_regs_list = []
            if input_registers is not None:
                print(
                    "Warning: read input registers has not been executed because of missing 'input_registers' property"
                )
                message = "'input_registers' property is missing"
        if "holding_registers" in points.keys():
            holding_regs_prop = points.get("holding_registers")
            try:
                holding_regs_list = self.__get_regs_list(
                    regs_prop=holding_regs_prop,
                    regs_dict=holding_registers,
                    dtype_list=dtype_list,
                )
            except LackConditionError as err:
                holding_regs_list = []
                print(err)
                print(
                    "Warning: read holding registers has not been executed because of missing property"
                )
                message = "reading holding registers has not been executed"
            except Exception as err:
                print(err)
                raise ReadPointsError("Read holding registers fails")
        else:
            holding_regs_list = []
            print(
                "Warning: read holding registers has not been executed because of missing 'holding_registers' property"
            )
            message = "'holding_registers' property is missing"
        points = {
            "input_registers": tuple(input_regs_list),
            "holding_registers": tuple(holding_regs_list),
        }
        return points, message

    def __get_regs_list(
        self,
        regs_prop: Dict[str, Union[str, Dict[str, str]]],
        regs_dict: dict,
        dtype_list: list,
    ):
        """
        @brief: get the list of registers from config file's request
        @param:
                regs_prop: request of config file to get registers
                regs_dict: content of driver about registers that need to be listed
                dtype_list: list of accepted datatypes
        @retval:
                regs_list: registers list returned
        """
        if "read" not in regs_prop.keys() and "except" not in regs_prop.keys():
            raise LackConditionError("Missing both 'read' and 'except' property")
        else:
            if "read" in regs_prop.keys():
                read_prop = regs_prop.get("read")
                regs_list = self.__read_filter(
                    read_prop=read_prop, regs_dict=regs_dict, dtype_list=dtype_list
                )
            else:
                regs_list = list(regs_dict.keys())
            if "except" in regs_prop.keys():
                regs_list = self.__except_filter(
                    regs_prop=regs_prop,
                    regs_dict=regs_dict,
                    reg_list_prim=regs_list,
                    dtype_list=dtype_list,
                )

        return regs_list

    def __read_filter(self, read_prop: dict, regs_dict: dict, dtype_list: list):
        """
        @brief: get list of registers from the request of "read" attribute from config file
        @param:
                regs_prop: request of config file to get registers
                regs_dict: content of driver about registers that need to be listed
                dtype_list: list of accepted datatypes
        @retval:
                regs_list: registers list returned
        """
        all_regs = list(regs_dict.keys())
        if isinstance(read_prop, dict):
            if (
                "register" not in read_prop.keys()
                and "datatype" not in read_prop.keys()
                and "match" not in read_prop.keys()
            ):
                regs_list = []
            else:
                if (
                    "register" not in read_prop.keys()
                    and "match" not in read_prop.keys()
                ):
                    regs_list = all_regs
                else:
                    if "register" in read_prop.keys():
                        reg_prop = read_prop.get("register")
                        regs_list = self.__read_registers_filter(
                            reg_prop=reg_prop, reg_list_prim=all_regs
                        )
                    else:
                        regs_list = all_regs
                    if "match" in read_prop.keys():
                        mat_prop = read_prop.get("match")
                        regs_list = self.__get_register_by_regex(
                            mat_prop=mat_prop, reg_list_prim=regs_list
                        )
                    else:
                        pass
                if "datatype" in read_prop.keys():
                    dtype_prop = read_prop.get("datatype")
                    regs_list = self.__read_datatype_filter(
                        dtype_prop=dtype_prop,
                        regs_dict=regs_dict,
                        reg_list_prim=regs_list,
                        dtype_list=dtype_list,
                    )
                else:
                    pass
        else:
            raise UnAcceptedValueError(
                """Unexpected value 'read' : {phrase}""".format(phrase=read_prop)
            )
        return regs_list

    def __read_registers_filter(
        self, reg_prop: Union[Any, Dict[str, Any]], reg_list_prim: list
    ):
        """
        @brief: get list of registers from the request of "read"->"register" attribute from config file
        @param:
                regs_prop: request of config file to get registers
                reg_list_prim: list of primitive registers
        @retval:
                regs_list: registers list returned
        """
        if isinstance(reg_prop, list):
            regs_list = []
            for register in reg_prop:
                if register in reg_list_prim:
                    regs_list += [register]
                else:
                    raise UnRecognizeRegisterNameError(
                        "Unrecognize register name '{register_name}'".format(
                            register_name=register
                        )
                    )
        elif isinstance(reg_prop, str):
            if reg_prop in reg_list_prim:
                regs_list = [reg_prop]
            else:
                raise UnRecognizeRegisterNameError(
                    "Unrecognize register name '{register_name}'".format(
                        register_name=reg_prop
                    )
                )
        else:
            raise UnAcceptedValueError(
                "Unexpected value 'register': {register}".format(register=reg_prop)
            )
        return regs_list

    def __read_datatype_filter(
        self,
        dtype_prop: str or list,
        regs_dict: dict,
        reg_list_prim: list,
        dtype_list: list,
    ):
        """
        @brief: get list of registers from the request of "read"->"datatype" attribute from config file
        @param:
                regs_prop: request of config file to get registers
                regs_dict: content of driver about registers that need to be listed
                reg_list_prim: list of primitive registers
                dtype_list: list of accepted datatypes
        @retval:
                regs_list: registers list returned
        """
        if isinstance(dtype_prop, str):
            if dtype_prop not in dtype_list:
                raise UnRecognizeDataTypeError(
                    "Unregconize datatype : '{datatype}'".format(
                        datatype=type(dtype_prop)
                    )
                )
            else:
                regs_list = self.__get_register_by_datatype(
                    regs_dict=regs_dict,
                    reg_list_prim=reg_list_prim,
                    datatype=dtype_prop,
                    dtype_list=dtype_list,
                )
        elif isinstance(dtype_prop, list):
            regs_list = reg_list_prim
            for dt in dtype_prop:
                regs_list = self.__get_register_by_datatype(
                    regs_dict=regs_dict,
                    reg_list_prim=regs_list,
                    datatype=dt,
                    dtype_list=dtype_list,
                )
        else:
            raise UnAcceptedConfigTypeError(
                "Unexpected value 'datatype': {datatype}".format(
                    datatype=type(dtype_prop)
                )
            )
        return regs_list

    def __except_filter(
        self, regs_prop: dict, regs_dict: dict, reg_list_prim: list, dtype_list: list
    ):
        """
        @brief: filter the registers from the request of "except" attribute from config file
        @param:
                regs_prop: request of config file to get registers
                regs_dict: content of driver about registers that need to be listed
                reg_list_prim: list of primitive registers
                dtype_list: list of accepted datatypes
        @retval:
                regs_list: registers list returned
        """
        except_prop = regs_prop.get("except")
        regs_list = reg_list_prim
        all_regs = list(regs_dict.keys())
        if isinstance(except_prop, dict):
            if "register" in except_prop.keys():
                reg_prop = except_prop.get("register")
                regs_list = self.__except_registers_filter(
                    reg_prop=reg_prop, all_regs=all_regs, reg_list_prim=regs_list
                )
            if "match" in except_prop.keys():
                mat_prop = except_prop.get("match")
                regs_list = self.__get_register_by_regex(
                    mat_prop=mat_prop, reg_list_prim=regs_list, exc=True
                )
            if "datatype" in except_prop.keys():
                dtype_prop = except_prop.get("datatype")
                regs_list = self.__except_datatype_filter(
                    dtype_prop=dtype_prop,
                    regs_dict=regs_dict,
                    reg_list_prim=reg_list_prim,
                    dtype_list=dtype_list,
                )
        else:
            raise UnAcceptedValueError(
                """Unexpected value 'except' : {phrase}""".format(phrase=except_prop)
            )
        return regs_list

    def __except_registers_filter(
        self, reg_prop: Union[list, str], all_regs: list, reg_list_prim: list
    ):
        """
        @brief: filter the registers from the request of "except"->"register" attribute from config file
        @param:
                regs_prop: request of config file to get registers
                all_regs: list of all registers got from file driver
                reg_list_prim: list of primitive registers
        @retval:
                regs_list: registers list returned
        """
        regs_list = reg_list_prim
        if isinstance(reg_prop, list):
            for register in reg_prop:
                if register in all_regs:
                    if register in regs_list:
                        regs_list.remove(register)
                else:
                    raise UnRecognizeRegisterNameError(
                        "Unrecognize register name '{register_name}'".format(
                            register_name=register
                        )
                    )
        elif isinstance(reg_prop, str):
            if reg_prop in all_regs:
                if reg_prop in regs_list:
                    regs_list.remove(reg_prop)
            else:
                raise UnRecognizeRegisterNameError(
                    "Unrecognize register name '{register_name}'".format(
                        register_name=reg_prop
                    )
                )
        else:
            raise UnAcceptedValueError(
                "Unexpected value 'register': {datatype}".format(
                    datatype=type(reg_prop)
                )
            )
        return regs_list

    def __except_datatype_filter(
        self,
        dtype_prop: Union[list, str],
        regs_dict: dict,
        reg_list_prim,
        dtype_list: list,
    ):
        """
        @brief: filter the registers from the request of "except"->"datatype" attribute from config file
        @param:
                regs_prop: request of config file to get registers
                regs_dict: content of driver about registers that need to be listed
                reg_list_prim: list of primitive registers
                dtype_list: list of accepted datatypes
        @retval:
                regs_list: registers list returned
        """
        if isinstance(dtype_prop, str):
            if dtype_prop not in dtype_list:
                raise UnRecognizeDataTypeError("Unregconize datatype: " + dtype_prop)
            else:
                regs_list = self.__get_register_by_datatype(
                    regs_dict=regs_dict,
                    reg_list_prim=reg_list_prim,
                    datatype=dtype_prop,
                    dtype_list=dtype_list,
                    exc=True,
                )
        elif isinstance(dtype_prop, list):
            for dt in dtype_prop:
                regs_list = self.__get_register_by_datatype(
                    regs_dict=regs_dict,
                    reg_list_prim=reg_list_prim,
                    datatype=dt,
                    dtype_list=dtype_list,
                    exc=True,
                )
        else:
            raise UnAcceptedValueError(
                "Unexpected value 'datatype': {datatype}".format(
                    datatype=type(dtype_prop)
                )
            )
        return regs_list

    def __get_register_by_regex(
        self, mat_prop: str, reg_list_prim: list, exc: bool = False
    ):
        regs_list = []
        for reg in reg_list_prim:
            if exc:
                if len(re.findall(mat_prop, reg)) == 0:
                    regs_list += [reg]
            else:
                if len(re.findall(mat_prop, reg)) > 0:
                    regs_list += [reg]
        return regs_list

    def __get_register_by_datatype(
        self,
        regs_dict: Dict[Any, Any],
        reg_list_prim: list,
        datatype: str,
        dtype_list: list,
        exc: bool = False,
    ):
        """
        @brief: get registers based on their datatype attribute
        @param:
                regs_dict: content of driver about registers that need to be listed
                reg_list_prim: list of primitive registers
                datatype: datatype needs to be referen
                dtype_list: list of accepted datatype
                exc:
                    True: if input datatype is "except"->"datatype"
                    False: if input datatype is "read"->"datatype"
        @retval:
                regs_list: registers list returned
        """
        regs_list = []
        if datatype in dtype_list:
            for register in reg_list_prim:
                if register not in regs_dict.keys():
                    raise UnRecognizeRegisterNameError(
                        "Unrecognize register name '{register_name}'".format(
                            register_name=register
                        )
                    )
                else:
                    reg_prop: Dict[str, str] = regs_dict.get(register)
                    if reg_prop.get("datatype") == datatype:
                        if not exc:
                            regs_list += [register]
                    else:
                        if exc:
                            regs_list += [register]
        else:
            raise UnRecognizeDataTypeError(
                "Unregconize datatype : '{datatype}'".format(datatype=datatype)
            )
        return regs_list

    def get_device(self, model: str, name: str):
        """
        @brief: get class that contains device information using defined model and name
        in config file
        @param:
                model: model
                name: name
        @retval:
                device: if model and name match to a device in device list
                None: if model and name don't match to any device in device list
        """
        for device in self.__DEVICE_LIST:
            if device.get_model() == model and device.get_name() == name:
                return device
        return None

    def get_all_device_API(self):
        """
        @brief: get all API of devices declare in config file
        @retval: all device API
        """
        return self.__device_API

    def get_model(self, device_name):
        """
        @brief: get model of device whose name is given
        @param:
                device_name: name of device need to look up
        @retval: model of device if its name was declare in config file, None if
        device name is none exist
        """
        for model, device_name_list in self.__device_name.items():
            if device_name in device_name_list:
                return model
        else:
            return None

    def get_NATS_server(self):
        """
        @brief: get NATS server address
        @retval: NATS server address
        """
        return self.__NATS_server

    def get_time_out(self):
        """
        @brief: get time out value in second
        @retval: time out value
        """
        return self.__time_out

    def get_topic(self):
        """
        @brief: get NATS network topic
        @retval: NATS network topic
        """
        return self.__topic

    def get_metric_submission(self):
        """
        @brief: get metric submission of site
        @retval: metric submission of site
        """
        return self.__metric_submission

    def get_buffer_length(self):
        """get buffer message's memory length
        Returns:
            int: buffer message's memory length
        """
        return self.__buffer_length


class Inverter:
    """
    This class contains all the neccessary information about the device, namely:
        - Model
        - Metric group
        - IPv4 address
        - ID Modbus address
        - Port number
        - SN number
        - Location of device's driver
        - Points to read from request from config file
    """

    def __init__(
        self,
        model: str,
        metrics_group: dict,
        ID: str,
        SN: str,
        driver_location: str,
        points: dict,
        protocol: str,
        IP: str = "",
        port: int = 502,
    ) -> None:
        self.__model = model
        self.__metrics_group = metrics_group
        self.__IP = IP
        self.__ID = ID
        self.__port = port
        self.__SN = SN
        self.__driver_location = driver_location
        self.__points = points
        self.__protocol = protocol

    def get_model(self):
        """
        @brief: get model of device
        @retval: model's name of device
        """
        return self.__model

    def get_metrics_group(self):
        """
        @brief: get metrics group of device
        @retval: metrics group of device
        """
        return self.__metrics_group

    def get_IP(self):
        """
        @brief: get IP address of device
        @retval: IP address of device
        """
        return self.__IP

    def get_ID(self):
        """
        @brief: get ID address of device
        @retval: ID address of device
        """
        return self.__ID

    def get_port(self):
        """
        @brief: get port number of device
        @retval: port number of device
        """
        return self.__port

    def get_SN(self):
        """
        @brief: get SN number of device
        @retval: SN number of device
        """
        return self.__SN

    def get_driver_location(self):
        """
        @brief: get driver's location in relative to rpi-playground folder
        @retval: driver's location
        """
        return self.__driver_location

    def get_points(self):
        """
        @brief: get driver's points to read
        @retval: driver's points
        """
        return self.__points

    def get_protocol(self):
        """
        @brief: get driver's protocol to read
        @retval: driver's protocol
        """
        return self.__protocol
