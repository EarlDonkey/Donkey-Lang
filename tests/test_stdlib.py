import contextlib
import io
import os

import pytest

from donky import modules
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser
from donky.vm import VM
from donky.compiler import Compiler


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_donk(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    prog = modules.expand(prog, REPO_ROOT)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(prog)
    return buf.getvalue()


def test_repeat():
    src = 'import "lib/format.donk"; print(repeat("ab", 3));'
    assert run_donk(src) == "ababab\n"


def test_repeat_zero():
    src = 'import "lib/format.donk"; print(repeat("x", 0));'
    assert run_donk(src) == "\n"


def test_pad_left():
    src = 'import "lib/format.donk"; print(pad_left("42", 5, " "));'
    assert run_donk(src) == "   42\n"


def test_pad_left_no_pad():
    src = 'import "lib/format.donk"; print(pad_left("hello", 3, "-"));'
    assert run_donk(src) == "hello\n"


def test_pad_right():
    src = 'import "lib/format.donk"; print(pad_right("hi", 5, "."));'
    assert run_donk(src) == "hi...\n"


def test_format_num_basic():
    src = 'import "lib/format.donk"; print(format_num(3.14159, 2));'
    assert run_donk(src) == "3.14\n"


def test_format_num_integer_input():
    src = 'import "lib/format.donk"; print(format_num(5, 2));'
    assert run_donk(src) == "5.00\n"


def test_format_num_short_decimal():
    src = 'import "lib/format.donk"; print(format_num(0.5, 2));'
    assert run_donk(src) == "0.50\n"


def test_format_num_negative():
    src = 'import "lib/format.donk"; print(format_num(-3.14, 2));'
    assert run_donk(src) == "-3.14\n"


def test_format_num_zero_places():
    src = 'import "lib/format.donk"; print(format_num(3.9, 0));'
    assert run_donk(src) == "3\n"


def test_format_num_truncates():
    # Documented behavior: truncates rather than rounds
    src = 'import "lib/format.donk"; print(format_num(3.999, 2));'
    assert run_donk(src) == "3.99\n"


def test_format_num_ten_thirds():
    src = 'import "lib/format.donk"; print(format_num(10 / 3, 2));'
    assert run_donk(src) == "3.33\n"


def test_stdlib_diff_vm(tmp_path):
    """Stdlib runs identically on the VM."""
    src = 'import "lib/format.donk"; print(format_num(3.14159, 2)); print(repeat("=", 10));'
    prog = Parser(Lexer(src).tokenize()).parse()
    prog = modules.expand(prog, REPO_ROOT)
    code = Compiler().compile(prog)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        VM().run(code)
    assert buf.getvalue() == "3.14\n==========\n"