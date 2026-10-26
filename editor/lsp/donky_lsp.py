"""Donky language server — diagnostics, completion, and hover."""

import logging
import os
import re
import sys
from urllib.parse import unquote, urlparse

from lsprotocol import types
from pygls.lsp.server import LanguageServer

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from donky import ast_nodes as ast  # noqa: E402
from donky import modules, typecheck  # noqa: E402
from donky.errors import DonkyRuntimeError  # noqa: E402
from donky.lexer import LexError, Lexer  # noqa: E402
from donky.parser import ParseError, Parser  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("donky-lsp")

server = LanguageServer("donky-lsp", "0.3.0")

_ERROR_PREFIXES = (
    "lex error:", "parse error:", "runtime error:",
    "compile error:", "type error:",
)

KEYWORDS = [
    "let", "fn", "if", "else", "while", "for", "in", "return",
    "break", "continue", "try", "catch", "throw", "import",
    "print", "div", "true", "false",
]

BUILTINS = {
    "len": "fn len(x: any) -> number",
    "str": "fn str(x: any) -> string",
    "num": "fn num(x: any) -> number",
    "type": "fn type(x: any) -> string",
    "push": "fn push(arr: array, val: any) -> void",
    "pop": "fn pop(arr: array) -> any",
    "read_file": "fn read_file(path: string) -> string",
    "write_file": "fn write_file(path: string, content: string) -> void",
    "file_exists": "fn file_exists(path: string) -> bool",
    "split": "fn split(s: string, sep: string) -> array",
    "join": "fn join(arr: array, sep: string) -> string",
    "contains": "fn contains(container: any, item: any) -> bool",
    "keys": "fn keys(m: map) -> array",
    "upper": "fn upper(s: string) -> string",
    "lower": "fn lower(s: string) -> string",
    "trim": "fn trim(s: string) -> string",
    "replace": "fn replace(s: string, old: string, new: string) -> string",
    "input": "fn input(prompt: string) -> string",
    "sort": "fn sort(arr: array) -> void",
}

# ---------------------------------------------------------------- helpers

def _clean_message(text: str) -> str:
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
    ln = max(0, line - 1)
    ch = max(0, col - 1)
    return types.Range(
        start=types.Position(line=ln, character=ch),
        end=types.Position(line=ln, character=ch + max(1, length)),
    )


def _diag(message: str, line: int, col: int, length: int = 1) -> types.Diagnostic:
    return types.Diagnostic(
        message=message,
        severity=types.DiagnosticSeverity.Error,
        range=_range(line, col, length),
        source="donky",
    )


def _parse(uri: str, text: str):
    """Helper to get the expanded AST. Returns None if parsing fails."""
    try:
        tokens = Lexer(text).tokenize()
        program = Parser(tokens).parse()
        path = unquote(urlparse(uri).path)
        base_dir = os.path.dirname(path) if path else os.getcwd()
        return modules.expand(program, base_dir)
    except Exception:
        return None

# ------------------------------------------------------------ diagnostics

def validate(uri: str, text: str) -> list[types.Diagnostic]:
    try:
        return _validate_inner(uri, text)
    except Exception as exc:
        log.exception("internal error while validating %s", uri)
        return [_diag(f"internal error: {exc}", 1, 1)]

def _validate_inner(uri: str, text: str) -> list[types.Diagnostic]:
    try:
        tokens = Lexer(text).tokenize()
    except LexError as exc:
        return [_diag(_clean_message(str(exc)), exc.line, exc.col)]

    try:
        program = Parser(tokens).parse()
    except ParseError as exc:
        return [_diag(_clean_message(str(exc)), exc.tok.line, exc.tok.col)]

    path = unquote(urlparse(uri).path)
    base_dir = os.path.dirname(path) if path else os.getcwd()
    try:
        program = modules.expand(program, base_dir)
    except DonkyRuntimeError as exc:
        return [_diag(_clean_message(str(exc)), exc.line or 1, exc.col or 1)]

    diagnostics = []
    try:
        typecheck.check(program)
    except typecheck.TypeCheckError as exc:
        diagnostics.append(_diag(_clean_message(str(exc)), exc.line, exc.col))
    except Exception as exc:
        log.exception("type checker crashed on %s", uri)
        diagnostics.append(_diag(f"type checker error: {exc}", 1, 1))

    return diagnostics


# ---------------------------------------------------------- AST Traversal

