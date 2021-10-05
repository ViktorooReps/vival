from subprocess import PIPE
import subprocess

from typing import Dict, Any, List, Iterable, TextIO

import os

from tester.features import Tag, Feature, construct_test_features, construct_file_features, FeatureContainer


def scan(text: str, tags: Iterable[str]) -> Dict[str, List[int]]:
    """Scans given text for every tag from tags. 
    Returns map tag->[positions]"""
    res = {}
    for tag in tags:
        res[tag] = []

        tag_pos = text.find(tag)
        while tag_pos != -1:
            res[tag].append(tag_pos)

            tag_pos += len(tag)
            tag_pos = text.find(tag, tag_pos)

    return res


def alignable(example: str, target: str) -> bool:
    return target.startswith(example)


def align(possible: str, target: str, added_symbol: str) -> bool:
    total = len(possible)
    if total == 0 and len(target) == 0:
        return True

    for ind, example in enumerate(possible):
        if total > 1:
            example += added_symbol

        if alignable(example, target):
            aligned = align(possible[:ind] + possible[ind + 1:], target[len(example):], added_symbol)

            if aligned:
                return True

    return False


class Test(FeatureContainer):
    """Single extracted test"""

    def __init__(self, title='Unnamed Test'):
        super(Test, self).__init__()
        for feature in construct_test_features():
            self.add_feature(feature)

        self.title = title
        self.prog_output = None
        self.failed = None
        self.filled = False

    def validate(self):
        """Checks if prog_output is correct"""
        if 'mSHUFFLED' in self.get_feature(Tag.OUTPUT).mods:
            possible = self.get_feature(Tag.OUTPUT).merged_contents()
            return align(possible, self.prog_output, self.get_feature(Tag.OUTPUT).join_symbol)
        else:
            return self.get_feature(Tag.OUTPUT).merged_contents() == self.prog_output

    def run(self, exec_path: os.PathLike, timeout: float) -> bool:
        """Runs executable on this test. Returns True if run succeeded"""
        exec_path = os.path.abspath(exec_path)

        cmd = self.get_feature(Tag.CMD).merged_contents()
        stdin = self.get_feature(Tag.INPUT).merged_contents()
        startup = self.get_feature(Tag.STARTUP).merged_contents()
        cleanup = self.get_feature(Tag.CLEANUP).merged_contents()

        all_args = str(exec_path) + ' ' + cmd

        if startup is not None:
            for args in startup.split('\n'):
                if args != '':
                    code = os.waitstatus_to_exitcode(os.system(args))
                    if code != 0:
                        self.prog_output = 'The program was not executed due to errors during environment preparation stage. ' \
                                           'Failed to execute: ' + args
                        self.failed = True
                        return not self.failed
        try:
            prog_output = subprocess.run(all_args, stderr=subprocess.STDOUT, stdout=PIPE, input=stdin,
                                         timeout=timeout, encoding='ascii', shell=True).stdout

        except subprocess.TimeoutExpired:
            prog_output = 'Time limit exceeded'
            self.failed = True

        self.prog_output = prog_output

        if cleanup is not None:
            for args in cleanup.split('\n'):
                if args != '':
                    code = os.waitstatus_to_exitcode(os.system(args))
                    if code != 0:
                        self.prog_output = 'Cleanup stage failed. Failed to execute: ' + args
                        self.failed = True
                        return not self.failed

        if self.filled:
            self.failed = not self.validate()
            return not self.failed
        else:
            self.failed = False
            return not self.failed

    def fill(self) -> None:
        """Fills in test using last run"""
        self.filled = True
        self.replace_feature(Feature(Tag.OUTPUT, [self.prog_output]))

    def print_last_run(self) -> None:
        """Prints details on last run"""
        print('-' * 30)

        print(self.title + '\n')

        for feature in sorted(self._tag2feature.values()):
            if feature.info() is not None and not feature.is_empty():
                if feature.info() != '':
                    print(feature.info() + ':')
                print(feature.merged_contents() + '\n')

        print('PROGRAM OUTPUT:')
        print(self.prog_output + '\n')

        print('-' * 30)

    def __str__(self):
        str_repr = ''

        if self.filled:
            str_repr += self.title + '\n\n'
        else:
            str_repr += self.title + ' (unfilled)\n\n'

        for feature in self._tag2feature.values():
            if not feature.is_empty():
                str_repr += str(feature)

        return str_repr

    def add_feature(self, feature):
        super(Test, self).add_feature(feature)

        if feature.tag == Tag.OUTPUT:
            self.filled = True


