"""
Exception raised
"""


class FileNotFound(Exception):
    """
    Exception raised when no config file available
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Can not get any device in config file"
