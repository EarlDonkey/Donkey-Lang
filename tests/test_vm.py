import contextlib
import io

import pytest

from donky.bytecode import CodeObject
from donky.compiler import Compiler
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser
from donky.vm import VM


def _compile(src: str) -> CodeObject:
    prog = Parser(Lexer(src).tokenize()).parse()
    return Compiler().compile(prog)


def _run_interp(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(prog)
    return buf.getvalue()


def _run_vm(src: str) -> str:
    code = _compile(src)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        VM().run(code)
    return buf.getvalue()


def assert_same(src: str) -> str:
    a = _run_interp(src)
    b = _run_vm(src)
    assert a == b, f"divergence on {src!r}: interp={a!r} vm={b!r}"
    return a


def assert_same_error(src: str) -> None:
    iexc = None
    try:
        _run_interp(src)
    except DonkyRuntimeError as e:
        iexc = e
    vexc = None
    try:
        _run_vm(src)
    except DonkyRuntimeError as e:
        vexc = e
    assert iexc is not None, f"interpreter did not raise for {src!r}"
    assert vexc is not None, f"vm did not raise for {src!r}"
    assert iexc.message == vexc.message, (
        f"message mismatch on {src!r}: "
        f"interp={iexc.message!r} vm={vexc.message!r}"
    )


# ---------- differential: happy paths ----------

def test_diff_arith():
    assert assert_same("print(1 + 2 * 3);") == "7\n"


def test_diff_parens():
    assert assert_same("print((1 + 2) * 3);") == "9\n"


def test_diff_string_concat():
    assert assert_same('print("a" + "b");') == "ab\n"


def test_diff_bool_print():
    assert assert_same("print(true); print(false);") == "true\nfalse\n"


def test_diff_let_global():
    assert assert_same("let x = 5; print(x);") == "5\n"


def test_diff_assign():
    assert assert_same("let x = 1; x = x + 4; print(x);") == "5\n"


def test_diff_block_shadow():
    assert_same("let x = 1; if true { let x = 2; print(x); } print(x);")


def test_diff_block_assign():
    assert_same("let x = 1; if true { x = 99; } print(x);")


def test_diff_if_taken():
    assert_same('if 1 < 2 { print("yes"); } else { print("no"); }')


def test_diff_if_not_taken():
    assert_same('if 2 < 1 { print("yes"); } else { print("no"); }')


def test_diff_while():
    assert_same("let i = 0; while i < 3 { print(i); i = i + 1; }")


def test_diff_modulo():
    assert assert_same("print(10 % 3);") == "1\n"


def test_diff_not():
    assert_same("print(!true); print(!false);")


def test_diff_and():
    assert_same("print(true && false); print(true && true);")


def test_diff_or():
    assert_same("print(false || false); print(false || true);")


def test_diff_and_short_circuit():
    assert assert_same("print(false && (1 / 0 == 0));") == "false\n"


def test_diff_or_short_circuit():
    assert assert_same("print(true || (1 / 0 == 0));") == "true\n"


def test_diff_function():
    assert assert_same(
        "fn add(a, b) -> num { return a + b; } print(add(2, 3));"
    ) == "5\n"


def test_diff_implicit_none():
    assert_same("fn n() -> void { } print(n());")


def test_diff_recursion():
    src = (
        "fn fib(n) -> num {"
        "  if n < 2 { return n; }"
        "  return fib(n - 1) + fib(n - 2);"
        "}"
        "print(fib(10));"
    )
    assert assert_same(src) == "55\n"


def test_diff_return_in_while():
    src = (
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
    assert assert_same(src) == "3\n"


def test_diff_builtin_len():
    assert assert_same('print(len("hello"));') == "5\n"


def test_diff_builtin_str():
    assert assert_same('print(str(10) + "!");') == "10!\n"


def test_diff_builtin_num():
    assert assert_same('print(num("42") + 8);') == "50\n"


def test_diff_builtin_type():
    assert_same(
        'print(type(1)); print(type("a")); print(type(true));'
    )


def test_diff_builtin_shadow():
    assert assert_same("let len = 5; print(len);") == "5\n"


def test_diff_empty_program():
    assert_same("")


def test_diff_nested_function_call():
    src = (
        "fn add(a, b) -> num { return a + b; }"
        "fn sum3(a, b, c) -> num { return add(add(a, b), c); }"
        "print(sum3(1, 2, 3));"
    )
    assert assert_same(src) == "6\n"


# ---------- differential: errors ----------

def test_diff_err_undefined_var():
    assert_same_error("print(nope);")


def test_diff_err_assign_undefined():
    assert_same_error("x = 1;")


def test_diff_err_plus_mismatch():
    assert_same_error('print(1 + "a");')


def test_diff_err_bool_is_not_num():
    assert_same_error("print(1 + true);")


def test_diff_err_div_zero():
    assert_same_error("print(1 / 0);")


def test_diff_err_mod_zero():
    assert_same_error("print(5 % 0);")


def test_diff_err_wrong_arity():
    assert_same_error("fn f(a) -> num { return a; } f();")


def test_diff_err_call_non_function():
    assert_same_error("let x = 1; x();")


def test_diff_err_non_bool_condition():
    assert_same_error("if 1 { print(0); }")


def test_diff_err_not_on_number():
    assert_same_error("print(!1);")


def test_diff_err_and_non_bool():
    assert_same_error("print(1 && true);")


# ---------- direct VM tests ----------

def test_vm_stack_empty_after_pop():
    vm = VM()
    vm.run(_compile("1;"))
    assert vm.stack == []


def test_vm_frames_empty_after_run():
    vm = VM()
    vm.run(_compile("let x = 1;"))
    assert vm.frames == []


def test_vm_global_after_let():
    vm = VM()
    vm.run(_compile("let x = 42;"))
    assert vm.globals.get("x") == 42


def test_vm_while_terminates():
    vm = VM()
    vm.run(_compile("let i = 0; while i < 3 { i = i + 1; }"))
    assert vm.globals.get("i") == 3


def test_vm_recursion_clears_frames():
    vm = VM()
    vm.run(_compile(
        "fn f(n) -> num {"
        "  if n < 1 { return 0; }"
        "  return f(n - 1) + 1;"
        "}"
        "f(5);"
    ))
    assert vm.frames == []


def test_vm_error_has_position():
    vm = VM()
    code = _compile("print(nope);")
    with pytest.raises(DonkyRuntimeError) as exc_info:
        vm.run(code)
    e = exc_info.value
    assert e.line == 1 and e.col == 7


def test_vm_fib10_actually_computes():
    vm = VM()
    code = _compile(
        "fn fib(n) -> num {"
        "  if n < 2 { return n; }"
        "  return fib(n - 1) + fib(n - 2);"
        "}"
        "let r = fib(10);"
    )
    vm.run(code)
    assert vm.globals.get("r") == 55

# ---------- div differential ----------

def test_diff_div():
    assert assert_same("print(7 div 2);") == "3\n"


def test_diff_div_negative():
    assert_same("print(-7 div 2); print(7 div -2); print(-7 div -2);")


def test_diff_err_div_zero():
    assert_same_error("print(7 div 0);")


def test_diff_err_div_float():
    assert_same_error("print(7.0 div 2);")


# ---------- arrays differential ----------

def test_diff_array_literal():
    assert assert_same("print([1, 2, 3]);") == "[1, 2, 3]\n"


def test_diff_array_empty():
    assert assert_same("print([]);") == "[]\n"


def test_diff_array_index():
    assert_same("let a = [10, 20, 30]; print(a[1]);")


def test_diff_array_index_set():
    assert_same("let a = [1, 2, 3]; a[1] = 99; print(a);")


def test_diff_array_len():
    assert_same("print(len([1, 2, 3]));")


def test_diff_array_push():
    assert_same("let a = [1]; push(a, 2); print(a);")


def test_diff_array_pop():
    assert_same("let a = [1, 2, 3]; print(pop(a)); print(a);")


def test_diff_array_loop_sum():
    assert_same(
        "let a = [1, 2, 3, 4];"
        "let s = 0; let i = 0;"
        "while i < len(a) { s = s + a[i]; i = i + 1; }"
        "print(s);"
    )


def test_diff_array_nested():
    assert_same("let m = [[1, 2], [3, 4]]; print(m[1][0]);")


def test_diff_array_type():
    assert_same("print(type([1]));")


def test_diff_err_array_out_of_range():
    assert_same_error("let a = [1, 2]; print(a[5]);")


def test_diff_err_negative_index():
    assert_same_error("let a = [1, 2]; print(a[-1]);")


def test_diff_err_index_non_int():
    assert_same_error("let a = [1, 2]; print(a[0.5]);")


def test_diff_err_index_non_array():
    assert_same_error("let x = 5; print(x[0]);")


def test_diff_err_push_non_array():
    assert_same_error("push(5, 1);")


def test_diff_err_pop_empty():
    assert_same_error("let a = []; pop(a);")


def test_diff_err_index_set_oob():
    assert_same_error("let a = [1]; a[5] = 0;")

# ---------- Session 6: closures ----------

def test_diff_closure_counter():
    src = (
        "fn make_counter() -> any {"
        "  let n = 0;"
        "  fn inc() -> num { n = n + 1; return n; }"
        "  return inc;"
        "}"
        "let c = make_counter();"
        "print(c()); print(c()); print(c());"
    )
    assert assert_same(src) == "1\n2\n3\n"


def test_diff_closure_independent():
    src = (
        "fn make_counter() -> any {"
        "  let n = 0;"
        "  fn inc() -> num { n = n + 1; return n; }"
        "  return inc;"
        "}"
        "let a = make_counter();"
        "let b = make_counter();"
        "a(); a();"
        "print(b()); print(a());"
    )
    assert assert_same(src) == "1\n3\n"


def test_diff_closure_multi_level():
    src = (
        "fn outer() -> num {"
        "  let x = 10;"
        "  fn middle() -> num {"
        "    fn inner() -> num { return x + 1; }"
        "    return inner();"
        "  }"
        "  return middle();"
        "}"
        "print(outer());"
    )
    assert assert_same(src) == "11\n"


def test_diff_closure_captures_by_reference():
    src = (
        "fn f() -> num {"
        "  let x = 1;"
        "  fn get() -> num { return x; }"
        "  x = 42;"
        "  return get();"
        "}"
        "print(f());"
    )
    assert assert_same(src) == "42\n"


def test_diff_closure_survives_frame():
    src = (
        "fn make() -> any {"
        "  let n = 100;"
        "  fn f() -> num { return n; }"
        "  return f;"
        "}"
        "let g = make();"
        "print(g());"
    )
    assert assert_same(src) == "100\n"