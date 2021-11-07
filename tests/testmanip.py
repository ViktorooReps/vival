import unittest
from tempfile import TemporaryFile

from tester.testmanip import TestsParser


class TestTest(unittest.TestCase):
    pass  # TODO


class TestsParserTest(unittest.TestCase):
    # TODO

    def setUp(self) -> None:
        self.tests_file = TemporaryFile(mode='r+')
        self.tests_file.write("""
        FLAGS /{1 2 3 -fsanitize=smth}/
        INPUT /{inp1}/
        INPUT /{inp2}/
        OUTPUT /{outp2}/
        """)
        self.tests_file.seek(0)

    def test_sanitizers_manipulation(self):
        parser = TestsParser()
        parser.parse(self.tests_file)

        self.assertEqual(['smth'], parser.get_sanitizers())

        parser.delete_sanitizers()
        self.assertEqual([], parser.get_sanitizers())

    def tearDown(self) -> None:
        self.tests_file.close()
