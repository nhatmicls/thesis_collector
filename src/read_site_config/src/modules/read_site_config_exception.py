# Config Exception

class UnAcceptedValueError(Exception):
    """
        Raise exception if pass value whose data type is not in dict type
    """

    def __init__(self, msg: str):
        self.msg = 'UnAcceptedValueError: ' + msg


class ReadPointsError(Exception):
    """
        Raise exception when read register fails
    """

    def __init__(self, msg: str):
        self.msg = 'ReadPointsError: ' + msg


class UnAcceptedConfigTypeError(Exception):
    """
        Raise exception when pass argument which datatype different form prescribed
        datatype of these property:
        - "read" : str or dict
        - "except" : str or dict
        - "register" : str or list
        - "datatype" : str or list
    """

    def __init__(self, msg: str):
        self.msg = 'UnAcceptedConfigTypeError: ' + msg


class UnRecognizeRegisterNameError(Exception):
    """
        Raise exception if one or the register itself is requested to be read or 
        excluded in the config file that is not in the driver of the respective device
    """

    def __init__(self, msg: str):
        self.msg = 'UnRecognizeRegisterNameError: ' + msg


class UnRecognizeDataTypeError(Exception):
    """
        Raise exception if one or the datatype itself is requested to be read or
        excluded in the config file that is not in the driver of the respective device
    """

    def __init__(self, msg: str):
        self.msg = 'UnRecognizeDataTypeError: ' + msg


class LackConditionError(Exception):
    """
        Raise exception if all of both "read" and "except" condition
    """

    def __init__(self, msg: str):
        self.msg = 'LackConditionError: ' + msg


class DuplicateNameError(Exception):
    """
        Raise exception if in the same model in the config file there are 2 or more
        devices being given the same name
    """

    def __init__(self, msg: str):
        self.msg = 'DuplicateNameError: ' + msg


class InvalidPointError(Exception):
    """
        Raise exception if there is error in config file cause by point error
    """

    def __init__(self, msg: str):
        self.msg = 'InvalidPointError: ' + msg


class InValidPathError(Exception):
    """
        Raise exception if "driver_location" property of config file contain
        invalid directory path
    """

    def __init__(self, msg: str):
        self.msg = 'InValidPathError: ' + msg


class MissingPropertyError(Exception):
    """
        Raise exception if occur missing property in config file
    """

    def __init__(self, msg: str):
        self.msg = 'MissingPropertyError: ' + msg


class MissingDeviceNameError(Exception):
    """
        Raise exception if occur missing device's name in any device of any 
        model in config file
    """

    def __init__(self, msg: str):
        self.msg = 'MissingDeviceNameError: ' + msg


class MissingDevicePropertyError(Exception):
    """
        Raise exception if occur missing device's name in any device of any 
        model in config file
    """

    def __init__(self, msg: str):
        self.msg = 'MissingDevicePropertyError: ' + msg
