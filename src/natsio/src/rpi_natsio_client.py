import argparse
import asyncio
import time
import socket
import ssl
import sys
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import FileIO
from pathlib import Path
from typing import *
from urllib import parse

import persistqueue
import psutil
import pykka
import snappy
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrNoServers, ErrTimeout
from rx.core.typing import Disposable
from rx.scheduler.eventloop import AsyncIOScheduler

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/modbuslib/src")
sys.path.append(parent_dir_path + "/src/read_site_config/src")
sys.path.append(parent_dir_path + "/src/natsio/src")
sys.path.append(parent_dir_path + "/src/identify_device/src")
sys.path.append(parent_dir_path + "/src/system/src")
sys.path.append(parent_dir_path + "/src/database/src")
sys.path.append(parent_dir_path + "/src/modbuslib/protobuf")

from rpi_compress_data import CompressData
from rpi_modbus import ModbusDevice, PointContainer
from rpi_queue import clientQueue
from rpi_verbose import verbose
from rpi_watchdog import Watchdog
import natsio_schema_pb2
from rpi_database import thread_error_database

loop_time: int = 15
time_out_rtu: int = 5
_container_name: str = ""


class NatsioSink(pykka.ThreadingActor):
    """
    Actor responsible for pushing information to server via natsio.
    persistqueue.Queue is used to persist data to disk before sending.
    """

    def __init__(
        self, subject: str, queue: persistqueue.Queue, thread_name: str, nc: NATS = None
    ) -> None:
        """
        @param  nc        a NATS client instance
        @param  subject   name of the natsio subject to push data to
        @param  queue     persistent queue, to save data to disk before trying to send
        """
        super().__init__()
        self._nc: NATS = nc
        self._thread_name: str = thread_name
        self._subject: str = subject
        self._loop: AbstractEventLoop = asyncio.get_event_loop()
        self._queue: clientQueue = queue
        self._scheduler: AsyncIOScheduler = AsyncIOScheduler(asyncio.get_event_loop())
        self._disposable: Union[None, Disposable] = None

        self._push()  # try to push any data saved on disk (if there's any) to server

    def submit(self, data: bytes) -> None:
        """
        Only perist to queue when new data is submitted.
        Pushing to server is done independently.
        """

        # now = datetime.now()
        # dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

        # print(dt_string + " -> Put data")
        self._queue.put(data)

    def set_server(self, nc: NATS) -> None:
        """
        @param  nc        a NATS client instance
        """

        self._nc = nc

    def _push(self) -> None:
        """
        Push to server. First, the function will try to push everything in the queue.
        When the queue is empty, it will try again in 1 second.
        When sending fails, it will also try to send again in 1 second.
        """

        def __debug(msg_data: bytes) -> None:
            snappy_msg = snappy.decompress(msg_data)
            data = natsio_schema_pb2.MetricSubmission()
            data.ParseFromString(snappy_msg)
            timestamp = data.metric_groups[0].timestamp
            if round(time.time() * 1000) - timestamp > 900:
                verbose(
                    "QUEUE - " + self._thread_name,
                    "Get old data at timestamp messeage: "
                    + str(data.metric_groups[0].timestamp),
                    "INFO",
                )

        def _entry_point() -> None:
            """
            The starting point of the push sequence.
            """

            # now = datetime.now()
            # dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            self._disposable = None
            if self._queue.qsize() > 0:
                data = self._queue.get()
                if data != None:
                    if len(data) > 0 and self._queue.qsize() > 400:
                        verbose(
                            "QUEUE",
                            "Get data from queue. Remain block data left: "
                            + str(self._queue.qsize()),
                            "INFO",
                        )
                        __debug(data)
                # print(dt_string + " -> Get data " + str(self._queue.qsize()))
                # Try to push data to server
                _try_push(data)
            else:
                # If queue is empty, try again in 1 second
                self._disposable = _do_again(1, lambda: _entry_point())
                # print(dt_string + " -> Try again " + str(self._queue.qsize()))

        def _next(fut: Future, data: bytes) -> None:
            """
            Check if previous attempt succeeded.
            If successful, continue with the next data point.
            Otherwise, retry with the current data point.
            @param fut    a Future containing the result of the previous push
            @param data   data of the previous attempt to send
            """

            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

            if fut.exception() is None:
                self._queue.task_done()

                verbose("NATS - " + self._thread_name, "Send success", "INFO")

                # Start again with new data (if available)
                # Call _do_again instead of calling _entry_point directly to avoid stackoverflow (trampoline)
                self._disposable = _do_again(0, lambda: _entry_point())
                thread_error_database.remove_from_list("NATS", self._thread_name)
            else:
                self._disposable = _do_again(1, lambda: _try_push(data))
                verbose(
                    "NATS - " + self._thread_name,
                    "Send error. Error code: " + str(fut.exception()),
                    "ERROR",
                )
                thread_error_database.add("NATS", self._thread_name)

        def _try_push(data: bytes) -> None:
            """
            Try to push the given data to server.
            @param data    data to be sent
            """
            fut = self._loop.create_task(
                # Wait for acknowledgement from server.
                # For now, we don't care about the content of the message.
                # We only need to know that the message has been sent successfully.
                self._nc.request(self._subject, data, timeout=1)
            )
            fut.add_done_callback(lambda _: _next(fut, data))

        def _do_again(delay: float, f: Callable[[], None]) -> Disposable:
            """
            Convenient helper function. Used to schedule a function after a delay.
            """

            return self._scheduler.schedule_relative(delay, lambda _1, _2: f())

        _entry_point()

    def on_receive(self, message: Any) -> Any:
        try:
            self.set_server(message)
            return "True"
        except:
            return "False"

    def on_stop(self):
        if self._disposable != None:
            self._disposable.dispose()


