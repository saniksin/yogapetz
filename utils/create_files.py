import os
import json
from typing import Union

from data.config import IMPORTANT_FILES, DB


def join_path(path: Union[str, tuple, list]) -> str:
    if isinstance(path, str):
        return path

    return os.path.join(*path)


def touch(path: Union[str, tuple, list], file: bool = False) -> bool:
    path = join_path(path)
    if file:
        if not os.path.exists(path):
            with open(path, 'w') as f:
                if path == DB:
                    db = {}
                    f.write(json.dumps(db))
                else:
                    f.write('')  

            return True

        return False

    if not os.path.isdir(path):
        os.mkdir(path)
        return True

    return False


def create_files():
    for file in IMPORTANT_FILES:
        touch(path=file, file=True)