"""
Exception raised
"""


class DeviceNotSupported(Exception):
    """
    Exception raised when calling a unimplement register
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{self.args[0]} is not support"
