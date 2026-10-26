import os
import pytest

from donky import modules
from donky.ast_nodes import ImportStmt
from donky.lexer import Lexer
from donky.parser import Parser


def parse_and_expand(src: str, base_dir: str):
    prog = Parser(Lexer(src).tokenize()).parse()
    return modules.expand(prog, base_dir)


def test_no_imports_passthrough():
    prog = parse_and_expand("let x = 1;", ".")
    assert len(prog.stmts) == 1
    assert not isinstance(prog.stmts[0], ImportStmt)


def test_import_inlines(tmp_path):
    (tmp_path / "lib.donk").write_text("let y = 5;", encoding="utf-8")
    prog = parse_and_expand('import "lib.donk";', str(tmp_path))
    assert len(prog.stmts) == 1
    assert not isinstance(prog.stmts[0], ImportStmt)


def test_duplicate_import_skipped(tmp_path):
    (tmp_path / "lib.donk").write_text("let y = 5;", encoding="utf-8")
    prog = parse_and_expand(
        'import "lib.donk";\nimport "lib.donk";', str(tmp_path)
    )
    assert len(prog.stmts) == 1


def test_cycle_terminates(tmp_path):
    (tmp_path / "a.donk").write_text('import "b.donk"; let a = 1;', encoding="utf-8")
    (tmp_path / "b.donk").write_text('import "a.donk"; let b = 2;', encoding="utf-8")
    prog = parse_and_expand('import "a.donk";', str(tmp_path))
    assert len(prog.stmts) == 2


def test_missing_import_errors(tmp_path):
    from donky.errors import DonkyRuntimeError
    with pytest.raises(DonkyRuntimeError):
        parse_and_expand('import "nope.donk";', str(tmp_path))