def _find_scope_symbols(program: ast.Program, target_line: int, target_col: int) -> dict[str, str]:
    """Walk the AST up to the target position and collect all visible variables."""
    symbols = {}
    
    # Add builtins and keywords as functions/objects
    for name, sig in BUILTINS.items():
        symbols[name] = sig
    symbols["args"] = "array"

    def walk_stmt(node, scope):
        if getattr(node, "line", 0) > target_line:
            return
        
        if isinstance(node, ast.LetStmt):
            scope[node.name] = f"let {node.name}: any"
        elif isinstance(node, ast.FnStmt):
            params = ", ".join(node.params)
            scope[node.name] = f"fn {node.name}({params}) -> {node.return_type}"
        
        # Recurse into blocks
        if isinstance(node, (ast.IfStmt, ast.WhileStmt)):
            walk_block(node.then, scope, target_line, target_col)
            if getattr(node, "else_", None):
                walk_block(node.else_, scope, target_line, target_col)
        elif isinstance(node, ast.ForStmt):
            scope[node.var_name] = "let " + node.var_name + ": any"
            walk_block(node.body, scope, target_line, target_col)
        elif isinstance(node, ast.TryStmt):
            walk_block(node.body, scope, target_line, target_col)
            scope[node.err_name] = "let " + node.err_name + ": string"
            walk_block(node.handler, scope, target_line, target_col)
        elif isinstance(node, ast.Block):
            walk_block(node, scope, target_line, target_col)
        elif isinstance(node, ast.FnStmt):
            inner_scope = dict(scope)
            for p in node.params:
                inner_scope[p] = f"let {p}: any"
            walk_block(node.body, inner_scope, target_line, target_col)

    def walk_block(block, scope, t_line, t_col):
        # Shallow copy to preserve parent scope, but allow local shadowing
        local_scope = dict(scope)
        for s in block.stmts:
            walk_stmt(s, local_scope)

    global_scope = {}
    for stmt in program.stmts:
        walk_stmt(stmt, global_scope)
        
    return global_scope


def _find_node_at(program: ast.Program, line: int, col: int):
    """Find the AST node at the exact line/col."""
    found = None
    
    def walk(node):
        nonlocal found
        if found: return
        if not hasattr(node, "line"): return
        
        n_line, n_col = node.line, node.col
        # If the node starts after our cursor, skip
        if n_line > line or (n_line == line and n_col > col):
            return

        # Check if the cursor is on an Ident or Call
        if isinstance(node, ast.Ident):
            if n_line == line and n_col <= col <= n_col + len(node.name):
                found = node
                return
        elif isinstance(node, ast.Call):
            if n_line == line and n_col <= col <= n_col + len(node.callee):
                found = node
                return
        
        # Recursively visit children
        if isinstance(node, ast.Program):
            for s in node.stmts: walk(s)
        elif isinstance(node, ast.Block):
            for s in node.stmts: walk(s)
        elif isinstance(node, ast.ExprStmt): walk(node.expr)
        elif isinstance(node, ast.LetStmt): walk(node.value)
        elif isinstance(node, ast.PrintStmt): walk(node.value)
        elif isinstance(node, ast.IfStmt):
            walk(node.cond)
            walk(node.then)
            if node.else_: walk(node.else_)
        elif isinstance(node, ast.WhileStmt):
            walk(node.cond)
            walk(node.body)
        elif isinstance(node, ast.ForStmt):
            walk(node.iter_expr)
            walk(node.body)
        elif isinstance(node, ast.FnStmt): walk(node.body)
        elif isinstance(node, ast.ReturnStmt):
            if node.value: walk(node.value)
        elif isinstance(node, ast.Binary):
            walk(node.left); walk(node.right)
        elif isinstance(node, ast.Unary): walk(node.operand)
        elif isinstance(node, ast.Assign): walk(node.value)
        elif isinstance(node, ast.Call):
            for a in node.args: walk(a)
        elif isinstance(node, ast.ArrayLit):
            for e in node.elems: walk(e)
        elif isinstance(node, ast.MapLit):
            for k, v in node.entries:
                walk(k); walk(v)
        elif isinstance(node, ast.Index):
            walk(node.array); walk(node.index)
        elif isinstance(node, ast.IndexSet):
            walk(node.index); walk(node.value)
        elif isinstance(node, ast.ThrowStmt): walk(node.value)
        elif isinstance(node, ast.InterpolatedString):
            for p in node.parts:
                if not isinstance(p, str):
                    walk(p)

    walk(program)
    return found


# ---------------------------------------------------------------- features

