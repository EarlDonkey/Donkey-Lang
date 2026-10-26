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
    
# ---------- Session 3: builtins ----------

def test_len(capsys):
    run_src('print(len("hello"));')
    assert capsys.readouterr().out == "5\n"


def test_len_empty(capsys):
    run_src('print(len(""));')
    assert capsys.readouterr().out == "0\n"


def test_len_non_string():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(len(5));")


def test_len_wrong_arity():
    with pytest.raises(DonkyRuntimeError):
        run_src('print(len("a", "b"));')


def test_str_returns_string(capsys):
    run_src('print(str(10) + "!");')
    assert capsys.readouterr().out == "10!\n"


def test_str_of_bool(capsys):
    run_src('print(str(true) + "!");')
    assert capsys.readouterr().out == "true!\n"


def test_str_of_string(capsys):
    run_src('print(str("hi") + "!");')
    assert capsys.readouterr().out == "hi!\n"


def test_str_is_string(capsys):
    run_src("print(type(str(10)));")
    assert capsys.readouterr().out == "string\n"


def test_num_from_int_string(capsys):
    run_src('print(num("42") + 8);')
    assert capsys.readouterr().out == "50\n"


def test_num_from_float_string(capsys):
    run_src('print(num("3.5") + 1.5);')
    assert capsys.readouterr().out == "5.0\n"


def test_num_from_number(capsys):
    run_src("print(num(10) + 5);")
    assert capsys.readouterr().out == "15\n"


def test_num_invalid():
    with pytest.raises(DonkyRuntimeError):
        run_src('print(num("abc"));')


def test_num_from_bool():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(num(true));")


def test_type_number(capsys):
    run_src("print(type(1));")
    assert capsys.readouterr().out == "number\n"


def test_type_string(capsys):
    run_src('print(type("a"));')
    assert capsys.readouterr().out == "string\n"


def test_type_bool(capsys):
    run_src("print(type(true));")
    assert capsys.readouterr().out == "bool\n"


def test_type_user_function(capsys):
    run_src("fn f() -> void { } print(type(f));")
    assert capsys.readouterr().out == "function\n"


def test_type_builtin(capsys):
    run_src("print(type(len));")
    assert capsys.readouterr().out == "function\n"


def test_builtin_shadowable(capsys):
    run_src("let len = 5; print(len);")
    assert capsys.readouterr().out == "5\n"

# ---------- Session 4: div ----------

def test_div_basic(capsys):
    run_src("print(7 div 2);")
    assert capsys.readouterr().out == "3\n"


def test_div_exact(capsys):
    run_src("print(10 div 5);")
    assert capsys.readouterr().out == "2\n"


def test_div_truncates_toward_zero(capsys):
    run_src("print(-7 div 2); print(7 div -2); print(-7 div -2);")
    assert capsys.readouterr().out == "-3\n-3\n3\n"


def test_div_by_zero():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(7 div 0);")


def test_div_rejects_floats():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(7.0 div 2);")


def test_div_rejects_bool():
    with pytest.raises(DonkyRuntimeError):
        run_src("print(true div 2);")


# ---------- Session 5: arrays ----------

def test_array_literal(capsys):
    run_src("print([1, 2, 3]);")
    assert capsys.readouterr().out == "[1, 2, 3]\n"


def test_array_empty(capsys):
    run_src("print([]);")
    assert capsys.readouterr().out == "[]\n"


def test_array_index(capsys):
    run_src("let a = [10, 20, 30]; print(a[1]);")
    assert capsys.readouterr().out == "20\n"


def test_array_index_set(capsys):
    run_src("let a = [1, 2, 3]; a[1] = 99; print(a);")
    assert capsys.readouterr().out == "[1, 99, 3]\n"


def test_array_len(capsys):
    run_src("print(len([1, 2, 3]));")
    assert capsys.readouterr().out == "3\n"


def test_array_push(capsys):
    run_src("let a = [1]; push(a, 2); print(a);")
    assert capsys.readouterr().out == "[1, 2]\n"


def test_array_pop(capsys):
    run_src("let a = [1, 2, 3]; print(pop(a)); print(a);")
    assert capsys.readouterr().out == "3\n[1, 2]\n"


