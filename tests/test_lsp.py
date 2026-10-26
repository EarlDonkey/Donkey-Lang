import os
import sys

import pytest

pytest.importorskip("pygls")
pytest.importorskip("lsprotocol")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "editor", "lsp"))

from donky_lsp import validate  # noqa: E402

URI = "file:///tmp/test.donk"


def test_valid_program_has_no_diagnostics():
    assert validate(URI, "let x = 1; print(x);") == []


def test_empty_file_has_no_diagnostics():
    assert validate(URI, "") == []


def test_lex_error_reported():
    diags = validate(URI, "let x = @;")
    assert len(diags) == 1
    assert "unexpected character" in diags[0].message


def test_parse_error_reported():
    diags = validate(URI, "let x = ;")
    assert len(diags) == 1
    assert "expected expression" in diags[0].message


def test_type_error_reported():
    diags = validate(URI, "print(nope);")
    assert len(diags) == 1
    assert "undefined variable" in diags[0].message


def test_positions_are_zero_based():
    # 'nope' starts at 1-based column 7, so LSP character 6, line 0.
    diags = validate(URI, "print(nope);")
    d = diags[0]
    assert d.range.start.line == 0
    assert d.range.start.character == 6


def test_severity_is_error():
    from lsprotocol import types
    diags = validate(URI, "print(nope);")
    assert diags[0].severity == types.DiagnosticSeverity.Error


def test_fixing_the_error_clears_diagnostics():
    assert len(validate(URI, "print(nope);")) == 1
    assert validate(URI, "print(1);") == []


def test_import_error_reported(tmp_path):
    doc = tmp_path / "main.donk"
    doc.write_text('import "nope.donk";', encoding="utf-8")
    diags = validate(doc.as_uri(), doc.read_text(encoding="utf-8"))
    assert len(diags) == 1
    assert "cannot import" in diags[0].message