class ProcessorActor(pykka.ThreadingActor):
    """
    Actor responsible for process data from device to server via protobuf.
    """

    def __init__(
        self,
        sink: NatsioSink,
    ) -> None:
        super().__init__()
        self.sink = sink

    def fileter(
        self, data: Tuple[Dict[str, PointContainer], Dict[str, Exception]]
    ) -> Union[None, Tuple[Dict[str, PointContainer], Dict[str, Exception]]]:
        return_data: Union[None, Tuple[Dict[str, PointContainer], Dict[str, Exception]]]

        if len(data[0]) > 0:
            return_data = data
        else:
            return_data = None

        return return_data

    def submit(
        self,
        metric_submission_init_data: Dict[str, str],
        metric_gr_init_data: Dict[str, Any],
        data_recieve: Tuple[Dict[str, PointContainer], Dict[str, Exception]],
    ):
        data_after_filter = self.fileter(data=data_recieve)
        if data_after_filter == None:
            return

        self._create_new_block(metric_submission_init_data)

        # Create new device group data
        metric_gr = CompressData().add_new_metrics_group(
            self.protobuf_block,
            metric_gr_init_data["model"],
            metric_gr_init_data["manufacturer"],
            metric_gr_init_data["serial_number"],
            metric_gr_init_data["version"],
            metric_gr_init_data["device_id"],
        )

        CompressData().add_metric_data(metric_gr, data_recieve)
        self.sink.submit(CompressData().compress_data(self.protobuf_block))

    def _create_new_block(self, metric_submission_init_data) -> None:
        self.protobuf_block = CompressData().create_new_metric_submission(
            metric_submission_init_data["tenant"],
            metric_submission_init_data["location"],
        )


class Source(pykka.ThreadingActor):
    """Each inverter should have its own actor.
    More experiments needed to see if this is safe when multiple inverters share the same ip address.
    If it's not safe, each actor should be responsible for just one ip address.
    To separate out data reading and data preparation, we should have an extra actor in between source
    and sink:
    Source Actor -> Processing Actor -> Sink Actor,
    where processing actor takes in the data from Source Actor (which comes from modbuslib) and convert it to
    the data defined by natsio schema.
    """

    def __init__(
        self,
        serial_number: str,
        process: ProcessorActor,
        producer: Callable[
            [
                str,
                ModbusDevice,
                Optional[List[str]],
                Optional[List[str]],
                Optional[str],
            ],
            Tuple[Dict[str, PointContainer], Dict[str, Exception]],
        ],
        device: ModbusDevice,
        metric_submission_init_data: Dict[str, Any],
        metric_gr_init_data: Dict[str, Any],
        protocol: str,
        input_registers: List[str] = [],
        holding_registers: List[str] = [],
    ):
        """
        @param process   the ActorProxy of the actor responsible for sending data
        @param producer  function responsible for producing data.
                         For example, in the case of modbus, this is where modbus
                         read can be performed.
        """
        super().__init__()
        scheduler = AsyncIOScheduler(asyncio.get_event_loop())
        self.serial_number = serial_number
        self.metric_submission_init_data = metric_submission_init_data
        self._disposable = scheduler.schedule_periodic(
            loop_time,
            lambda _: process.submit(
                metric_submission_init_data,
                metric_gr_init_data,
                producer(
                    serial_number, device, input_registers, holding_registers, protocol
                ),
            ),
        )

    def on_stop(self):
        verbose(
            "SYSTEM - " + self.metric_submission_init_data["location"],
            "Removing device " + self.serial_number,
            "INFO",
        )
        try:
            self._disposable.dispose()
            verbose(
                "SYSTEM - " + self.metric_submission_init_data["location"],
                "Remove completed",
                "INFO",
            )
        except:
            verbose(
                "SYSTEM - " + self.metric_submission_init_data["location"],
                "Error while remove device " + self.serial_number,
                "INFO",
            )