def test_array_pop_empty():
    with pytest.raises(DonkyRuntimeError):
        run_src("let a = []; pop(a);")


def test_array_push_non_array():
    with pytest.raises(DonkyRuntimeError):
        run_src("push(5, 1);")


def test_array_index_out_of_range():
    with pytest.raises(DonkyRuntimeError):
        run_src("let a = [1, 2]; print(a[5]);")


def test_array_negative_index():
    with pytest.raises(DonkyRuntimeError):
        run_src("let a = [1, 2]; print(a[-1]);")


def test_array_index_non_int():
    with pytest.raises(DonkyRuntimeError):
        run_src("let a = [1, 2]; print(a[0.5]);")


def test_array_index_non_array():
    with pytest.raises(DonkyRuntimeError):
        run_src("let x = 5; print(x[0]);")


def test_array_index_set_out_of_range():
    with pytest.raises(DonkyRuntimeError):
        run_src("let a = [1]; a[5] = 0;")


def test_array_nested(capsys):
    run_src("let m = [[1, 2], [3, 4]]; print(m[1][0]);")
    assert capsys.readouterr().out == "3\n"


def test_array_type(capsys):
    run_src("print(type([1]));")
    assert capsys.readouterr().out == "array\n"


def test_array_loop_sum(capsys):
    run_src(
        "let a = [1, 2, 3, 4];"
        "let s = 0; let i = 0;"
        "while i < len(a) { s = s + a[i]; i = i + 1; }"
        "print(s);"
    )
    assert capsys.readouterr().out == "10\n"
    
# ---------- Session 6: closures (interpreter already supports these) ----------

def test_closure_counter(capsys):
    run_src(
        "fn make_counter() -> any {"
        "  let n = 0;"
        "  fn inc() -> num { n = n + 1; return n; }"
        "  return inc;"
        "}"
        "let c = make_counter();"
        "print(c()); print(c()); print(c());"
    )
    assert capsys.readouterr().out == "1\n2\n3\n"


