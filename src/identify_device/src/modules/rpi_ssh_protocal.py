import paramiko, socket
import struct
import os
import sys

from typing import *
from pathlib import Path

parent_dir_path = str(Path(__file__).resolve().parents[4])
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_verbose import verbose


def ssh_command(hostname: str, username: str, password: str, command: str) -> List[str]:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for _ in range(10):
        try:
            ssh.connect(
                hostname=hostname,
                username=username,
                password=password,
                allow_agent=False,
            )
            break
        except Exception as e:
            verbose("SYSTEM - Scan thread", str(e), "ERROR")

    for _ in range(10):
        try:
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
            break
        except Exception as e:
            verbose("SYSTEM - Scan thread", str(e), "ERROR")

    ssh_stdout.channel.recv_exit_status()
    return_data = ssh_stdout.readlines()
    return return_data
