# VIVAL

Command line app to validate standard I/O applications on series of tests.

# Installation

Everything should work on Linux, Windows and MacOS with Python 3.6+ versions. Also having C/C++ compiler installed is recommended but isn't required.

## Using Pip

```bash
  $ pip install vival
```
## Manual

```bash
  $ git clone https://github.com/ViktorooReps/vival
  $ cd vival
  $ python setup.py install
```

# Usage

## Testing

VIVAL supports compiling C/C++ source code with gcc/g++ compilers. Make sure you have them installed and available through CLI.

`vival <executable or source code> -t <path/tests.txt>`

Here are some flags you may find useful:
* `-t <path/tests.txt>` to specify path to text file with tests (required).
* `-nt <INTEGER>` to set the number of failed tests displayed.
* `-o <path/output.txt>` if specified, will write all tests to output.txt (recommended in fill mode).

## Creating your own tests

All the tests file structure condenses to pairs __(tag, tagged text)__, where tag specifies the use of it's text.

Tags and their meaning (some tags might not be available on earlier versions of VIVAL) for v3.1:

Tag         | Category | Tagged text meaning
----------- | -------- | -------------------
INPUT       | Test     | What will executed program get on stdin. 
CMD         | Test     | Command line arguments with which the program will be executed.
OUTPUT      | Test     | Expected contents of stdout.
COMMENT     | Test     | Some commentary on test that will be displayed if program fails it.
MAIN        | File     | Some auxillary code (usually just `int main() { ... }`) that will be compiled and linked with given source code (ignored if executable is given as argument). 
FLAGS       | File     | Flags that will be passed to compiler.
DESCRIPTION | File     | Description of tests file.
STARTUP     | Test     | Shell commands that will be executed before test.
CLEANUP     | Test     | Shell commands that will be executed after test.
TIMEOUT     | File     | Sets time limit in seconds for all tests in the file (default is 2.0 sec).

The body of tests file consists of repeating sections of "wild space" and bracketed text: <...WS...>__/{__<...text...>__}/__ . Wild space is mostly skipped apart from tags that will define meaning of text in brackets. The text in brackets stays unformatted.

So, for example:
```
The text that is going to be skipped
INPUT
This will be skipped as well /{1 2 3}/
```
Will be converted to pair `(INPUT, "1 2 3")`.

If there are multiple tags only the last one will define bracketed text's meaning.

There are two categories of tags: the ones that define some features of a particular test and the ones that define features of an entire tests file. Only one definition of each feature is allowed, so when multiple File feature definitions are present in file, the last one is used. Redifinitions of Test features mark the beginning of a new test.

For example, file with such contents: 
```
DESCRIPTION /{Description 1}/
DESCRIPTION /{Description 2}/ <- DESCRIPTION is redefined

COMMENT /{Empty test}/

MAIN /{int sum(int a, int b) { return a + b; }}/

COMMENT <- the start of a new test
/{Some other test}/
INPUT
/{1}/
OUTPUT
/{}/
```
Will be translated to File features: `{(DESCRIPTION, "Description 2"), (MAIN, "int sum(int a, int b) { return a + b; }")}`, and two tests: `{(COMMENT, "Empty test")}` and `{(COMMENT, "Some other test"), (INPUT, "1"), (OUTPUT, "")}`

Tests without `OUTPUT` feature are considered unfilled and VIVAL wont't run given program on them. These tests can be filled in manually or using another executable.

## Filling in

Fill mode activates with flag `-m`:

`vival <executable or source code> -t <path/tests.txt> -m fill`

VIVAL in fill mode runs given executable on unfilled tests, saving the output from stdout. \
But it will be lost unless `-o <path/output.txt>` is specified:

`vival <executable or source code> -t <path/tests.txt> -m fill -o <path/output.txt>`

In which case executable's output on a test will be saved as `OUTPUT` feature of test and then resulting filled tests will be written to `output.txt`.

# Contribution

If you found a bug or just isn't sure how to use VIVAL, please consider creating an issue describing your problem. It might help other users as well as future project development.  
If you want to fix any known bug or add new functionality, clone this repository, branch out from `dev` branch, add any changes you think are necessary, push, and create pull request to merge your changes into `dev` branch. They will later be added to `master` branch as well as PyPI. 
