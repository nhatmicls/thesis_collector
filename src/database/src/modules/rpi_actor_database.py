import pykka
import sys

from pathlib import Path
from typing import *

parent_dir_path = str(Path(__file__).resolve().parents[4])
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_verbose import verbose


class ActorErrorDatabase:
    def __init__(self) -> None:
        self.actor_list: Dict[str, int] = {}

    def add(self, SN: str) -> None:
        """add counter up error per device

        Args:
            SN (str): device serial number
        """
        if SN in self.actor_list:
            error_count = self.actor_list[SN]
        else:
            error_count = 0
        error_count += 1
        self.actor_list.update({SN: error_count})

    def get_list(self) -> dict:
        """get_list return list of error device

        Returns:
            dict: Name and number error time
        """
        return self.actor_list

    def remove_from_list(self, SN: str) -> None:
        if SN in self.actor_list:
            self.actor_list.pop(SN)
        else:
            verbose("DATABASE", "Not have " + SN + " in Actor Error Database", "ERROR")


class ActorDatabase:
    def __init__(
        self,
    ) -> None:
        self.actor_list: Dict[str, pykka.ThreadingActor] = {}

    def add(
        self,
        serial_number: str,
        source: pykka.ThreadingActor,
    ) -> None:
        """
        Create and run actor
        """

        self.actor_list.update({serial_number: source})

    def remove_actor(self, SN: str) -> None:
        """
        Stop and remove actor
        """

        if SN in self.actor_list:
            _ = self.actor_list[SN].actor_ref.stop(True, timeout=100)
            self.actor_list.pop(SN)
        else:
            verbose("DATABASE", "Not have " + SN + " in Actor Database", "ERROR")

    def list(self) -> Dict[str, Any]:
        """
        Return actor list
        """

        return self.actor_list
