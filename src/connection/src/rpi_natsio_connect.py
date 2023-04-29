import asyncio
import ssl
import sys

from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrNoServers, ErrTimeout

from pathlib import Path

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_verbose import verbose


# Connect NATS server
async def init_natsio(
    server: str,
    time_out: int = 10,
    user_credentials_path: str = "",
    cert_file_path: str = "",
    key_file_path: str = "",
    rootCA_file_path: str = "",
    thread_name: str = "",
    tls: bool = False,
) -> NATS:
    loop = asyncio.get_event_loop()
    nc = NATS()

    async def error_cb(e: Exception):
        verbose("NATS " + thread_name, str(e), "ERROR")

    async def disconnect_cb():
        verbose("NATS " + thread_name, "Disconnected", "INFO")

    async def closed_cb():
        verbose("NATS " + thread_name, "Closed", "INFO")

    async def discovered_server_cb():
        verbose("NATS " + thread_name, "Discovered", "INFO")

    async def reconnected_cb():
        verbose("NATS " + thread_name, "Reconnected", "INFO")

    try:
        if tls == True:
            ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_verify_locations(rootCA_file_path)
            ssl_ctx.load_cert_chain(
                certfile=cert_file_path,
                keyfile=key_file_path,
            )

            await nc.connect(
                server,
                tls=ssl_ctx,
                user_credentials=user_credentials_path,
                loop=loop,
                ping_interval=20,
                max_outstanding_pings=10,
                connect_timeout=time_out,
                reconnect_time_wait=2,
                allow_reconnect=True,
                max_reconnect_attempts=3,
                verbose=True,
                error_cb=error_cb,
                disconnected_cb=disconnect_cb,
                closed_cb=closed_cb,
                discovered_server_cb=discovered_server_cb,
                reconnected_cb=reconnected_cb,
            )
        else:
            await nc.connect(
                server,
                user_credentials=user_credentials_path,
                loop=loop,
                ping_interval=20,
                max_outstanding_pings=10,
                connect_timeout=time_out,
                reconnect_time_wait=2,
                allow_reconnect=True,
                max_reconnect_attempts=3,
                verbose=True,
                error_cb=error_cb,
                disconnected_cb=disconnect_cb,
                closed_cb=closed_cb,
                discovered_server_cb=discovered_server_cb,
                reconnected_cb=reconnected_cb,
            )
    except ErrNoServers as e:
        verbose("NATSIO - " + thread_name, str(e), "ERROR")
    except Exception as e:
        verbose("NATSIO - " + thread_name, str(e), "ERROR")
    return nc