class TestsParser(FeatureContainer):
    """Parses text file with tests"""

    def __init__(self, parse_format='new', expect_filled_tests=True):
        super(TestsParser, self).__init__()
        for feature in construct_file_features():
            self.add_feature(feature)

        self.format = parse_format
        self.expect_filled_tests = expect_filled_tests
        self.parse_details: Dict[str, Any] = {
            'ntests': 0,
            'format': None,
            'error_message': None,
            'warning_messages': [],
        }

    def __str__(self):
        desc = self.get_feature(Tag.DESCRIPTION).merged_contents()
        if desc != '':
            return desc
        else:
            return 'No description was provided'

    def get_flags(self) -> str:
        return self.get_feature(Tag.FLAGS).merged_contents()

    def has_main(self) -> bool:
        return not self.get_feature(Tag.MAIN).is_empty()

    def get_main(self) -> str:
        return self.get_feature(Tag.MAIN).merged_contents()

    def get_timeout(self) -> float:
        return float(self.get_feature(Tag.TIMEOUT).merged_contents())

    def parse(self, tests_file: TextIO):
        """Parses tests_file and returns list of Test objects. Returns None in case of an error"""
        self.parse_details['ntests'] = 0
        tests = []

        text = tests_file.read()

        brackets = scan(text, ['/{', '}/'])

        if len(brackets['/{']) != len(brackets['}/']):
            self.parse_details['error_message'] = 'Wrong format! Unmatched number of /{ and }/ brackets.\n'
            return None

        if len(brackets['/{']) == 0 or self.format == 'old':
            if self.format == 'new':
                self.parse_details['warning_messages'].append('Old format detected!\n')
            return self.old_parse(text)

        curr_test = Test('Test ' + str(self.parse_details['ntests'] + 1))
        filled_fields = set()
        prev_tag = None

        section_start = 0
        for lbracket_ind, rbracket_ind in zip(brackets['/{'], brackets['}/']):
            contents = text[lbracket_ind + len('/{'): rbracket_ind]

            wild_space = text[section_start: lbracket_ind]

            # search for tag in wild space
            search_results = scan(wild_space, map(lambda t: t.value, Feature.tag_configs.keys()))

            best_tag = None
            max_pos = -1
            for tag in search_results:
                if len(search_results[tag]) != 0:
                    curr_max = max(search_results[tag])
                    if curr_max > max_pos:
                        best_tag = tag

                    max_pos = max(curr_max, max_pos)

            # search for modifiers in wild space
            search_results = scan(wild_space, Feature.all_mods)
            mods = []
            for mod in search_results:
                if len(search_results[mod]) != 0:
                    mods.append(mod)

            if best_tag is None:
                # no tag was found in wild space
                feature = Feature(Tag(prev_tag), [contents])
                feature.apply_mod(*mods)

                if feature.is_file_type():
                    self.add_feature(feature)

                if feature.is_test_type():
                    curr_test.add_feature(feature)
            else:
                feature = Feature(Tag(best_tag), [contents])
                feature.apply_mod(*mods)

                if best_tag in filled_fields:
                    # new test has started
                    tests.append(curr_test)

                    self.parse_details['ntests'] += 1
                    curr_test = Test('Test ' + str(self.parse_details['ntests'] + 1))
                    filled_fields = {best_tag}

                    curr_test.add_feature(feature)
                else:
                    # continue filling in current test
                    if feature.is_file_type():
                        self.add_feature(feature)

                    if feature.is_test_type():
                        filled_fields.add(best_tag)
                        curr_test.add_feature(feature)

                prev_tag = best_tag

            section_start = rbracket_ind + len('}/')

        tests.append(curr_test)
        self.parse_details['ntests'] += 1

        return tests

    def old_parse(self, text):
        tests = []
        if self.expect_filled_tests:
            contents = list(text.split('[INPUT]\n'))[1:]
            for content in contents:
                curr_test = Test('Test ' + str(self.parse_details['ntests'] + 1))

                if '{CMD}\n' in content:
                    cmd, inp = content.split('{CMD}\n')

                    curr_test.add_feature(Feature(Tag.CMD, [cmd]))
                else:
                    inp = content

                curr_test.add_feature(Feature(Tag.INPUT, [inp]))

                tests.append(curr_test)
                self.parse_details['ntests'] += 1
        else:
            contents = list(text.split('[INPUT]\n'))[1:]
            for content in contents:
                curr_test = Test("Test " + str(self.parse_details['ntests'] + 1))

                content, outp = content.split('[OUTPUT]\n')

                if '{CMD}\n' in content:
                    cmd, inp = content.split('{CMD}\n')

                    curr_test.add_feature(Feature(Tag.CMD, [cmd]))
                else:
                    inp = content

                curr_test.add_feature(Feature(Tag.INPUT, [inp]))
                curr_test.add_feature(Feature(Tag.OUTPUT, [outp]))

                tests.append(curr_test)
                self.parse_details['ntests'] += 1

        return tests

    def write_tests(self, tests, output_filename):
        """Writes contents of tests and parser to output_filename"""
        with open(output_filename, 'w') as tests_file:
            line_len = 70

            tests_file.write('Contents of this file were automatically generated by VIVAL tool.\n\n')
            tests_file.write('Install with pip: pip install vival\n')
            tests_file.write('Visit GitHub for more info: https://github.com/ViktorooReps/vival\n\n')

            for feature in self._tag2feature.values():
                if not feature.is_empty():
                    tests_file.write(str(feature))

            dashes = (line_len - len('Tests')) // 2
            tests_file.write(dashes * '-' + 'Tests' + dashes * '-' + '\n\n')

            for test in tests:
                tests_file.write(str(test))
                tests_file.write("\n\n")
