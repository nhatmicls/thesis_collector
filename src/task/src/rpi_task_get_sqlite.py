import asyncio
import threading
import sys
import os

from pathlib import Path
from typing import *

parent_dir_path = str(Path(__file__).resolve().parents[3])
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_system import get_sqlite_data

event_loop_read_db = asyncio.new_event_loop()


def __read_scan_database(db_path: str, db_name: str):
    data = get_sqlite_data(db_path, db_name)


async def thread_read_db(db_path: str, db_name: str):
    thread_name = "Read DB thread"

    asyncio.set_event_loop(event_loop_read_db)
    event_loop_read_db.create_task(
        __read_scan_database(
            db_path=db_path,
            db_name=db_name,
        )
    )

    event_loop_read_db.run_forever()
