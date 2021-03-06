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
        self.type = "unfilled"

        self.cmd_join_symbol = " "
        self.stdin_join_symbol = "\n"
        self.stdout_join_symbol = "\n"
        self.comment_join_symbol = "\n"

        self.prog_output = None
        self.failed = None

    def run(self, exec_path):
        """Runs executable on this test. Returns True if run succeded"""
        all_args = [exec_path]
        joined_cmd = self.cmd_join_symbol.join(self.cmd)
        joined_stdin = self.stdin_join_symbol.join(self.stdin)
        joined_stdout = self.stdout_join_symbol.join(self.stdout)

        for arg in joined_cmd.split(" "):
            if arg != "":
                all_args.append(arg)

        prog_output = subprocess.run(all_args, 
                                    stderr=subprocess.STDOUT, 
                                    stdout=PIPE,
                                    input=joined_stdin, 
                                    encoding='ascii').stdout
        
        self.prog_output = prog_output

        if self.type == "filled":
            self.failed = (prog_output != joined_stdout)
            return (prog_output == joined_stdout)
        else:
            self.failed = False
            return True
    
    def fill(self):
        """Fills in test using last run"""
        self.type = "filled"
        self.stdout = [self.prog_output]

    def print_last_run(self):
        """Prints details on last run"""
        print("-" * 30)
        
        joined_comment = self.comment_join_symbol.join(self.comment)
        print(joined_comment)

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


class Compiler:
    """Compiles supported languages to executable code"""

    supported_extentions = [".c", ".cpp", ".o"]
    compiler = {
        "C": "gcc",
        "C++": "g++"
    }

    def __init__(self, lang="C++"):
        self.guess_lang = lang
        self.compile_details = {
            "error_message": None
        }

    def plant_main(self, parser, tmpdir_path, exec_path):
        """Compiles given C/C++ code with new entry point. Returns new executable path"""

        compiler = new_compiler()

        if exec_path.endswith(".c"):
            self.guess_lang = "C"

        elif exec_path.endswith(".cpp"):
            self.guess_lang = "C++"

        # create main(.c/.cpp) in tmpdir

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
            subprocess.run([self.compiler[self.guess_lang], "-c", main_src, "-o", main_obj], check=True)
            subprocess.run([self.compiler[self.guess_lang], "-c", exec_path, "-o", exec_obj], check=True)
        except CalledProcessError as err:
            self.compile_details["error_message"] = "Failed to compile source files. Make sure you have C/C++ compiler installed."
            return None

        # link object files
        try:
            subprocess.run([self.compiler[self.guess_lang], main_obj, exec_obj, "-o", res_path], check=True)
        except CalledProcessError as err:
            self.compile_details["error_message"] = "Failed to link object files."
            return None

        return res_path
            

class TestsParser:
    """Parses text file with tests"""

    id_tags = {"INPUT", "OUTPUT", "MAIN", "CMD", "COMMENT", "DESCRIPTION"}
    global_tags = {"MAIN", "DESCRIPTION"}

    def __init__(self, parse_format="new", expected_tests="filled"): 
        self.description = None
        self.main_text = None
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
            tsts_file.write("Contents of this file were automatically generated by VIVAL tool.\n\n")
            tsts_file.write("Install with pip: pip install vival\n")
            tsts_file.write("Visit GitHub for more info: https://github.com/ViktorooReps/vival\n\n")

            tsts_file.write("DESCRIPTION\n\n")
            if self.description == None:
                self.description = "No description was provided for these tests."
            tsts_file.write("/{" + self.description + "}/\n")

            tsts_file.write("\n\n")

            if self.main_text != None:
                tsts_file.write("MAIN\n\n")
                tsts_file.write("/{" + self.main_text + "}/\n")

                tsts_file.write("\n\n")

            tsts_file.write(17 * "-" + "Tests" + 17 * "-")
            tsts_file.write("\n\n")

            for test in tests:
                title = test.comment[0]
                if len(test.comment) > 1:
                    comment = test.comment_join_symbol.join(test.comment[1:])
                else:
                    comment = "No comment was provided."
                
                joined_stdin = test.stdin_join_symbol.join(test.stdin)
                joined_stdout = test.stdout_join_symbol.join(test.stdout)
                joined_cmd = test.cmd_join_symbol.join(test.cmd)

                if test.type == "filled":
                    tsts_file.write(title + "\n\n")

                if test.type == "unfilled":
                    tsts_file.write(title + " (unfilled)\n\n")

                tsts_file.write("COMMENT\n")
                tsts_file.write("/{" + comment + "}/\n")

                tsts_file.write("\n")

                if len(test.cmd) > 0:
                    tsts_file.write("CMD\n")
                    tsts_file.write("/{" + joined_cmd + "}/\n")

                    tsts_file.write("\n")

                if len(test.stdin) > 0:
                    tsts_file.write("INPUT\n")
                    tsts_file.write("/{" + joined_stdin + "}/\n")

                    tsts_file.write("\n")

                if len(test.stdout) > 0:
                    tsts_file.write("OUTPUT\n")
                    tsts_file.write("/{" + joined_stdout + "}/\n")
                
                tsts_file.write("\n\n\n")
    