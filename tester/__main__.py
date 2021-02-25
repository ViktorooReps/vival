from pprint import pprint as pp
from subprocess import Popen, PIPE, STDOUT

import sys
import os

import argparse
import subprocess

try:
    from resource import setrlimit, getrlimit
    import resource

    def limit_resources():
        setrlimit(resource.RLIMIT_NPROC, (900, 1000))
except ImportError:
    def limit_resources():
        pass

#TODO progress bar

def main():
    parser = argparse.ArgumentParser(description="Automatic tester")
    parser.add_argument("x_file", 
                        help="Path to the executable file you want to test.")

    parser.add_argument("--tests", "-t", default="tests.txt",
                        help="Path to the text file with tests.")

    parser.add_argument("--print", "-p", default="wrong", choices=["none", "all", "wrong"],
                        help="What types of tests you want to print: "
                        "none - no tests will be printed, "
                        "all - every test will be printed, "
                        "wrong - only the ones your program got wrong answers on will be printed.")

    parser.add_argument("--ntests", "-nt", default=5, type=int, 
                        help="How many tests of specified type you want to be printed.")

    parser.add_argument("--mode", "-m", choices=["fill", "test"], default="test",
                        help="Choose what mode you want: test lets you test your programs "
                        "and fill lets you fill in outputs for test inputs using x_file executable.")

    parser.add_argument("--output_file", "-o", default="output.txt",
                        help="In fill mode lets you specify path to file with filled in tests.")

    parser.add_argument("--repeat", "-r", default=1, type=int,
                        help="How many times to repeat the same tests (high value is recommended "
                        "when result might be ambiguous)")

    args = parser.parse_args()


    if args.mode == "fill":
        tests = []
        outputs = []
        ntest = 0
        total_tests = 0
        written = 0
        with open(args.tests) as tst_file:
            tests = list(tst_file.read().split("[INPUT]\n"))[1:]
            for test in tests:
                cmd_args = ""
                if "{CMD}\n" in test:
                    cmd_args, test = test.split("{CMD}\n")
                
                all_args = ['./' + args.x_file]
                for arg in cmd_args.split(" "):
                    if arg != "":
                        all_args.append(arg)

                prog_output = subprocess.run(all_args, 
                                            stderr=subprocess.STDOUT, 
                                            stdout=PIPE,
                                            input=test, 
                                            encoding='ascii').stdout
                outputs.append(prog_output)

        with open(args.output_file, "w") as out_file:
            total_tests = len(tests)
            for test, output in zip(tests, outputs):
                ntest += 1
                out_file.writelines(["[INPUT]\n", 
                                    test,  
                                    "[OUTPUT]\n", 
                                    output])

                if args.print == "all":
                    print(30 * "-")
                    print("TEST ", ntest, ":\n", test, sep="")
                    print("PROGRAM OUTPUT:\n", output, sep="")
                    print(30 * "-")

                written += 1
                if written == args.ntests:
                    break

        
        print("Written tests: ", written, "/", total_tests, sep="")

    if args.mode == "test":
        with open(args.tests) as tst_file:
            ntest = 0
            passed = 0
            printed = 0

            tests = list(tst_file.read().split("[INPUT]\n"))[1:]
            for test in tests:
                if printed == int(args.ntests):
                    break

                ntest += 1

                test_input, test_output = test.split("[OUTPUT]\n")
                
                cmd_args = ""
                if "{CMD}\n" in test_input:
                    cmd_args, test_input = test_input.split("{CMD}\n")

                all_args = ['./' + args.x_file]
                for arg in cmd_args.split(" "):
                    if arg != "":
                        all_args.append(arg)
                
                test_failed = False
                for i in range(args.repeat):
                    prog_output = subprocess.run(all_args, 
                                                stderr=subprocess.STDOUT, 
                                                stdout=PIPE,
                                                input=test_input, 
                                                encoding='ascii').stdout
                    if prog_output != test_output:
                        test_failed = True
                        break
                
                if args.print == "all":
                    print(30 * "-")
                    print("TEST ", ntest, ":", sep="")
                    if len(cmd_args) > 1:
                        print("command line arguments:", all_args[1:])
                    print(test_input)
                    print("PROGRAM OUTPUT:\n", prog_output, sep="")
                    print("NEEDED OUTPUT:\n", test_output, sep="")
                    print(30 * "-")
                    printed += 1

                if not test_failed:
                    passed += 1
                else:
                    if args.print == "wrong":
                        print(30 * "-")
                        print("TEST ", ntest, ":", sep="")
                        if len(cmd_args) > 1:
                            print("command line arguments:", all_args[1:])
                        print(test_input)
                        print("PROGRAM OUTPUT:\n", prog_output, sep="")
                        print("NEEDED OUTPUT:\n", test_output, sep="")
                        print(30 * "-")
                        printed += 1

            print("Passed tests: ", passed, "/", ntest, sep="")

if __name__ == "__main__":
    main()
    