from enum import Enum
from pathlib import Path
from subprocess import CalledProcessError
import subprocess

from distutils.ccompiler import new_compiler

import os
from typing import Dict, Any, List, Optional

from tester.lang import Lang, Extension


class CompilerName(Enum):
    GCC = 'gcc'
    GPP = 'g++'


class Compiler:
    """Compiles supported languages to executable code"""

    _lang2compiler: Dict[Lang, CompilerName] = {Lang.C: CompilerName.GCC, Lang.CPP: CompilerName.GPP}

    def __init__(self, lang: Lang = Lang.CPP, temp_dir: os.PathLike = None, flags: str = None):
        if flags is None:
            flags = ''

        self.flags = flags.split(' ') if flags != '' else []
        self.default_lang = lang
        self.guessed_lang = self.default_lang
        self.temp_dir = temp_dir
        self.compile_details: Dict[str, Any] = {
            'error_message': None
        }

        self._build_mappings()

    def _build_mappings(self):
        self._ext2lang: Dict[Extension, Lang] = {Extension.C: Lang.C, Extension.CPP: Lang.CPP}
        self._lang2ext: Dict[Lang, Extension] = {lang: ext for ext, lang in self._ext2lang.items()}
        self._ext2lang[Extension.OBJ] = self.default_lang

    def set_language(self, src_file: os.PathLike) -> None:
        """Changes self.guessed_lang according to file's extension"""
        src_str = str(src_file)
        for ext, lang in self._ext2lang.items():
            if src_str.endswith(ext.value):
                self.guessed_lang = lang
                return

        self.guessed_lang = self.default_lang

    def get_tempdir(self) -> os.PathLike:
        """Returns directory to use as temporary storage"""
        if self.temp_dir is not None:
            tempdir_path = self.temp_dir
        else:
            tempdir_path = os.path.dirname(os.path.realpath(__file__))

        return os.path.abspath(tempdir_path)

    def compile(self, src_file: os.PathLike, main: Optional[str] = None) -> Optional[os.PathLike]:
        """Compiles source file to executable"""
        self.set_language(src_file)
        tempdir_path = self.get_tempdir()
        exec_file: os.PathLike = Path(new_compiler().executable_filename(os.path.join(tempdir_path, "res")))

        args: List[str] = [self._lang2compiler[self.guessed_lang].value] + self.flags
        if main is not None:
            main_src: os.PathLike = Path(os.path.join(tempdir_path, 'main' + self._lang2ext[self.guessed_lang].value))
            with open(main_src, 'w') as main_file:
                main_file.write(main)
            args += [str(main_src)]
        try:
            subprocess.run(args + [str(src_file), '-o', str(exec_file)], check=True)
        except CalledProcessError:
            self.compile_details['error_message'] = 'Failed to compile source file. ' \
                                                    'Make sure you have C/C++ compiler installed.'
            return None

        return os.path.abspath(exec_file)
