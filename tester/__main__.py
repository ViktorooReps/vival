from enum import Enum
from tempfile import TemporaryDirectory

from tester.testmanip import TestsParser, ParseFormat
from tester.compiler import Compiler
from tester.lang import Lang, detect_lang

from tqdm import tqdm
import click
import os
import shutil

import pkg_resources

__version__ = pkg_resources.require('vival')[0].version


class Mode(Enum):
    TEST = 'test'
    FILL = 'fill'


@click.command()
@click.version_option(__version__, prog_name='VIVAL')
@click.option('-t', '--tests', 'tests_file',
              default='tests.txt',
              type=click.File(),
              help='Path to file with tests.')
@click.option('-nt', '--ntests',
              default=5, show_default=True,
              type=click.INT,
              help='Number of failed tests to display.')
@click.option('-o', '--output', 'output_filename',
              default=None,
              type=click.Path(writable=True),
              help='File to store all the extracted (and maybe filled) tests.')
@click.option('-l', '--lang',
              default=Lang.CPP.value, show_default=True,
              type=click.Choice([lang.value for lang in Lang], case_sensitive=False),
              help='Source language.')
@click.option('-m', '--mode',
              default=Mode.TEST.value,
              type=click.Choice([mode.value for mode in Mode], case_sensitive=False),
              help='In fill mode will fill in outputs of unfilled tests. '
                   'In test mode will run executable on given tests.')
@click.option('--old-format',
              is_flag=True,
              help='Flag for backward compatibility.')
@click.argument("executable_path", type=click.Path(exists=True, resolve_path=True))
@click.option('-vg', '--valgrind',
              default=False,
              is_flag=True,
              help='Flag for valgrind memory checks.')
@click.option('-bf', '--break-fail',
              default=-1, show_default=False,
              type=click.INT,
              help='Stop testing when failed specified number of times.')
def main(executable_path, tests_file, ntests, output_filename, lang, mode, old_format, valgrind, break_fail):
    with TemporaryDirectory() as tempdir_name:
        executable_path = os.path.abspath(executable_path)

        if output_filename is not None:
            output_filename = os.path.abspath(output_filename)

        mode = Mode(mode)
        parser = TestsParser(ParseFormat.OLD if old_format else ParseFormat.NEW, expect_filled_tests=(mode == Mode.TEST))
        tests = parser.parse(tests_file)

        if parser.get_sanitizers() and valgrind:
            print('Warning: valgrind is enabled, so sanitizers were deleted from flags')
            parser.delete_sanitizers()

        if tests is None:
            print('Parse failed!')
            print(parser.parse_details['error_message'])
            return

        if len(parser.parse_details['warning_messages']) > 0:
            print('Warnings from parser:')
            for warning in parser.parse_details['warning_messages']:
                print(warning)

        detected_language = detect_lang(executable_path)
        if detected_language is None:
            detected_language = lang

        if detected_language == Lang.CPP or detected_language == Lang.C:
            compiler = Compiler(lang=detected_language, temp_dir=tempdir_name, flags=parser.get_flags())

            if parser.has_main():
                executable_path = compiler.compile(executable_path, parser.get_main())
            else:
                executable_path = compiler.compile(executable_path)

            if executable_path is None:
                print('Compilation failed!')
                print(compiler.compile_details['error_message'])
                return

        if valgrind:
            valgrind_options = [shutil.which('valgrind'), '-q', '--leak-check=full']
            executable_path = ' '.join(valgrind_options + [executable_path])

        passed = 0
        failed = 0
        suitable = 0

        timeout = parser.get_timeout()

        mode2desc = {Mode.TEST: 'Testing', Mode.FILL: 'Filling'}
        for test in tqdm(tests, desc=mode2desc[mode], leave=False):
            run_succeeded = False
            if (test.filled and mode == Mode.TEST) or (not test.filled and mode == Mode.FILL):
                run_succeeded = test.run(executable_path, timeout)
                suitable += 1

            if run_succeeded:
                passed += 1
                if mode == Mode.FILL:
                    test.fill()
            else:
                failed += 1
                if break_fail > 0 and failed >= break_fail:
                    break

        print('\n' + str(parser) + '\n')

        if passed < suitable:
            print('Failed on these tests:\n')

            printed = 0
            for test in tests:
                if printed >= ntests:
                    break

                if test.failed:
                    test.print_last_run()
                    printed += 1

        if mode == Mode.TEST:
            print('Passed tests: ' + str(passed) + '/' + str(suitable))

        if mode == Mode.FILL:
            print('Filled tests: ' + str(passed) + '/' + str(suitable))

        if output_filename is not None:
            parser.write_tests(tests, output_filename)


if __name__ == '__main__':
    main()
