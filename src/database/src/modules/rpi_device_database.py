import sys
from pathlib import Path
from typing import *

parent_dir_path = str(Path(__file__).resolve().parents[4])


class DeviceDatabase:
    def __init__(self) -> None:
        self.doctrine_device: Dict[str, Any] = {}
        self.old_doctrine_device: Dict[str, Any] = {}
        self.known_device: Dict[str, Any] = {}
        self.new_device: Dict[str, Any] = {}
        self.modifine_state = False

    def add_doctrine_device(self, site_data: Dict[str, Any]) -> None:
        """
        Add doctrine device
        """

        self.old_doctrine_device = self.doctrine_device
        self.doctrine_device.update(site_data)
        if self.old_doctrine_device != self.doctrine_device:
            self.modifine_state = True

    def add_new_device(self, site_data: Dict[str, Any]) -> None:
        """
        Add new device
        """

        site_data = site_data["mapping_SN_IP"]
        self.new_device.update(site_data)

    def accept(self, SN: str) -> None:
        """
        Add device to actor and remove from queue list
        """

        self.known_device.update({SN: self.new_device[SN]})
        self.new_device.pop(SN)

    def reject(self, SN: str) -> None:
        """
        Not add device to actor and remove from queue list
        """

        self.new_device.pop(SN)

    def remove_known_device(self, SN: str) -> None:
        """
        Remove device from list actor
        """

        self.known_device.pop(SN)

    def remove_doctrine_device(self, SN: str) -> None:
        """
        Remove device from doctrine
        """

        self.doctrine_device.pop(SN)

    def confirm_modify(self) -> None:
        """
        Confirm change device
        """

        self.modifine_state = False

    def get_doctrine_device(self) -> Dict[str, Any]:
        return self.doctrine_device

    def get_known_device(self) -> Dict[str, Any]:
        return self.known_device

    def get_new_device(self) -> Dict[str, Any]:
        return self.new_device

    def len_theory_device(self) -> int:
        return len(self.doctrine_device)

    def len_known_device(self) -> int:
        return len(self.known_device)

    def len_new_device(self) -> int:
        return len(self.known_device)
