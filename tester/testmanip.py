# distutils: language = c++

from subprocess import STDOUT, PIPE, CalledProcessError
import subprocess

from distutils.ccompiler import new_compiler

import os

def scan(text, tags):
    """Scans given text for every tag from tags. Returns map tag->[positions]"""
    res = {}
    for tag in tags:
        res[tag] = []

        stpos = text.find(tag)
        while (stpos != -1):
            res[tag].append(stpos)

            stpos += len(tag)
            stpos = text.find(tag, stpos)
    
    return res

class Test:
    """Single extracted test"""

    def __init__(self, title="Unnamed Test"):
        self.stdin = []
        self.stdout = []
        self.cmd = []
        self.comment = [title]
        self.startup = []
        self.cleanup = []

        self.type = "unfilled"

        self.cmd_join_symbol = " "
        self.stdin_join_symbol = "\n"
        self.stdout_join_symbol = "\n"
        self.comment_join_symbol = "\n"
        self.startup_join_symbol = "\n"
        self.cleanup_join_symbol = "\n"

        self.prog_output = None
        self.failed = None

    def run(self, exec_path):
        """Runs executable on this test. Returns True if run succeded"""
        all_args = [exec_path]
        joined_cmd = self.cmd_join_symbol.join(self.cmd)
        joined_stdin = self.stdin_join_symbol.join(self.stdin)
        joined_stdout = self.stdout_join_symbol.join(self.stdout)
        joined_startup = self.startup_join_symbol.join(self.startup)
        joined_cleanup = self.cleanup_join_symbol.join(self.cleanup)

        exec_path = os.path.abspath(exec_path)

        for arg in joined_cmd.split(" "):
            if arg != "":
                all_args.append(arg)

        for args in joined_startup.split("\n"):
            if args != "":
                code = os.waitstatus_to_exitcode(os.system(args))
                if code != 0:
                    self.prog_output = "The program was not executed due to errors during environment preparation stage. Failed to execute: " + args
                    self.failed = True
                    return not self.failed

        prog_output = subprocess.run(all_args, 
                                    stderr=subprocess.STDOUT, 
                                    stdout=PIPE,
                                    input=joined_stdin, 
                                    encoding='ascii').stdout
        
        self.prog_output = prog_output

        for args in joined_cleanup.split("\n"):
            if args != "":
                code = os.waitstatus_to_exitcode(os.system(args))
                if code != 0:
                    self.prog_output = "The program was not executed due to errors during environment preparation stage. Failed to execute: " + args
                    self.failed = True
                    return not self.failed

        if self.type == "filled":
            self.failed = (prog_output != joined_stdout)
            return not self.failed
        else:
            self.failed = False
            return not self.failed
    
    def fill(self):
        """Fills in test using last run"""
        self.type = "filled"
        self.stdout = [self.prog_output]

    def print_last_run(self):
        """Prints details on last run"""
        print("-" * 30)
        
        joined_comment = self.comment_join_symbol.join(self.comment)
        print(joined_comment)

        if len(self.startup) > 0:
            print("\nENVIRONMENT PREPARATION:")
            joined_startup = self.startup_join_symbol.join(self.startup)
            print(joined_startup)

        if len(self.cmd) > 0:
            print("\nCOMMAND LINE ARGUMENTS")
            joined_cmd = self.cmd_join_symbol.join(self.cmd)
            print(joined_cmd)

        if len(self.stdin) > 0:
            print("\nINPUT:")
            joined_stdin = self.stdin_join_symbol.join(self.stdin)
            print(joined_stdin)

        print("\nEXPECTED OUTPUT:")
        joined_stdout = self.stdout_join_symbol.join(self.stdout)
        print(joined_stdout)

        print("\nPROGRAM OUTPUT:")
        print(self.prog_output)

        print("-" * 30)

    def __str__(self):
        title = self.comment[0]
        if len(self.comment) > 1:
            comment = self.comment_join_symbol.join(self.comment[1:])
        else:
            comment = "No comment was provided."
        
        joined_stdin = self.stdin_join_symbol.join(self.stdin)
        joined_stdout = self.stdout_join_symbol.join(self.stdout)
        joined_cmd = self.cmd_join_symbol.join(self.cmd)
        joined_startup = self.startup_join_symbol.join(self.startup)
        joined_cleanup = self.cleanup_join_symbol.join(self.cleanup)

        str_repr = ""

        if self.type == "filled":
            str_repr += title + "\n\n"

        if self.type == "unfilled":
            str_repr += title + " (unfilled)\n\n"

        str_repr += "COMMENT\n"
        str_repr += "/{" + comment + "}/\n\n"

        if len(self.startup) > 0:
            str_repr += "STARTUP\n"
            str_repr += "/{" + joined_startup + "}/\n\n"

        if len(self.cleanup) > 0:
            str_repr += "CLEANUP\n"
            str_repr += "/{" + joined_cleanup + "}/\n\n"

        if len(self.cmd) > 0:
            str_repr += "CMD\n"
            str_repr += "/{" + joined_cmd + "}/\n\n"

        if len(self.stdin) > 0:
            str_repr += "INPUT\n"
            str_repr += "/{" + joined_stdin + "}/\n\n"

        if len(self.stdout) > 0:
            str_repr += "OUTPUT\n"
            str_repr += "/{" + joined_stdout + "}/\n\n"
        
        return str_repr

    def tag_with(self, tag, contents):
        if tag == "INPUT":
            self.stdin.append(contents)

        if tag == "OUTPUT":
            self.stdout.append(contents)
            self.type = "filled"

        if tag == "CMD":
            self.cmd.append(contents)

        if tag == "COMMENT":
            self.comment.append(contents)

        if tag == "STARTUP":
            self.startup.append(contents)

        if tag == "CLEANUP":
            self.cleanup.append(contents)


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
            main_file.write(parser.main_text)

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
            

