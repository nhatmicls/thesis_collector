import time

LOG_STATE = 0
_NATS_INFO_LOG_REDUCE_INFO = 500
_ERROR_LOGS_REDUCE = 50

_verbose_count_info = _NATS_INFO_LOG_REDUCE_INFO - 3
_verbose_count_error = _ERROR_LOGS_REDUCE - 3


def verbose(
    data_from: str,
    string_send: str,
    type_verbose: str,
):
    """verbose function to print logs to terminal

    Args:
        data_from (str): Logs from
        type_verbose (str): Level logs
        string_send (str): Logs info
    """
    global _verbose_count_info, _verbose_count_error

    dt_string = time.strftime("%d/%m/%Y %H:%M:%S")
    time_now = int(time.strftime("%H")) + 7

    if type_verbose == "INFO":
        if "NATS" in data_from and "Send success" in string_send:
            _verbose_count_info += 1
            if _verbose_count_info > _NATS_INFO_LOG_REDUCE_INFO:
                _verbose_count_info = 0
            else:
                return
    elif type_verbose == "ERROR":
        if time_now < 7 or time_now > 17:
            _verbose_count_error += 1
            if _verbose_count_error > _ERROR_LOGS_REDUCE:
                _verbose_count_error = 0
            else:
                return

    print(
        "["
        + data_from
        + "] "
        + dt_string
        + " ["
        + type_verbose
        + "] "
        + str(string_send)
    )
