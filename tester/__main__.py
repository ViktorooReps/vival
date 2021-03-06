from tempfile import TemporaryDirectory
from tester.testmanip import Compiler, TestsParser

import click

#TODO progress bar
#TODO run executables with c code, main insertion to .cpp and .c files 
#TODO documentation

@click.command()
@click.option("-t", "--tests", "tests_file", default="tests.txt", type=click.File(), 
    help="Path to file with tests.")
@click.option("-nt", "--ntests", default=5, show_default=True, type=click.INT,
    help="Number of failed tests to display.")
@click.option("-o", "--output", "output_filename", default=None, type=click.Path(writable=True), 
    help="File to store all the extracted (and maybe filled) tests.")
@click.option("-l", "--lang", default="C++", show_default=True, type=click.Choice(["C", "C++"], case_sensitive=False),
    help="Source language.")
@click.option("-m", "--mode", default="test", type=click.Choice(["fill", "test"], case_sensitive=False),
    help="In fill mode will fill in outputs of unfilled tests. In test mode will run executable on given tests.")
@click.option('--old-format', is_flag=True,
    help="Flag for backward compatibility.")
@click.argument("executable_path", type=click.Path(exists=True, resolve_path=True))
def main(executable_path, tests_file, ntests, output_filename, lang, mode, old_format):
    with TemporaryDirectory() as tmpdir_name:
        if mode == "test":
            expected_tests = "filled"
        else:
            expected_tests = "unfilled"
        
        if old_format:
            parse_format = "old"
        else:
            parse_format = "new"
        
        parser = TestsParser(expected_tests=expected_tests, parse_format=parse_format)
        compiler = Compiler(lang=lang) 

        tests = parser.parse(tests_file)

        passed = 0
        suitable = 0

        if tests == None:
            print("Parse failed!")
            print(parser.parse_details["error_message"])
            return

        if parser.main_text != None:
            executable_path = compiler.plant_main(parser, tmpdir_name, executable_path)

            if executable_path == None:
                print("Compilation failed!")
                print(compiler.compile_details["error_message"])
                return

        if len(parser.parse_details["warning_messages"]) > 0:
            print("\nWarnings from parser:")
            for warning in parser.parse_details["warning_messages"]:
                print(warning)

        if parser.description != None:
            print("\n" + parser.description + "\n")

        total_tests = len(tests)
        if mode == "test":
            for test in tests:
                if test.type == "filled":
                    run_succeded = test.run(executable_path)
                    suitable += 1

                    if run_succeded:
                        passed += 1
            
        if mode == "fill":
            for test in tests:
                if test.type == "unfilled":
                    run_succeded = test.run(executable_path)
                    suitable += 1

                    if run_succeded:
                        passed += 1
                        test.fill()

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
    