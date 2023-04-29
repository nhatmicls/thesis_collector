import argparse
import sys
import os
from pathlib import Path
from typing import *

parent_dir_path = str(Path(__file__).resolve().parents[0])
sys.path.append(parent_dir_path + "/src/task/src")

from rpi_task import thread_base


def prepare_args(args=None) -> None:
    if args.default_config != None:
        default_config_file_direct = args.default_config
    elif os.getenv("DefaultConfigFolderPath") != None:
        default_config_file_direct = os.getenv("DefaultConfigFolderPath")
    else:
        raise

    if args.config_driver != None:
        config_folder_path = args.config_driver
    elif os.getenv("ConfigFolderPath") != None:
        config_folder_path = os.getenv("ConfigFolderPath")
    else:
        raise

    if args.creds != None:
        user_credentials_path = args.creds
    elif os.getenv("UserCredentialsPath") != None:
        user_credentials_path = os.getenv("UserCredentialsPath")
    else:
        raise

    if args.client_cert != None:
        cert_file_path = args.client_cert
    elif os.getenv("CertFilePath") != None:
        cert_file_path = os.getenv("CertFilePath")
    else:
        raise

    if args.client_key != None:
        key_file_path = args.client_key
    elif os.getenv("KeyFilePath") != None:
        key_file_path = os.getenv("KeyFilePath")
    else:
        raise

    if args.rootCA_cert != None:
        rootCA_file_path = args.rootCA_cert
    elif os.getenv("RootCaFilePath") != None:
        rootCA_file_path = os.getenv("RootCaFilePath")
    else:
        raise

    container_name = os.getenv("ContainerName")

    thread_base(
        default_config_file_direct=default_config_file_direct,
        site_config_folder_direct=config_folder_path,
        user_credentials_path=user_credentials_path,
        cert_file_path=cert_file_path,
        key_file_path=key_file_path,
        rootCA_file_path=rootCA_file_path,
    )


def main():
    parser = argparse.ArgumentParser(
        description="This program will get data from device using modbus protocol.",
        prog="RPI PECOM",
    )

    parser.add_argument(
        "--default-config",
        help="Destination of default config file",
        type=str,
    )

    parser.add_argument(
        "--config-driver",
        help="Destination of config file",
        type=str,
    )
    parser.add_argument(
        "--creds",
        help="Destination of creds file",
        type=str,
    )
    parser.add_argument(
        "--client-cert",
        help="Destination of client cert file",
        type=str,
    )
    parser.add_argument(
        "--client-key",
        help="Destination of client key file",
        type=str,
    )
    parser.add_argument(
        "--rootCA-cert",
        help="Destination of root CA cert file",
        type=str,
    )

    args = parser.parse_args()

    prepare_args(args)


if __name__ == "__main__":
    main()
