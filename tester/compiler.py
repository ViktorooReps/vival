from subprocess import STDOUT, PIPE, CalledProcessError
from collections.abc import Iterable
import subprocess

from distutils.ccompiler import new_compiler

import os

class Compiler:
    """Compiles supported languages to executable code"""

    supported_extentions = [".c", ".cpp", ".o"]
    compiler = {
        "C": "gcc",
        "C++": "g++"
    }

    def __init__(self, lang="C++", tmp_dir=None, flags=None):
        if flags == None:
            self.flags = []
        else:
            self.flags = flags.split(" ")

        self.guess_lang = lang
        self.tmp_dir = tmp_dir
        self.compile_details = {
            "error_message": None
        }

    def get_language(self, src_file):
        """Changes self.guess_lang according to file's extension"""
        if src_file.endswith(".c"):
            self.guess_lang = "C"

        if src_file.endswith(".cpp"):
            self.guess_lang = "C++"

    def get_tmpdir(self):
        """Returns directory to use as temporary storage"""
        if self.tmp_dir != None:
            tmpdir_path = self.tmp_dir
        else:
            tmpdir_path = os.path.dirname(os.path.realpath(__file__))

        return os.path.abspath(tmpdir_path)

    def plant_main(self, parser, exec_path):
        """Compiles given C/C++ code with new entry point. Returns new executable path"""

        compiler = new_compiler()

        self.get_language(exec_path)
        tmpdir_path = self.get_tmpdir()

        # create main{.c/.cpp} in tmpdir

        if self.guess_lang == "C++":
            main_src = os.path.join(tmpdir_path, "main.cpp")
        
        if self.guess_lang == "C":
            main_src = os.path.join(tmpdir_path, "main.c")

        main_obj = os.path.join(tmpdir_path, "main.o")
        exec_obj = os.path.join(tmpdir_path, "exec.o")

        res_path = compiler.executable_filename(os.path.join(tmpdir_path, "res"))

        with open(main_src, "w") as main_file:
            main_file.write(parser.get_main())

        # compile source files
        try:
            args = [self.compiler[self.guess_lang]] + self.flags
            subprocess.run(args + [ "-c", main_src, "-o", main_obj], check=True)
            subprocess.run(args + ["-c", exec_path, "-o", exec_obj], check=True)
        except CalledProcessError as err:
            self.compile_details["error_message"] = "Failed to compile source files. Make sure you have C/C++ compiler installed."
            return None

        # link object files
        try:
            subprocess.run([self.compiler[self.guess_lang], main_obj, exec_obj, "-o", res_path], check=True)
        except CalledProcessError as err:
            self.compile_details["error_message"] = "Failed to link object files."
            return None

        return os.path.abspath(res_path)

    def compile(self, src_file):
        """Compiles source file to executable"""
        self.get_language(src_file)
        tmpdir_path = self.get_tmpdir()
        exec_file = new_compiler().executable_filename(os.path.join(tmpdir_path, "res"))

        try:
            args = [self.compiler[self.guess_lang]] + self.flags
            subprocess.run(args + [src_file, "-o", exec_file], check=True)
        except CalledProcessError as err:
            self.compile_details["error_message"] = "Failed to compile source file. Make sure you have C/C++ compiler installed."
            return None

        return os.path.abspath(exec_file)