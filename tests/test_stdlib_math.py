import contextlib
import io
import os

from donky import modules
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser
import pytest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    prog = modules.expand(prog, REPO_ROOT)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(prog)
    return buf.getvalue()


def test_min():
    assert run('import "lib/math.donk"; print(min(3, 7));') == "3\n"


def test_max():
    assert run('import "lib/math.donk"; print(max(3, 7));') == "7\n"


def test_abs_positive():
    assert run('import "lib/math.donk"; print(abs(5));') == "5\n"


def test_abs_negative():
    assert run('import "lib/math.donk"; print(abs(-5));') == "5\n"


def test_pow():
    assert run('import "lib/math.donk"; print(pow(2, 10));') == "1024\n"


def test_pow_zero():
    assert run('import "lib/math.donk"; print(pow(5, 0));') == "1\n"


def test_sqrt_16():
    assert run('import "lib/math.donk"; print(sqrt(16));') == "4.0\n"


def test_sqrt_2_approx():
    # sqrt(2) ≈ 1.4142...
    assert run('import "lib/math.donk"; print(sqrt(2) > 1.41);') == "true\n"
    assert run('import "lib/math.donk"; print(sqrt(2) < 1.42);') == "true\n"


def test_sqrt_zero():
    assert run('import "lib/math.donk"; print(sqrt(0));') == "0\n"


def test_sqrt_negative_errors():
    with pytest.raises(DonkyRuntimeError):
        run('import "lib/math.donk"; print(sqrt(-1));')