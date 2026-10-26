from donky.repl import _brace_delta


def test_brace_delta_balanced():
    assert _brace_delta("if x { }") == 0


def test_brace_delta_open():
    assert _brace_delta("if x {") == 1


def test_brace_delta_close():
    assert _brace_delta("}") == -1


def test_brace_delta_nested():
    assert _brace_delta("fn f() { if x { } }") == 0


def test_brace_delta_ignores_strings():
    assert _brace_delta('print("{ }")') == 0


def test_brace_delta_ignores_comments():
    assert _brace_delta("{ // } ") == 1


def test_brace_delta_escaped_quote():
    assert _brace_delta(r'print("\"{")') == 0

from donky.interpreter import Interpreter
from donky.repl import _report


def test_repl_import(tmp_path, capsys):
    (tmp_path / "mymod.donk").write_text(
        "fn double(n) -> num { return n * 2; }", encoding="utf-8"
    )
    interp = Interpreter()
    seen: set[str] = set()
    _report('import "mymod.donk";', interp, str(tmp_path), seen)
    assert len(seen) == 1
    _report('print(double(5));', interp, str(tmp_path), seen)
    assert capsys.readouterr().out == "10\n"


def test_repl_import_without_semicolon(tmp_path, capsys):
    (tmp_path / "mymod.donk").write_text(
        "fn triple(n) -> num { return n * 3; }", encoding="utf-8"
    )
    interp = Interpreter()
    seen: set[str] = set()
    _report('import "mymod.donk"', interp, str(tmp_path), seen)
    assert len(seen) == 1
    _report('print(triple(4));', interp, str(tmp_path), seen)
    assert capsys.readouterr().out == "12\n"


def test_repl_import_idempotent(tmp_path):
    (tmp_path / "mymod.donk").write_text(
        "fn f() -> num { return 1; }", encoding="utf-8"
    )
    interp = Interpreter()
    seen: set[str] = set()
    _report('import "mymod.donk";', interp, str(tmp_path), seen)
    _report('import "mymod.donk";', interp, str(tmp_path), seen)
    assert len(seen) == 1


def test_repl_import_missing_errors(tmp_path, capsys):
    interp = Interpreter()
    seen: set[str] = set()
    _report('import "nope.donk";', interp, str(tmp_path), seen)
    err = capsys.readouterr().err
    assert "cannot import" in err
    assert len(seen) == 0  # failed import doesn't pollute seen