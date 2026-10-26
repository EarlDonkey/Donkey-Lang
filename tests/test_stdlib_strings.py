import contextlib
import io
import os

from donky import modules
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    prog = modules.expand(prog, REPO_ROOT)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(prog)
    return buf.getvalue()


def test_starts_with_true():
    assert run('import "lib/strings.donk"; print(starts_with("hello", "he"));') == "true\n"


def test_starts_with_false():
    assert run('import "lib/strings.donk"; print(starts_with("hello", "lo"));') == "false\n"


def test_starts_with_empty():
    assert run('import "lib/strings.donk"; print(starts_with("hello", ""));') == "true\n"


def test_ends_with_true():
    assert run('import "lib/strings.donk"; print(ends_with("hello", "lo"));') == "true\n"


def test_ends_with_false():
    assert run('import "lib/strings.donk"; print(ends_with("hello", "he"));') == "false\n"


def test_slice_basic():
    assert run('import "lib/strings.donk"; print(slice("hello", 1, 4));') == "ell\n"


def test_slice_to_end():
    assert run('import "lib/strings.donk"; print(slice("hello", 2, 100));') == "llo\n"


def test_slice_empty():
    assert run('import "lib/strings.donk"; print(slice("hello", 2, 2));') == "\n"


def test_index_of_found():
    assert run('import "lib/strings.donk"; print(index_of("hello", "ll"));') == "2\n"


def test_index_of_not_found():
    assert run('import "lib/strings.donk"; print(index_of("hello", "zz"));') == "-1\n"


def test_index_of_at_start():
    assert run('import "lib/strings.donk"; print(index_of("hello", "he"));') == "0\n"


def test_index_of_empty_needle():
    assert run('import "lib/strings.donk"; print(index_of("hello", ""));') == "0\n"