from tempfile import TemporaryDirectory
from tester.testmanip import TestsParser
from tester.compiler import Compiler

import click
import os

import pkg_resources 

__version__ = pkg_resources.require("vival")[0].version

#TODO progress bar

def detect_lang(executable_path):
    if executable_path.endswith(".c"):
        return "C"

    if executable_path.endswith(".cpp"):
        return "C++"

    if executable_path.endswith(".py"):
        return "Python"
        
    return None

@click.command()
@click.version_option(__version__, prog_name="VIVAL")
@click.option("-t", "--tests", "tests_file", default="tests.txt", type=click.File(), 
    help="Path to file with tests.")
@click.option("-nt", "--ntests", default=5, show_default=True, type=click.INT,
    help="Number of failed tests to display.")
@click.option("-o", "--output", "output_filename", default=None, type=click.Path(writable=True), 
    help="File to store all the extracted (and maybe filled) tests.")
@click.option("-l", "--lang", default="C++", show_default=True, type=click.Choice(["C", "C++", "Python"], case_sensitive=False),
    help="Source language.")
@click.option("-m", "--mode", default="test", type=click.Choice(["fill", "test"], case_sensitive=False),
    help="In fill mode will fill in outputs of unfilled tests. In test mode will run executable on given tests.")
@click.option('--old-format', is_flag=True,
    help="Flag for backward compatibility.")
@click.argument("executable_path", type=click.Path(exists=True, resolve_path=True))
def main(executable_path, tests_file, ntests, output_filename, lang, mode, old_format):
    with TemporaryDirectory() as tmpdir_name:
        print("wtf")

        if output_filename != None:
            output_filename = os.path.abspath(output_filename)

        if mode == "test":
            expected_tests = "filled"
        else:
            expected_tests = "unfilled"
        
        if old_format:
            parse_format = "old"
        else:
            parse_format = "new"
        
        parser = TestsParser(
            expect_filled_tests=(expected_tests == "filled"), 
            parse_format=parse_format
        )
        tests = parser.parse(tests_file)

        if tests == None:
            print("Parse failed!")
            print(parser.parse_details["error_message"])
            return

        if len(parser.parse_details["warning_messages"]) > 0:
            print("\nWarnings from parser:")
            for warning in parser.parse_details["warning_messages"]:
                print(warning)

        detected_language = detect_lang(executable_path)
        if detected_language == None:
            detected_language = lang
        
        if detected_language == "C++" or detected_language == "C":
            compiler = Compiler(lang=detected_language, tmp_dir=tmpdir_name, flags=parser.get_flags()) 

            if parser.get_main() != None:
                executable_path = compiler.plant_main(parser, executable_path)

            if executable_path != None and not os.access(executable_path, mode=os.X_OK):
                executable_path = compiler.compile(executable_path)

            if executable_path == None:
                print("Compilation failed!")
                print(compiler.compile_details["error_message"])
                return

        passed = 0
        suitable = 0

        file_features = parser.get_file_features()

        total_tests = len(tests)
        if mode == "test":
            for test in tests:
                if test.filled:
                    run_succeded = test.run(executable_path, file_features)
                    suitable += 1

                    if run_succeded:
                        passed += 1
            
        if mode == "fill":
            for test in tests:
                if not test.filled:
                    run_succeded = test.run(executable_path, file_features)
                    suitable += 1

                    if run_succeded:
                        passed += 1
                        test.fill()

        print("\n" + str(parser) + "\n")

        if passed < suitable:
            print("Failed on these tests:\n")
            
            printed = 0
            for test in tests:
                if printed >= ntests:
                    break

                if test.failed:
                    test.print_last_run()
                    printed += 1
        
        if mode == "test":
            print("Passed tests: " + str(passed) + "/" + str(suitable))

        if mode == "fill":
            print("Filled tests: " + str(passed) + "/" + str(suitable))

        if output_filename != None:
            parser.write_tests(tests, output_filename)


if __name__ == "__main__":
    main()
    