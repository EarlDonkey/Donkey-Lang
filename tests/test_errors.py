import pytest

from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser


def run_src(src: str) -> None:
    prog = Parser(Lexer(src).tokenize()).parse()
    Interpreter().run(prog)


def test_undefined_variable_position():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src("print(nope);")
    e = exc_info.value
    assert (e.line, e.col) == (1, 7)
    assert "undefined variable 'nope'" in str(e)


def test_type_error_points_at_operator():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src('print(1 + "a");')
    e = exc_info.value
    # the '+' is at column 9 in "print(1 + \"a\");"
    assert e.line == 1 and e.col == 9


def test_division_by_zero_position():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src("print(1 / 0);")
    e = exc_info.value
    # '/' is at column 9
    assert e.line == 1 and e.col == 9


def test_error_position_multi_line():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src("let x = 1;\nlet y = 2;\nprint(nope);")
    e = exc_info.value
    assert e.line == 3


def test_condition_error_points_at_if():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src("if 1 { print(0); }")
    e = exc_info.value
    # 'if' is at line 1, col 1
    assert e.line == 1 and e.col == 1


def test_wrong_arity_points_at_call():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src("fn f(a) -> num { return a; }\nf();")
    e = exc_info.value
    # 'f' call is on line 2
    assert e.line == 2


def test_undefined_assign_position():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src("x = 1;")
    e = exc_info.value
    assert e.line == 1 and e.col == 1


def test_call_undefined_function():
    with pytest.raises(DonkyRuntimeError) as exc_info:
        run_src("nope();")
    e = exc_info.value
    assert (e.line, e.col) == (1, 1)