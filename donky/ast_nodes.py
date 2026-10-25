from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------- expressions ----------

@dataclass
class NumberLit:
    value: int | float

@dataclass
class StringLit:
    value: str

@dataclass
class BoolLit:
    value: bool

@dataclass
class Ident:
    name: str

@dataclass
class Binary:
    left: Expr
    op: str          # the lexeme: "+", "-", "==", ...
    right: Expr

@dataclass
class Unary:
    op: str          # "-" or "!"
    operand: Expr

@dataclass
class Assign:
    name: str
    value: Expr

@dataclass
class Call:
    callee: str
    args: list[Expr]


# ---------- statements ----------

@dataclass
class LetStmt:
    name: str
    value: Expr

@dataclass
class PrintStmt:
    value: Expr

@dataclass
class ExprStmt:
    expr: Expr

@dataclass
class IfStmt:
    cond: Expr
    then: Block
    else_: Optional[Block]

@dataclass
class WhileStmt:
    cond: Expr
    body: Block

@dataclass
class FnStmt:
    name: str
    params: list[str]
    return_type: str
    body: Block

@dataclass
class ReturnStmt:
    value: Optional[Expr]

@dataclass
class Block:
    stmts: list[Stmt]


@dataclass
class Program:
    stmts: list[Stmt]


# type aliases — used only for readability
Expr = NumberLit | StringLit | BoolLit | Ident | Binary | Unary | Assign | Call
Stmt = LetStmt | PrintStmt | ExprStmt | IfStmt | WhileStmt | FnStmt | ReturnStmt | Block