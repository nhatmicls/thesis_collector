import sys
import threading
from typing import *
from pathlib import Path

parent_dir_path = str(Path(__file__).resolve().parents[4])
sys.path.append(parent_dir_path + "/src/system/src")

from rpi_verbose import verbose


class ThreadErrorDatabase:
    def __init__(self) -> None:
        self.error_list: Dict[str, int] = {}

    def add(self, type_error: str, thread_name: str) -> None:
        """add counter error of thread

        Args:
            type_error (str): type error
            thread_name (str): thread name need to take care
        """

        if thread_name in self.error_list:
            if type_error in self.error_list[thread_name]:
                error_count = self.error_list[thread_name][type_error]
            else:
                error_count = 0
        else:
            error_count = 0
        error_count += 1
        self.error_list.update({thread_name: {type_error: error_count}})
        # print(self.error_list)

    def get_list(self) -> dict:
        """get_list return list of error thread

        Returns:
            dict: Name and number error time
        """
        return self.error_list

    def remove_from_list(self, type_error: str, thread_name: str) -> None:
        if thread_name in self.error_list:
            if type_error in self.error_list[thread_name]:
                self.error_list[thread_name].pop(type_error)
        else:
            # verbose(
            #     "DATABASE",
            #     "Not have " + thread_name + " in Thread Error Database",
            #     "ERROR",
            # )
            pass


class ThreadManager:
    def __init__(self) -> None:
        self.threads: Dict[str, threading.Thread] = {}

    def add(
        self,
        thread_name: str,
        thread_function: Callable[[Any], Any],
        thread_init_data: Dict[str, Any],
    ) -> None:
        thread = threading.Thread(
            target=thread_function,
            daemon=True,
            args=(thread_init_data,),
        )
        thread.start()
        self.threads.update({thread_name: thread})

    def join(self):
        for t in [self.threads[x] for x in (self.threads.keys())]:
            t.join()
