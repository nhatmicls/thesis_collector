# Support IO file

import json
from typing import *


def json2dict(direct_path: str) -> Dict[str, Any]:
    """
    @brief: read "json" format file
    @param:
            direct_path: file directory
    @retval:
            data:        dict data
    """

    with open(direct_path) as json_file:
        data = json.load(json_file)

    json_file.close()

    return data


def dict2json(direct_path: str, data: Dict[str, Any]) -> None:
    """
    @brief: export dictionary tyoe data to json file
    @param:
            direct_path: file directory will be exported
    """

    with open(direct_path, "w+", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    f.close()