class TestsParser:
    """Parses text file with tests"""

    id_tags = {
        "INPUT", 
        "OUTPUT", 
        "MAIN", 
        "CMD", 
        "COMMENT", 
        "DESCRIPTION",
        "FLAGS",
        "STARTUP",
        "CLEANUP"
    }
    global_tags = {
        "MAIN", 
        "DESCRIPTION",
        "FLAGS"
    }

    def __init__(self, parse_format="new", expected_tests="filled"): 
        self.description = None
        self.main_text = None
        self.compiler_flags = None
        self.format = parse_format
        self.expected_tests = expected_tests
        self.parse_details = {
            "ntests": 0,
            "format": None,
            "error_message": None,
            "warning_messages": [],
        }
    
    def tag_globally(self, tag, contents):
        if tag == "DESCRIPTION":
            self.description = contents

        if tag == "MAIN":
            self.main_text = contents

        if tag == "FLAGS":
            self.compiler_flags = contents

    def parse(self, tests_file):
        """Parses tests_file and returns list of Test objects. Returns None in case of an error"""
        self.parse_details["ntests"] = 0
        tests = []

        text = tests_file.read()

        brackets = scan(text, ["/{", "}/"])

        if len(brackets["/{"]) != len(brackets["}/"]):
            self.parse_details["error_message"] = "Wrong format! Unmatched number of /{ and }/ brackets.\n"
            return None

        if len(brackets["/{"]) == 0 or self.format == "old":
            if self.format == "new":
                self.parse_details["warning_messages"].append("Old format detected!\n")

            # parse tests according to old format

            if self.expected_tests == "unfilled":
                contents = list(text.split("[INPUT]\n"))[1:]
                for content in contents:
                    curr_test = Test( "Test " + str(self.parse_details["ntests"] + 1) )

                    if "{CMD}\n" in content:
                        cmd, inp = content.split("{CMD}\n")

                        curr_test.tag_with("CMD", cmd)
                    else:
                        inp = content

                    curr_test.tag_with("INPUT", inp)

                    tests.append(curr_test)
                    self.parse_details["ntests"] += 1
            
            if self.expected_tests == "filled":
                contents = list(text.split("[INPUT]\n"))[1:]
                for content in contents:
                    curr_test = Test( "Test " + str(self.parse_details["ntests"] + 1) )

                    content, outp = content.split("[OUTPUT]\n")

                    if "{CMD}\n" in content:
                        cmd, inp = content.split("{CMD}\n")

                        curr_test.tag_with("CMD", cmd)
                    else:
                        inp = content

                    curr_test.tag_with("INPUT", inp)
                    curr_test.tag_with("OUTPUT", outp)

                    tests.append(curr_test)
                    self.parse_details["ntests"] += 1
                    
            return tests

        # parse tests according to new format

        curr_test = Test( "Test " + str(self.parse_details["ntests"] + 1) )
        filled_fields = set()
        prev_tag = "DESCRIPTION"

        section_start = 0
        for lbracket_ind, rbracket_ind in zip(brackets["/{"], brackets["}/"]):
            contents = text[lbracket_ind + len("/{") : rbracket_ind]
            
            wild_space = text[section_start : lbracket_ind]

            # search for id tag in wild space
            search_results = scan(wild_space, self.id_tags)
            
            best_tag = None
            max_pos = -1
            for tag in search_results:
                if len(search_results[tag]) != 0:
                    curr_max = max(search_results[tag])
                    if curr_max > max_pos:
                        best_tag = tag

                    max_pos = max(curr_max, max_pos)

            if best_tag == None:
                # no tag was found in wild space
                if prev_tag in self.global_tags:
                    self.tag_globally(prev_tag, contents) 
                else:
                    curr_test.tag_with(prev_tag, contents)
            else:
                if best_tag in filled_fields:
                    # new test has started
                    tests.append(curr_test)

                    self.parse_details["ntests"] += 1
                    curr_test = Test( "Test " + str(self.parse_details["ntests"] + 1) )
                    filled_fields = {best_tag}

                    curr_test.tag_with(best_tag, contents)
                else:
                    # continue filling in current test
                    if best_tag in self.global_tags:
                        self.tag_globally(best_tag, contents)
                    else:
                        filled_fields.add(best_tag)
                        curr_test.tag_with(best_tag, contents)
                
                prev_tag = best_tag

            section_start = rbracket_ind + len("}/")

        tests.append(curr_test)
        self.parse_details["ntests"] += 1
    
        return tests

    def write_tests(self, tests, output_filename):
        """Writes contents of tests and parser to output_filename"""
        with open(output_filename, "w") as tsts_file:
            line_len = 70

            tsts_file.write("Contents of this file were automatically generated by VIVAL tool.\n\n")
            tsts_file.write("Install with pip: pip install vival\n")
            tsts_file.write("Visit GitHub for more info: https://github.com/ViktorooReps/vival\n\n")

            tsts_file.write("DESCRIPTION\n\n")
            if self.description == None:
                self.description = "No description was provided for these tests."
            tsts_file.write("/{" + self.description + "}/\n")

            tsts_file.write("\n\n")

            if self.compiler_flags != None:
                tsts_file.write("FLAGS\n\n")
                tsts_file.write("/{" + self.compiler_flags + "}/\n")

                tsts_file.write("\n\n")

            if self.main_text != None:
                tsts_file.write("MAIN\n\n")
                tsts_file.write("/{" + self.main_text + "}/\n")

                tsts_file.write("\n\n")

            dashes = (line_len - len("Tests")) // 2
            tsts_file.write(dashes * "-" + "Tests" + dashes * "-")
            tsts_file.write("\n\n")

            for test in tests:
                tsts_file.write(str(test))
                tsts_file.write("\n\n")

