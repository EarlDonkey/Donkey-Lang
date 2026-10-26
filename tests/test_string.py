import pytest

from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser


def run_src(src: str) -> None:
    prog = Parser(Lexer(src).tokenize()).parse()
    Interpreter().run(prog)


def test_string_index(capsys):
    run_src('print("hello"[0]);')
    assert capsys.readouterr().out == "h\n"


def test_string_index_last(capsys):
    run_src('let s = "hello"; print(s[4]);')
    assert capsys.readouterr().out == "o\n"


def test_string_index_out_of_range():
    with pytest.raises(DonkyRuntimeError):
        run_src('print("hi"[5]);')


def test_string_negative_index():
    with pytest.raises(DonkyRuntimeError):
        run_src('print("hi"[-1]);')


def test_string_len_still_works(capsys):
    run_src('print(len("hello"));')
    assert capsys.readouterr().out == "5\n"


def test_string_index_loop(capsys):
    run_src(
        'let s = "abc";'
        'let i = 0;'
        'while i < len(s) { print(s[i]); i = i + 1; }'
    )
    assert capsys.readouterr().out == "a\nb\nc\n"


def test_string_index_set_errors():
    with pytest.raises(DonkyRuntimeError):
        run_src('let s = "abc"; s[0] = "x";')


def test_split(capsys):
    run_src('print(split("a,b,c", ","));')
    assert capsys.readouterr().out == "[a, b, c]\n"


def test_split_by_space(capsys):
    run_src('print(len(split("a b c d", " ")));')
    assert capsys.readouterr().out == "4\n"


def test_split_empty_sep():
    with pytest.raises(DonkyRuntimeError):
        run_src('split("abc", "");')


def test_split_non_string():
    with pytest.raises(DonkyRuntimeError):
        run_src('split(5, ",");')


def test_join(capsys):
    run_src('print(join(["a", "b", "c"], "-"));')
    assert capsys.readouterr().out == "a-b-c\n"


def test_join_non_array():
    with pytest.raises(DonkyRuntimeError):
        run_src('join("abc", "-");')


def test_join_non_string_element():
    with pytest.raises(DonkyRuntimeError):
        run_src('join([1, 2], ",");')


def test_contains_true(capsys):
    run_src('print(contains("hello world", "world"));')
    assert capsys.readouterr().out == "true\n"


def test_contains_false(capsys):
    run_src('print(contains("hello", "xyz"));')
    assert capsys.readouterr().out == "false\n"


def test_upper(capsys):
    run_src('print(upper("hello"));')
    assert capsys.readouterr().out == "HELLO\n"


def test_lower(capsys):
    run_src('print(lower("HELLO"));')
    assert capsys.readouterr().out == "hello\n"


def test_trim(capsys):
    run_src('print(trim("  hello  "));')
    assert capsys.readouterr().out == "hello\n"


def test_replace(capsys):
    run_src('print(replace("a-b-c", "-", "+"));')
    assert capsys.readouterr().out == "a+b+c\n"


def test_replace_empty_old():
    with pytest.raises(DonkyRuntimeError):
        run_src('replace("abc", "", "x");')


def test_split_join_roundtrip(capsys):
    run_src(
        'let parts = split("a,b,c", ",");'
        'print(join(parts, "|"));'
    )
    assert capsys.readouterr().out == "a|b|c\n"