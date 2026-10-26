"""Donky language server — publish diagnostics for .donk files.

Runs the real Donky front-end (lexer, parser, module expansion, type
checker) on every document change and publishes the errors as LSP
diagnostics. No code generation, no execution.
"""

import logging
import os
import sys
from urllib.parse import unquote, urlparse

from lsprotocol import types
from pygls.lsp.server import LanguageServer

# Make the `donky` package importable no matter what cwd the client uses.
# This file lives at <repo>/editor/lsp/donky_lsp.py.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from donky import modules, typecheck  # noqa: E402
from donky.errors import DonkyRuntimeError  # noqa: E402
from donky.lexer import LexError, Lexer  # noqa: E402
from donky.parser import ParseError, Parser  # noqa: E402

# stdout is the LSP channel — logs MUST go to stderr.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("donky-lsp")

server = LanguageServer("donky-lsp", "0.2.0")

_ERROR_PREFIXES = (
    "lex error:",
    "parse error:",
    "runtime error:",
    "compile error:",
    "type error:",
)


def _clean_message(text: str) -> str:
    """Turn '[3:9] parse error: expected ;' into 'expected ;'."""
    if not text.startswith("["):
        return text
    close = text.find("]")
    if close == -1:
        return text
    rest = text[close + 1:].lstrip()
    for prefix in _ERROR_PREFIXES:
        if rest.startswith(prefix):
            return rest[len(prefix):].strip()
    return rest


def _range(line: int, col: int, length: int = 1) -> types.Range:
    """Donky is 1-based; LSP is 0-based."""
    ln = max(0, line - 1)
    ch = max(0, col - 1)
    return types.Range(
        start=types.Position(line=ln, character=ch),
        end=types.Position(line=ln, character=ch + max(1, length)),
    )


def _diag(message: str, line: int, col: int,
          severity: types.DiagnosticSeverity = types.DiagnosticSeverity.Error,
          length: int = 1) -> types.Diagnostic:
    return types.Diagnostic(
        message=message,
        severity=severity,
        range=_range(line, col, length),
        source="donky",
    )


def validate(uri: str, text: str) -> list[types.Diagnostic]:
    """Run the Donky front-end and return diagnostics for `text`."""
    try:
        return _validate_inner(uri, text)
    except Exception as exc:  # never let a bug kill the server
        log.exception("internal error while validating %s", uri)
        return [_diag(f"internal error: {exc}", 1, 1)]


def _validate_inner(uri: str, text: str) -> list[types.Diagnostic]:
    # 1. Lex
    try:
        tokens = Lexer(text).tokenize()
    except LexError as exc:
        return [_diag(_clean_message(str(exc)), exc.line, exc.col)]

    # 2. Parse
    try:
        program = Parser(tokens).parse()
    except ParseError as exc:
        return [_diag(_clean_message(str(exc)), exc.tok.line, exc.tok.col)]

    # 3. Resolve imports so the type checker sees symbols from other files.
    path = unquote(urlparse(uri).path)
    base_dir = os.path.dirname(path) if path else os.getcwd()
    try:
        program = modules.expand(program, base_dir)
    except DonkyRuntimeError as exc:
        return [_diag(_clean_message(str(exc)), exc.line or 1, exc.col or 1)]

    # 4. Type check
    diagnostics: list[types.Diagnostic] = []
    try:
        typecheck.check(program)
    except typecheck.TypeCheckError as exc:
        diagnostics.append(
            _diag(_clean_message(str(exc)), exc.line, exc.col)
        )
    except Exception as exc:
        log.exception("type checker crashed on %s", uri)
        diagnostics.append(_diag(f"type checker error: {exc}", 1, 1))

    return diagnostics


def _publish(ls: LanguageServer, uri: str, version: int | None) -> None:
    doc = ls.workspace.get_text_document(uri)
    diagnostics = validate(uri, doc.source)
    log.info("%s: %d diagnostic(s)", uri, len(diagnostics))
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=uri, version=version, diagnostics=diagnostics
        )
    )


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams) -> None:
    _publish(ls, params.text_document.uri, params.text_document.version)


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer,
               params: types.DidChangeTextDocumentParams) -> None:
    _publish(ls, params.text_document.uri, params.text_document.version)


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: LanguageServer,
              params: types.DidCloseTextDocumentParams) -> None:
    # Clear squiggles when the file closes.
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=params.text_document.uri, diagnostics=[]
        )
    )


if __name__ == "__main__":
    server.start_io()