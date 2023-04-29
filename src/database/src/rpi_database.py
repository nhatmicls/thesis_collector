import sys
from pathlib import Path
from typing import *

parent_dir_path = str(Path(__file__).resolve().parents[3])

sys.path.append(parent_dir_path + "/src/database/src/modules")

from rpi_actor_database import ActorDatabase, ActorErrorDatabase
from rpi_device_database import DeviceDatabase
from rpi_thread_database import ThreadManager, ThreadErrorDatabase

"""
Database of device
"""

CONFIG_FILE_NAME = "system_config_preset.json"
MAPPING_FILE_NAME = "system_mapping_preset.json"

actor_error_database = ActorErrorDatabase()
actor_database = ActorDatabase()
device_database = DeviceDatabase()
thread_database = ThreadManager()
thread_error_database = ThreadErrorDatabase()