def test_closure_independent_counters(capsys):
    run_src(
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
    assert capsys.readouterr().out == "1\n3\n"


def test_closure_multi_level(capsys):
    run_src(
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
    assert capsys.readouterr().out == "11\n"

# ---------- Session 9: input / sort / break / continue ----------

def test_input_returns_string(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda prompt='': "hello")
    run_src('let x = input(""); print(x);')
    assert capsys.readouterr().out == "hello\n"


def test_input_no_prompt(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda prompt='': "world")
    run_src('print(input());')
    assert capsys.readouterr().out == "world\n"


def test_input_eof(monkeypatch):
    def raise_eof(prompt=''):
        raise EOFError()
    monkeypatch.setattr('builtins.input', raise_eof)
    with pytest.raises(DonkyRuntimeError):
        run_src('print(input(""));')


def test_input_type(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda prompt='': "42")
    run_src('print(type(input()));')
    assert capsys.readouterr().out == "string\n"


def test_sort_numbers(capsys):
    run_src("let a = [3, 1, 2]; sort(a); print(a);")
    assert capsys.readouterr().out == "[1, 2, 3]\n"


def test_sort_strings(capsys):
    run_src('let a = ["charlie", "alice", "bob"]; sort(a); print(a);')
    assert capsys.readouterr().out == "[alice, bob, charlie]\n"


def test_sort_mixed_ints_floats(capsys):
    run_src("let a = [3.5, 1, 2.0]; sort(a); print(a);")
    assert capsys.readouterr().out == "[1, 2.0, 3.5]\n"


def test_sort_empty(capsys):
    run_src("let a = []; sort(a); print(a);")
    assert capsys.readouterr().out == "[]\n"


def test_sort_single(capsys):
    run_src("let a = [5]; sort(a); print(a);")
    assert capsys.readouterr().out == "[5]\n"


def test_sort_mixed_types_errors():
    with pytest.raises(DonkyRuntimeError):
        run_src('let a = [1, "a"]; sort(a);')


def test_sort_bool_number_errors():
    with pytest.raises(DonkyRuntimeError):
        run_src("let a = [1, true]; sort(a);")


def test_sort_non_array():
    with pytest.raises(DonkyRuntimeError):
        run_src("sort(5);")


def test_break_basic(capsys):
    run_src(
        "let i = 0;"
        "while true {"
        "  if i == 3 { break; }"
        "  print(i);"
        "  i = i + 1;"
        "}"
    )
    assert capsys.readouterr().out == "0\n1\n2\n"


def test_continue_basic(capsys):
    run_src(
        "let i = 0;"
        "while i < 5 {"
        "  i = i + 1;"
        "  if i == 3 { continue; }"
        "  print(i);"
        "}"
    )
    assert capsys.readouterr().out == "1\n2\n4\n5\n"


def test_break_nested_if(capsys):
    run_src(
        "let i = 0;"
        "while i < 10 {"
        "  if i == 5 {"
        "    if true {"
        "      break;"
        "    }"
        "  }"
        "  i = i + 1;"
        "}"
        "print(i);"
    )
    assert capsys.readouterr().out == "5\n"


def test_continue_skips_rest(capsys):
    run_src(
        "let i = 0;"
        "while i < 3 {"
        "  i = i + 1;"
        "  continue;"
        "  print(\"never\");"
        "}"
        "print(i);"
    )
    assert capsys.readouterr().out == "3\n"


def test_break_inside_function_errors():
    with pytest.raises(Exception):
        run_src("fn f() -> void { break; }")


def test_continue_inside_function_errors():
    with pytest.raises(Exception):
        run_src("fn f() -> void { continue; }")


def test_break_at_top_errors():
    with pytest.raises(Exception):
        run_src("break;")


def test_break_finds_early(capsys):
    run_src(
        "let nums = [4, 7, 10, 15, 22];"
        "let i = 0;"
        "let found = -1;"
        "while i < len(nums) {"
        "  if nums[i] > 10 { found = nums[i]; break; }"
        "  i = i + 1;"
        "}"
        "print(found);"
    )
    assert capsys.readouterr().out == "15\n"

# ---------- Session 10: try/catch ----------

def test_try_no_error(capsys):
    run_src('try { print("ok"); } catch e { print("caught"); }')
    assert capsys.readouterr().out == "ok\n"


def test_try_catches_error(capsys):
    run_src('try { let x = 1 / 0; } catch e { print(e); }')
    assert capsys.readouterr().out == "division by zero\n"


def test_throw_caught(capsys):
    run_src('try { throw "boom"; } catch e { print(e); }')
    assert capsys.readouterr().out == "boom\n"


def test_throw_uncaught():
    with pytest.raises(DonkyRuntimeError):
        run_src('throw "boom";')


def test_error_in_handler_propagates():
    with pytest.raises(DonkyRuntimeError):
        run_src('try { let x = 1 / 0; } catch e { let y = 1 / 0; }')


def test_return_through_try(capsys):
    run_src(
        'fn f() -> num {'
        '  try { return 1; } catch e { return 2; }'
        '}'
        'print(f());'
    )
    assert capsys.readouterr().out == "1\n"


def test_break_through_try(capsys):
    run_src(
        'let i = 0;'
        'while true {'
        '  try { break; } catch e { print("caught"); }'
        '  i = i + 1;'
        '}'
        'print(i);'
    )
    assert capsys.readouterr().out == "0\n"


def test_try_nested(capsys):
    run_src(
        'try {'
        '  try { throw "inner"; } catch e { throw "outer: " + e; }'
        '} catch e { print(e); }'
    )
    assert capsys.readouterr().out == "outer: inner\n"


# ---------- Session 10: maps ----------

def test_map_literal(capsys):
    run_src('print({"a": 1, "b": 2});')
    out = capsys.readouterr().out
    assert "a: 1" in out and "b: 2" in out


def test_map_empty(capsys):
    run_src("print({});")
    assert capsys.readouterr().out == "{}\n"


def test_map_get(capsys):
    run_src('let m = {"x": 42}; print(m["x"]);')
    assert capsys.readouterr().out == "42\n"


def test_map_set(capsys):
    run_src('let m = {}; m["a"] = 1; print(m["a"]);')
    assert capsys.readouterr().out == "1\n"


def test_map_missing_key():
    with pytest.raises(DonkyRuntimeError):
        run_src('let m = {"a": 1}; print(m["z"]);')


def test_map_int_keys(capsys):
    run_src('let m = {1: "one", 2: "two"}; print(m[1]);')
    assert capsys.readouterr().out == "one\n"


def test_map_len(capsys):
    run_src('print(len({"a": 1, "b": 2, "c": 3}));')
    assert capsys.readouterr().out == "3\n"


def test_map_keys(capsys):
    run_src('print(keys({"a": 1, "b": 2}));')
    assert capsys.readouterr().out == "[a, b]\n"


def test_map_contains(capsys):
    run_src('let m = {"a": 1}; print(contains(m, "a")); print(contains(m, "z"));')
    assert capsys.readouterr().out == "true\nfalse\n"


def test_map_type(capsys):
    run_src('print(type({}));')
    assert capsys.readouterr().out == "map\n"


# ---------- Session 10: for loop ----------

def test_for_array(capsys):
    run_src('for x in [1, 2, 3] { print(x); }')
    assert capsys.readouterr().out == "1\n2\n3\n"


def test_for_string(capsys):
    run_src('for c in "abc" { print(c); }')
    assert capsys.readouterr().out == "a\nb\nc\n"


def test_for_map(capsys):
    run_src('for k in {"a": 1, "b": 2} { print(k); }')
    assert capsys.readouterr().out == "a\nb\n"


def test_for_empty(capsys):
    run_src('for x in [] { print(x); } print("done");')
    assert capsys.readouterr().out == "done\n"


def test_for_break(capsys):
    run_src(
        'for x in [1, 2, 3, 4, 5] {'
        '  if x > 3 { break; }'
        '  print(x);'
        '}'
    )
    assert capsys.readouterr().out == "1\n2\n3\n"


def test_for_continue(capsys):
    run_src(
        'for x in [1, 2, 3, 4, 5] {'
        '  if x % 2 == 0 { continue; }'
        '  print(x);'
        '}'
    )
    assert capsys.readouterr().out == "1\n3\n5\n"


def test_for_nested(capsys):
    run_src('for i in [1, 2] { for j in [10, 20] { print(str(i) + "-" + str(j)); } }')
    assert capsys.readouterr().out == "1-10\n1-20\n2-10\n2-20\n"


def test_for_non_iterable():
    with pytest.raises(DonkyRuntimeError):
        run_src("for x in 5 { print(x); }")


def test_for_break_inside_try(capsys):
    run_src(
        'for x in [1, 2, 3] {'
        '  try { if x == 2 { break; } } catch e { }'
        '  print(x);'
        '}'
        'print("done");'
    )
    assert capsys.readouterr().out == "1\ndone\n"

def test_else_if_first(capsys):
    run_src('if true { print("a"); } else if true { print("b"); }')
    assert capsys.readouterr().out == "a\n"


def test_else_if_second(capsys):
    run_src('if false { print("a"); } else if true { print("b"); }')
    assert capsys.readouterr().out == "b\n"


def test_else_if_chain_third(capsys):
    run_src(
        'let x = 3;'
        'if x == 1 { print("one"); }'
        'else if x == 2 { print("two"); }'
        'else if x == 3 { print("three"); }'
        'else { print("other"); }'
    )
    assert capsys.readouterr().out == "three\n"


def test_else_if_fallthrough(capsys):
    run_src(
        'let x = 99;'
        'if x == 1 { print("one"); }'
        'else if x == 2 { print("two"); }'
        'else { print("other"); }'
    )
    assert capsys.readouterr().out == "other\n"

def test_import_function(tmp_path, capsys):
    (tmp_path / "lib.donk").write_text(
        "fn double(n) -> num { return n * 2; }", encoding="utf-8"
    )
    import os
    from donky import modules
    from donky.interpreter import Interpreter
    src = 'import "lib.donk"; print(double(5));'
    prog = Parser(Lexer(src).tokenize()).parse()
    prog = modules.expand(prog, str(tmp_path))
    Interpreter().run(prog)
    assert capsys.readouterr().out == "10\n"