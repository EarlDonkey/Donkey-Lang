import pytest

from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser


def run_src(src: str) -> None:
    prog = Parser(Lexer(src).tokenize()).parse()
    Interpreter().run(prog)


# ---------- expressions / print ----------

def test_arith(capsys):
    run_src("print(1 + 2 * 3);")
    assert capsys.readouterr().out == "7\n"


def test_parens(capsys):
    run_src("print((1 + 2) * 3);")
    assert capsys.readouterr().out == "9\n"


def test_string_concat(capsys):
    run_src('print("a" + "b");')
    assert capsys.readouterr().out == "ab\n"


def test_bool_print(capsys):
    run_src("print(true); print(false);")
    assert capsys.readouterr().out == "true\nfalse\n"


# ---------- let / assign / scoping ----------

def test_let_and_lookup(capsys):
    run_src("let x = 5; print(x);")
    assert capsys.readouterr().out == "5\n"


def test_assignment(capsys):
    run_src("let x = 1; x = x + 4; print(x);")
    assert capsys.readouterr().out == "5\n"


def test_block_shadows_let(capsys):
    run_src("let x = 1; if true { let x = 2; print(x); } print(x);")
    assert capsys.readouterr().out == "2\n1\n"


def test_block_assignment_reaches_outer(capsys):
    run_src("let x = 1; if true { x = 99; } print(x);")
    assert capsys.readouterr().out == "99\n"


# ---------- control flow ----------

def test_if_else_taken(capsys):
    run_src('if 1 < 2 { print("yes"); } else { print("no"); }')
    assert capsys.readouterr().out == "yes\n"


def test_if_else_not_taken(capsys):
    run_src('if 2 < 1 { print("yes"); } else { print("no"); }')
    assert capsys.readouterr().out == "no\n"


def test_while_counts(capsys):
    run_src("let i = 0; while i < 3 { print(i); i = i + 1; }")
    assert capsys.readouterr().out == "0\n1\n2\n"


# ---------- functions ----------

def test_call_with_return(capsys):
    run_src("fn add(a, b) -> num { return a + b; } print(add(2, 3));")
    assert capsys.readouterr().out == "5\n"


def test_implicit_none(capsys):
    run_src("fn nothing() -> void { } print(nothing());")
    assert capsys.readouterr().out == "None\n"


def test_recursion(capsys):
    run_src(
        "fn fib(n) -> num {"
        "  if n < 2 { return n; }"
        "  return fib(n - 1) + fib(n - 2);"
        "}"
        "print(fib(10));"
    )
    assert capsys.readouterr().out == "55\n"


def test_return_inside_while_exits(capsys):
    run_src(
        "fn f() -> num {"
        "  let i = 0;"
        "  while true {"
        "    if i == 3 { return i; }"
        "    i = i + 1;"
        "  }"
        "  return -1;"
        "}"
        "print(f());"
    )
    assert capsys.readouterr().out == "3\n"


# ---------- errors ----------

def test_undefined_var():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(nope);")


def test_assign_undefined():
    with pytest.raises(DonkyRuntimeError):
        run_src("x = 1;")


def test_type_mismatch_plus():
    with pytest.raises(DonkyRuntimeError):
        run_src('print(1 + "a");')


def test_bool_is_not_number():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(1 + true);")


def test_div_by_zero():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(1 / 0);")


def test_wrong_arity():
    with pytest.raises(DonkyRuntimeError):
        run_src("fn f(a) -> num { return a; } f();")


def test_call_non_function():
    with pytest.raises(DonkyRuntimeError):
        run_src("let x = 1; x();")


def test_non_bool_condition():
    with pytest.raises(DonkyRuntimeError):
        run_src("if 1 { print(0); }")


def test_return_at_top_level():
    with pytest.raises(DonkyRuntimeError):
        run_src("return 1;")


# ---------- Session 2 additions ----------

def test_modulo(capsys):
    run_src("print(10 % 3);")
    assert capsys.readouterr().out == "1\n"


def test_modulo_zero():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(5 % 0);")


def test_not_true(capsys):
    run_src("print(!true);")
    assert capsys.readouterr().out == "false\n"


def test_not_false(capsys):
    run_src("print(!false);")
    assert capsys.readouterr().out == "true\n"


def test_not_on_number():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(!1);")


def test_and_true(capsys):
    run_src("print(true && true);")
    assert capsys.readouterr().out == "true\n"


def test_and_false(capsys):
    run_src("print(true && false);")
    assert capsys.readouterr().out == "false\n"


def test_or_false(capsys):
    run_src("print(false || false);")
    assert capsys.readouterr().out == "false\n"


def test_or_true(capsys):
    run_src("print(false || true);")
    assert capsys.readouterr().out == "true\n"


def test_and_short_circuits():
    # If not short-circuited, this would evaluate 1/0 and raise.
    run_src("print(false && (1 / 0 == 0));")


def test_or_short_circuits():
    run_src("print(true || (1 / 0 == 0));")


def test_and_rejects_non_bool():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(1 && true);")


def test_not_associativity_in_expression(capsys):
    run_src("print(!true || true);")
    assert capsys.readouterr().out == "true\n"