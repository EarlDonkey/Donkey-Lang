import pytest

from donky import ast_nodes as ast
from donky.lexer import Lexer
from donky.parser import Parser
from donky.typecheck import TypeCheckError, check

def check_src(src: str):
    prog = Parser(Lexer(src).tokenize()).parse()
    check(prog)


def test_valid_program_passes():
    check_src("let x = 1; print(x + 2);")


def test_undefined_var():
    with pytest.raises(TypeCheckError):
        check_src("print(x);")


def test_undefined_fn():
    with pytest.raises(TypeCheckError):
        check_src("f();")


def test_assign_undefined():
    with pytest.raises(TypeCheckError):
        check_src("x = 5;")


def test_condition_must_be_bool():
    with pytest.raises(TypeCheckError):
        check_src("if 1 { }")


def test_while_condition_bool():
    with pytest.raises(TypeCheckError):
        check_src("while 5 { }")


def test_bad_plus():
    with pytest.raises(TypeCheckError):
        check_src('let x = 1 + "a";')


def test_bad_unary_minus():
    with pytest.raises(TypeCheckError):
        check_src('let x = -"a";')


def test_bad_unary_not():
    with pytest.raises(TypeCheckError):
        check_src("let x = !1;")


def test_return_type_mismatch():
    with pytest.raises(TypeCheckError):
        check_src('fn f() -> num { return "a"; }')


def test_return_type_ok():
    check_src("fn f() -> num { return 1; }")


def test_arity_check():
    with pytest.raises(TypeCheckError):
        check_src("fn f(a, b) -> num { return 1; } f(1);")


def test_any_suppresses():
    # safe_div returns any, so its body's return values aren't checked
    check_src(
        'fn safe_div(a, b) -> any {'
        '  try { return a / b; } catch e { return 0; }'
        '}'
    )


def test_throw_must_be_string():
    with pytest.raises(TypeCheckError):
        check_src("throw 42;")


def test_index_non_container():
    with pytest.raises(TypeCheckError):
        check_src("let x = 5; let y = x[0];")


def test_bad_comparison():
    with pytest.raises(TypeCheckError):
        check_src('let x = 1 < "a";')


def test_valid_map():
    check_src('let m = {"a": 1}; let x = m["a"];')


def test_valid_for_array():
    check_src("for x in [1, 2, 3] { print(x); }")


def test_valid_for_string():
    check_src('for c in "abc" { print(c); }')


def test_for_bad_iterable():
    with pytest.raises(TypeCheckError):
        check_src("for x in 5 { }")