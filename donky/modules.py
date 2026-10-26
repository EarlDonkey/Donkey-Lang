import os

from donky import ast_nodes as ast
from donky.errors import DonkyRuntimeError
from donky.lexer import Lexer
from donky.parser import Parser, ParseError


def expand(program: ast.Program, base_dir: str, seen: set[str] | None = None) -> ast.Program:
    """Replace ImportStmt nodes at program top-level with the parsed+expanded
    statements of the imported files. Path resolution is relative to base_dir.
    Duplicate imports (by absolute path) are skipped."""
    if seen is None:
        seen = set()

    new_stmts: list[ast.Stmt] = []
    for stmt in program.stmts:
        if isinstance(stmt, ast.ImportStmt):
            path = os.path.abspath(os.path.join(base_dir, stmt.path))
            if path in seen:
                continue
            seen.add(path)
            try:
                with open(path, encoding="utf-8-sig") as f:
                    src = f.read()
            except OSError as e:
                raise DonkyRuntimeError(
                    f"cannot import {stmt.path!r}: {e.strerror or e}",
                    stmt.line, stmt.col,
                )
            try:
                toks = Lexer(src).tokenize()
                sub = Parser(toks).parse()
            except (Exception,) as e:
                msg = getattr(e, "args", [str(e)])[0]
                raise DonkyRuntimeError(
                    f"error importing {stmt.path!r}: {msg}",
                    stmt.line, stmt.col,
                ) from e
            sub_dir = os.path.dirname(path)
            expanded = expand(sub, sub_dir, seen)
            new_stmts.extend(expanded.stmts)
        else:
            new_stmts.append(stmt)
    return ast.Program(new_stmts, program.line, program.col)