from typing import *
import time

import snappy
import rpi_natsio_schema_pb2

from rpi_modbus import PointContainer


class CompressData:
    def __init__(self) -> None:
        pass

    @staticmethod
    def create_new_metric_submission(
        tenant: str, location: str
    ) -> rpi_natsio_schema_pb2.MetricSubmission:
        """
        @brief      Create new metric site
        @param      tenant          name of owner
        @param      location        location of site
        @retval     protobuf block data
        """

        protobuf_data = rpi_natsio_schema_pb2.MetricSubmission()
        protobuf_data.site_info.tenant = tenant
        protobuf_data.site_info.location = location
        return protobuf_data

    @staticmethod
    def add_new_metrics_group(
        metric_submission: rpi_natsio_schema_pb2.MetricSubmission,
        model: str,
        manufacturer: str,
        serial_number: str,
        driver_version: str,
        device_id: str,
    ) -> rpi_natsio_schema_pb2.MetricGroup:
        """
        @brief      Add new device with info of that device
        @param      metric_submission       protobuf block metric site
        @param      model                   device model
        @param      manufacturer            device manufacturer
        @param      serial_number           device serial number
        @param      driver_version          device version
        @param      device_id               device ID
        @retval     protobuf metric group data
        """

        metrics_group = metric_submission.metric_groups.add()
        metrics_group.timestamp = round(time.time() * 1000)
        metrics_group.device_info.model = model
        metrics_group.device_info.manufacturer = manufacturer
        metrics_group.device_info.serial_number = serial_number
        metrics_group.device_info.driver_version = driver_version
        metrics_group.device_info.device_id = str(device_id)
        return metrics_group

    @staticmethod
    def add_metric_data(
        metric_group: rpi_natsio_schema_pb2.MetricGroup,
        block_data: Tuple[Dict[str, PointContainer], Dict[str, Exception]],
    ) -> None:
        """
        @brief      Add data to protobuf data block
        @param      metric_group        protobuf metric group data
        @param      block_data          block data ready for push to server
        @retval     None
        """

        for readable_value in block_data[0].items():
            data = metric_group.metrics.add()

            data.name = readable_value[0]
            data.unit = readable_value[1].unit
            result = readable_value[1].value

            data_type = ""
            data_type_json = readable_value[1].data_type

            if type(result) is float:
                data_type = "float"
            elif type(result) is str:
                data_type = "str"
            elif data_type_json == "bitfield16" or data_type_json == "bitfield32":
                data_type = data_type_json
            elif data_type_json == "enum16" or data_type_json == "enum32":
                data_type = data_type_json
            elif data_type_json == "int16" or data_type_json == "int32":
                data_type = "int32"
            elif (
                data_type_json == "uint16"
                or data_type_json == "uint32"
                or data_type_json == "acc32"
            ):
                data_type = "uint32"
            elif data_type_json == "int64":
                data_type = "int64"
            elif data_type_json == "uint64" or data_type_json == "acc64":
                data_type = "uint64"

            if data_type == "int32":
                data.int32_value = result
            elif data_type == "uint32":
                data.uint32_value = result
            elif data_type == "int64":
                data.int64_value = result
            elif data_type == "uint64":
                data.uint64_value = result
            elif data_type == "bitfield16":
                data.bitfield16_value = result
            elif data_type == "bitfield32":
                data.bitfield32_value = result
            elif data_type == "enum16":
                data.enum16_value = result
            elif data_type == "enum32":
                data.enum32_value = result
            elif data_type == "float":
                data.float_value = result
            elif data_type == "str":
                data.str_value = result

    @staticmethod
    def compress_data(
        metric_submission: rpi_natsio_schema_pb2.MetricSubmission,
    ) -> bytes:
        """
        @brief      Compress data
        @param      metric_submission        protobuf metric group data
        @retval     block_data as bytes
        """

        return_data = snappy.compress(metric_submission.SerializeToString())
        return return_data

    @staticmethod
    def remove_all_metric_data(
        metric_group: rpi_natsio_schema_pb2.MetricSubmission, no_device: int = 0
    ) -> rpi_natsio_schema_pb2.MetricSubmission:
        """
        @brief      Delete metric data in metric group
        @param      metric_group        protobuf metric group data
        @retval     protobuf block data
        """

        del metric_group.metrics[no_device][:]
        return metric_group
