import contextlib
import io

import pytest

from donky.compiler import Compiler
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser
from donky.vm import VM


def run_src(src: str, args: list[str] | None = None) -> None:
    prog = Parser(Lexer(src).tokenize()).parse()
    Interpreter(args=args).run(prog)


def test_args_empty_by_default(capsys):
    run_src('print(len(args));')
    assert capsys.readouterr().out == "0\n"


def test_args_visible(capsys):
    run_src('print(args[0]); print(args[1]);', args=["42", "hello"])
    assert capsys.readouterr().out == "42\nhello\n"


def test_args_type(capsys):
    run_src('print(type(args));', args=["a"])
    assert capsys.readouterr().out == "array\n"


def test_args_elements_are_strings(capsys):
    run_src('print(type(args[0]));', args=["42"])
    assert capsys.readouterr().out == "string\n"


def test_args_shadowable(capsys):
    run_src('let args = [1, 2, 3]; print(args[0]);', args=["x"])
    assert capsys.readouterr().out == "1\n"


def test_read_file(tmp_path, capsys):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    run_src(f'print(read_file("{p.as_posix()}"));')
    assert capsys.readouterr().out == "hello\n"


def test_read_file_missing(tmp_path):
    p = tmp_path / "nope.txt"
    with pytest.raises(DonkyRuntimeError):
        run_src(f'print(read_file("{p.as_posix()}"));')


def test_read_file_non_string():
    with pytest.raises(DonkyRuntimeError):
        run_src("read_file(5);")


def test_write_file(tmp_path, capsys):
    p = tmp_path / "out.txt"
    run_src(f'write_file("{p.as_posix()}", "abc");')
    assert capsys.readouterr().out == ""
    assert p.read_text(encoding="utf-8") == "abc"


def test_write_file_overwrites(tmp_path):
    p = tmp_path / "out.txt"
    p.write_text("old", encoding="utf-8")
    run_src(f'write_file("{p.as_posix()}", "new");')
    assert p.read_text(encoding="utf-8") == "new"


def test_write_file_invalid_dir(tmp_path):
    p = tmp_path / "no_such_dir" / "out.txt"
    with pytest.raises(DonkyRuntimeError):
        run_src(f'write_file("{p.as_posix()}", "x");')


def test_read_write_roundtrip(tmp_path, capsys):
    p = tmp_path / "rt.txt"
    run_src(f'write_file("{p.as_posix()}", "line1\\nline2");')
    run_src(f'print(read_file("{p.as_posix()}"));')
    assert capsys.readouterr().out == "line1\nline2\n"


def test_read_file_preserves_newlines(tmp_path, capsys):
    p = tmp_path / "n.txt"
    p.write_text("a\nb\nc", encoding="utf-8")
    run_src(f'print(len(read_file("{p.as_posix()}")));')
    assert capsys.readouterr().out == "5\n"


def test_args_in_vm():
    prog = Parser(Lexer('print(len(args));').tokenize()).parse()
    code = Compiler().compile(prog)
    vm = VM(args=["a", "b"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        vm.run(code)
    assert buf.getvalue() == "2\n"