import os
import json
from typing import Union

from data.config import IMPORTANT_FILES, DB, DB_DIR


def join_path(path: Union[str, tuple, list]) -> str:
    if isinstance(path, str):
        return path

    return os.path.join(*path)


def touch(path: Union[str, tuple, list], file: bool = False) -> bool:
    path = join_path(path)
    if file:
        if not os.path.exists(path):
            # Создаем все промежуточные каталоги
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                if path == DB:
                    db = {}
                    f.write(json.dumps(db))
                else:
                    f.write('')
            return True
        else:
            return False
    else:
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            return True
        else:
            return False



def create_files():
    touch(DB_DIR)
    for file in IMPORTANT_FILES:
        touch(path=file, file=True)