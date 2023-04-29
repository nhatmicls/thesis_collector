"""
Exception raised
"""


class UnimplementedRegister(Exception):
    """
    Exception raised when calling a unimplement register
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{self.args[0]} is unimplement register"


class UnknownDataType(Exception):
    """
    Exception raised when calling a unimplement register
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Unknown this data type {self.args[0]}(type '{self.args[1]}')"


class WrongInput(Exception):
    """
    Exception raised when input wrong
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{self.args[0]}() wrong input argument '{self.args[1]}' be '{self.args[2]}'"


class MissingInput(Exception):
    """
    Exception raised when register device same ID with registered device
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{self.args[0]}() missing 1 required positional argument: '{self.args[1]}' "


class ClientIDAlreadyInitialized(Exception):
    """
    Exception raised when register device same ID with registered device
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Client {self.args[0]} already initialize"


class ClientIDNotFound(Exception):
    """
    Exception raised when register device same ID with registered device
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Client {self.args[0]} not initialize or already deleted"
