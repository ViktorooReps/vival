import os
from enum import Enum
from typing import Optional


class Lang(Enum):
    C = 'C'
    CPP = 'C++'
    Python = 'Python'


class Extension(Enum):
    C = '.c'
    CPP = '.cpp'
    OBJ = '.o'
    PY = '.py'


def detect_lang(executable_path: os.PathLike) -> Optional[Lang]:
    exec_str = str(executable_path)

    if exec_str.endswith(Extension.C.value):
        return Lang.C

    if exec_str.endswith(Extension.CPP.value):
        return Lang.CPP

    if exec_str.endswith(Extension.PY.value):
        return Lang.Python

    return None
