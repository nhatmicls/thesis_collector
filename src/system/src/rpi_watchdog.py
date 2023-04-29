from threading import Timer
import rpi_system
import typing

from rpi_verbose import verbose


class Watchdog(Exception):
    def __init__(self, timeout=10, userHandler=None):  # timeout in seconds
        self.timeout = timeout
        self.handler = userHandler if userHandler is not None else self.defaultHandler
        self.timer = Timer(self.timeout, self.handler)

    def start(self):
        if self.timer.is_alive() == False:
            self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.timer = Timer(self.timeout, self.handler)
        self.timer.start()

    def stop(self):
        self.timer.cancel()

    def defaultHandler(self):
        verbose("WATCHDOG", "Time up", "INFO")
