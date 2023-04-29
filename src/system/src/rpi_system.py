import os, glob, shutil, psutil
import typing
import docker
import sqlite3

from typing import *


def get_sqlite_data(db_path: str, db_name: str) -> List[str]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    res = cur.execute("SELECT * FROM " + db_name)
    return res.fetchall()


def remove_queue() -> None:
    path_queue = "/pecom/rpi-playground/queue_store"
    _glob_path = path_queue + "/*"
    paths = glob.glob(_glob_path)

    for path in paths:
        shutil.rmtree(path)


def kill_process(container_name: str):
    docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    docker_client.containers.get(container_name).restart()
