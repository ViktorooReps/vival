import unittest
from itertools import product
from pathlib import Path
from typing import Iterable, Optional

from tester.compiler import Compiler
from tester.features import Tag, Feature
from tester.lang import Lang
from tester.testmanip import Test, TestsParser


class CompilerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.simple_test = Test('simple')
        self.input = Feature(Tag.INPUT, ['1 2 3'])
        self.output = Feature(Tag.OUTPUT, ['2 3 4 '])

        self.simple_test.add_feature(self.input)
        self.simple_test.add_feature(self.output)

        self.lm_flags = ['-lm']
        self.fsanitize_flags = ['-fsanitize=undefined']

        self.c_compiler = Compiler(Lang.C)
        self.cpp_compiler = Compiler(Lang.CPP)
        self.flagged_c_compiler = Compiler(Lang.C, flags=' '.join(self.lm_flags + self.fsanitize_flags))
        self.flagged_cpp_compiler = Compiler(Lang.C, flags=' '.join(self.lm_flags + self.fsanitize_flags))

    def _run_tests(self, paths: Iterable[Path], compilers: Iterable[Compiler], main: Optional[str] = None) -> None:
        for path, compiler in product(paths, compilers):
            exec_path = compiler.compile(path, main=main)
            self.simple_test.run(exec_path)
            self.assertTrue(self.simple_test.validate())

    def test_simple_compilation(self):
        c_src_path = Path('tests/resources/src/inc/src.c')
        cpp_src_path = Path('tests/resources/src/inc/src.cpp')

        self._run_tests([c_src_path], [self.c_compiler, self.flagged_c_compiler])
        self._run_tests([cpp_src_path], [self.cpp_compiler, self.flagged_cpp_compiler])

    def test_main_insertion(self):
        c_src_path = Path('tests/resources/src/inc/no_main.c')
        cpp_src_path = Path('tests/resources/src/inc/no_main.cpp')

        parser = TestsParser()
        with open('tests/resources/filled/inc_tests/main_c.txt') as f:
            parser.parse(f)
            cmain = parser.get_main()

        with open('tests/resources/filled/inc_tests/main_cpp.txt') as f:
            parser.parse(f)
            cppmain = parser.get_main()

        self._run_tests([c_src_path], [self.c_compiler, self.flagged_c_compiler], main=cmain)
        self._run_tests([cpp_src_path], [self.cpp_compiler, self.flagged_cpp_compiler], main=cppmain)

