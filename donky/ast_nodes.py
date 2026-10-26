from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


# ---------- expressions ----------

@dataclass
class NumberLit:
    value: int | float
    line: int = 0
    col: int = 0

@dataclass
class StringLit:
    value: str
    line: int = 0
    col: int = 0

@dataclass
class BoolLit:
    value: bool
    line: int = 0
    col: int = 0

@dataclass
class Ident:
    name: str
    line: int = 0
    col: int = 0

@dataclass
class Binary:
    left: Expr
    op: str
    right: Expr
    line: int = 0
    col: int = 0

@dataclass
class Unary:
    op: str
    operand: Expr
    line: int = 0
    col: int = 0

@dataclass
class Assign:
    name: str
    value: Expr
    line: int = 0
    col: int = 0

@dataclass
class Call:
    callee: str
    args: list[Expr]
    line: int = 0
    col: int = 0

@dataclass
class ArrayLit:
    elems: list[Expr]
    line: int = 0
    col: int = 0

@dataclass
class MapLit:
    entries: list[tuple[Expr, Expr]]
    line: int = 0
    col: int = 0

@dataclass
class Index:
    array: Expr
    index: Expr
    line: int = 0
    col: int = 0

@dataclass
class FnExpr:
    params: list[str]
    return_type: str
    body: Block
    line: int = 0
    col: int = 0

@dataclass
class InterpolatedString:
    parts: list[str | Expr]
    line: int = 0
    col: int = 0

@dataclass
class StructInit:
    name: str
    fields: list[tuple[str, Expr]]
    line: int = 0
    col: int = 0

@dataclass
class FieldAccess:
    obj: Expr
    field: str
    line: int = 0
    col: int = 0


# ---------- statements ----------

@dataclass
class StructDefStmt:
    name: str
    fields: list[tuple[str, str]]
    line: int = 0
    col: int = 0

@dataclass
class LetStmt:
    name: str
    value: Expr
    line: int = 0
    col: int = 0

@dataclass
class PrintStmt:
    value: Expr
    line: int = 0
    col: int = 0

@dataclass
class ExprStmt:
    expr: Expr
    line: int = 0
    col: int = 0

@dataclass
class IfStmt:
    cond: Expr
    then: Block
    else_: Optional[Block]
    line: int = 0
    col: int = 0

@dataclass
class WhileStmt:
    cond: Expr
    body: Block
    line: int = 0
    col: int = 0

@dataclass
class ForStmt:
    var_name: str
    iter_expr: Expr
    body: Block
    line: int = 0
    col: int = 0

@dataclass
class FnStmt:
    name: str
    params: list[str]
    return_type: str
    body: Block
    line: int = 0
    col: int = 0

@dataclass
class ReturnStmt:
    value: Optional[Expr]
    line: int = 0
    col: int = 0

@dataclass
class BreakStmt:
    line: int = 0
    col: int = 0

@dataclass
class ContinueStmt:
    line: int = 0
    col: int = 0

@dataclass
class TryStmt:
    body: Block
    err_name: str
    handler: Block
    line: int = 0
    col: int = 0

@dataclass
class ThrowStmt:
    value: Expr
    line: int = 0
    col: int = 0

@dataclass
class ImportStmt:
    path: str
    line: int = 0
    col: int = 0

@dataclass
class Block:
    stmts: list[Stmt]
    line: int = 0
    col: int = 0

@dataclass
class IndexSet:
    array_name: str
    index: Expr
    value: Expr
    line: int = 0
    col: int = 0

@dataclass
class FieldSet:
    obj: Expr
    field: str
    value: Expr
    line: int = 0
    col: int = 0


@dataclass
class Program:
    stmts: list[Stmt]
    line: int = 0
    col: int = 0


Expr = (NumberLit | StringLit | BoolLit | Ident | Binary | Unary
        | Assign | Call | ArrayLit | MapLit | Index | FnExpr | InterpolatedString | StructInit | FieldAccess)
Stmt = (StructDefStmt | LetStmt | PrintStmt | ExprStmt | IfStmt | WhileStmt | ForStmt
        | FnStmt | ReturnStmt | Block | IndexSet | BreakStmt | ContinueStmt
        | TryStmt | ThrowStmt | ImportStmt | FieldSet)