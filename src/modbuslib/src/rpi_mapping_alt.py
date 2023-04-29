import asyncio
import threading
import sys
import os
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import FileIO
from pathlib import Path
from typing import *
from urllib import parse
import sqlite3


class MappingAlt:
    def __init__(
        self,
        mapping_key_data_database_path: str,
        mapping_error_value_data_database_path: str,
    ) -> None:

        self.defaul_command = {
            "search": "SELECT * FROM MappingScheme WHERE yyyy='xxxx'",
        }

        self.mapping_key_data = ""
        self.mapping_error_value_data = ""
        self.mapping_key_data_database = sqlite3.connect(mapping_key_data_database_path)
        self.mapping_error_value_data_database = sqlite3.connect(
            mapping_error_value_data_database_path
        )

    def mapping_key(self, key: str) -> str:
        replace_command = self.defaul_command["search"].replace("xxxx", key)
        replace_command = replace_command.replace("yyyy", "key")
        cur = self.mapping_key_data_database.cursor()
        replace_database = cur.execute(replace_command)
        data = replace_database.fetchall()
        return data

    def mapping_error_value(self, key: str, device_name: str) -> int:
        replace_command = self.defaul_command["search"].replace("xxxx", key)
        replace_command = replace_command.replace("yyyy", "Error_name")
        cur = self.mapping_key_data_database.cursor()
        replace_database = cur.execute(replace_command)
        data = replace_database.fetchall()
        return data