@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params: types.HoverParams) -> types.Hover | None:
    uri = params.text_document.uri
    doc = ls.workspace.get_text_document(uri)
    program = _parse(uri, doc.source)
    if not program:
        return None

    line = params.position.line + 1
    col = params.position.character + 1
    
    node = _find_node_at(program, line, col)
    if not node:
        return None

    name = node.name if isinstance(node, ast.Ident) else node.callee
    
    # 1. Check builtins first
    if name in BUILTINS:
        return types.Hover(contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value=f"```donky\n{BUILTINS[name]}\n```"
        ))

    # 2. Look up in scope
    symbols = _find_scope_symbols(program, line, col)
    if name in symbols:
        return types.Hover(contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value=f"```donky\n{symbols[name]}\n```"
        ))

    return None


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def completion(ls: LanguageServer, params: types.CompletionParams) -> types.CompletionList:
    uri = params.text_document.uri
    doc = ls.workspace.get_text_document(uri)
    
    # If the file doesn't parse yet, we still want to offer keywords!
    program = _parse(uri, doc.source)
    
    items = []
    
    # 1. Keywords
    for kw in KEYWORDS:
        items.append(types.CompletionItem(
            label=kw, kind=types.CompletionItemKind.Keyword
        ))
        
    # 2. Scope symbols (if it parses)
    if program:
        line = params.position.line + 1
        col = params.position.character + 1
        symbols = _find_scope_symbols(program, line, col)
        for name, sig in symbols.items():
            kind = types.CompletionItemKind.Function if sig.startswith("fn") else types.CompletionItemKind.Variable
            items.append(types.CompletionItem(
                label=name,
                kind=kind,
                detail=sig
            ))

    # VS Code automatically filters items based on what the user typed,
    # so we can just return the whole list.
    return types.CompletionList(is_incomplete=False, items=items)

# ---------------------------------------------------------- Navigation

def _find_definition(program: ast.Program, name: str, current_uri: str, base_dir: str):
    """Walk the AST looking for the definition. Returns (uri, node)."""
    found = None
    
    def walk(node):
        nonlocal found
        if found: return
        
        if isinstance(node, ast.LetStmt) and node.name == name:
            found = node
        elif isinstance(node, ast.FnStmt) and node.name == name:
            found = node
        
        # Recurse into blocks
        if isinstance(node, ast.Program):
            for s in node.stmts: walk(s)
        elif isinstance(node, ast.Block):
            for s in node.stmts: walk(s)
        elif isinstance(node, ast.IfStmt):
            walk(node.then)
            if node.else_: walk(node.else_)
        elif isinstance(node, ast.WhileStmt):
            walk(node.body)
        elif isinstance(node, ast.ForStmt):
            walk(node.body)
        elif isinstance(node, ast.FnStmt):
            walk(node.body)
        elif isinstance(node, ast.TryStmt):
            walk(node.body)
            walk(node.handler)

    walk(program)
    return found


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
def definition(ls: LanguageServer, params: types.DefinitionParams) -> types.Location | None:
    uri = params.text_document.uri
    doc = ls.workspace.get_text_document(uri)
    
    # We need the unexpanded program to find which module it came from
    try:
        tokens = Lexer(doc.source).tokenize()
        raw_program = Parser(tokens).parse()
    except Exception:
        return None

    path = unquote(urlparse(uri).path)
    base_dir = os.path.dirname(path) if path else os.getcwd()
    
    # Check local scope first
    line = params.position.line + 1
    col = params.position.character + 1
    
    local_node = _find_node_at(raw_program, line, col)
    if not local_node:
        return None

    name = local_node.name if isinstance(local_node, ast.Ident) else local_node.callee
    
    # Look in the current file
    defn = _find_definition(raw_program, name, uri, base_dir)
    target_uri = uri
    
    if not defn:
        # Not in current file. Check imports.
        for stmt in raw_program.stmts:
            if isinstance(stmt, ast.ImportStmt):
                import_path = os.path.abspath(os.path.join(base_dir, stmt.path))
                if os.path.exists(import_path):
                    import_uri = "file:///" + import_path.replace("\\", "/")
                    if import_uri.startswith("file:////"):
                        import_uri = import_uri.replace("file:////", "file:///")
                    
                    import_doc = ls.workspace.get_text_document(import_uri)
                    if import_doc:
                        try:
                            imp_toks = Lexer(import_doc.source).tokenize()
                            imp_prog = Parser(imp_toks).parse()
                            defn = _find_definition(imp_prog, name, import_uri, base_dir)
                            if defn:
                                target_uri = import_uri
                                break
                        except Exception:
                            pass

    if defn:
        return types.Location(
            uri=target_uri,
            range=_range(defn.line, defn.col, len(name))
        )
    return None


# ------------------------------------------------------------- lifecycle

def _publish(ls: LanguageServer, uri: str, version: int | None) -> None:
    doc = ls.workspace.get_text_document(uri)
    diagnostics = validate(uri, doc.source)
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=uri, version=version, diagnostics=diagnostics
        )
    )

@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams) -> None:
    _publish(ls, params.text_document.uri, params.text_document.version)

@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams) -> None:
    _publish(ls, params.text_document.uri, params.text_document.version)

@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: LanguageServer, params: types.DidCloseTextDocumentParams) -> None:
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(uri=params.text_document.uri, diagnostics=[])
    )

if __name__ == "__main__":
    server.start_io()