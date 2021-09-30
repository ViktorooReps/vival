from tempfile import TemporaryDirectory

from tester.testmanip import TestsParser
from tester.compiler import Compiler
from tester.lang import Lang, detect_lang

from tqdm import tqdm
import click
import os

import pkg_resources

__version__ = pkg_resources.require('vival')[0].version


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
              default='C++', show_default=True,
              type=click.Choice(['C', 'C++', 'Python'], case_sensitive=False),
              help='Source language.')
@click.option('-m', '--mode',
              default='test',
              type=click.Choice(['fill', 'test'], case_sensitive=False),
              help='In fill mode will fill in outputs of unfilled tests. '
                   'In test mode will run executable on given tests.')
@click.option('--old-format',
              is_flag=True,
              help='Flag for backward compatibility.')
@click.argument("executable_path", type=click.Path(exists=True, resolve_path=True))
def main(executable_path, tests_file, ntests, output_filename, lang, mode, old_format):
    with TemporaryDirectory() as tempdir_name:
        if output_filename is not None:
            output_filename = os.path.abspath(output_filename)

        expected_tests = 'filled' if mode == 'test' else 'unfilled'
        parse_format = 'old' if old_format else 'new'

        parser = TestsParser(
            expect_filled_tests=(expected_tests == 'filled'),
            parse_format=parse_format
        )
        tests = parser.parse(tests_file)

        if tests is None:
            print('Parse failed!')
            print(parser.parse_details['error_message'])
            return

        if len(parser.parse_details['warning_messages']) > 0:
            print('\nWarnings from parser:')
            for warning in parser.parse_details['warning_messages']:
                print(warning)

        detected_language = detect_lang(executable_path)
        if detected_language is None:
            detected_language = lang

        if detected_language == Lang.CPP or detected_language == Lang.C:
            compiler = Compiler(lang=detected_language, temp_dir=tempdir_name, flags=parser.get_flags())

            if parser.has_main():
                executable_path = compiler.plant_main(parser, executable_path)
            else:
                executable_path = compiler.compile(executable_path)

            if executable_path is None:
                print('Compilation failed!')
                print(compiler.compile_details['error_message'])
                return

        passed = 0
        suitable = 0

        timeout = parser.get_timeout()

        mode2desc = {'test': 'Testing', 'fill': 'Filling'}
        for test in tqdm(tests, desc=mode2desc[mode], leave=False):
            run_succeeded = False
            if (test.filled and mode == 'test') or (not test.filled and mode == 'fill'):
                run_succeeded = test.run(executable_path, timeout)
                suitable += 1

            if run_succeeded:
                passed += 1
                if mode == 'fill':
                    test.fill()

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

        if mode == 'test':
            print('Passed tests: ' + str(passed) + '/' + str(suitable))

        if mode == 'fill':
            print('Filled tests: ' + str(passed) + '/' + str(suitable))

        if output_filename is not None:
            parser.write_tests(tests, output_filename)


if __name__ == '__main__':
    main()
