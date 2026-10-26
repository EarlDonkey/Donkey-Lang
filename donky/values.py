from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

from donky import ast_nodes as ast
from donky.bytecode import CodeObject
from donky.errors import DonkyRuntimeError


class Environment:
    def __init__(self, parent: Environment | None = None):
        self.vars: dict[str, object] = {}
        self.parent = parent

    def define(self, name: str, value: object) -> None:
        self.vars[name] = value

    def get(self, name: str) -> object:
        env: Environment | None = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise DonkyRuntimeError(f"undefined variable '{name}'")

    def assign(self, name: str, value: object) -> None:
        env: Environment | None = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        raise DonkyRuntimeError(f"assignment to undefined variable '{name}'")


@dataclass
class Function:
    name: str
    params: list[str]
    body: ast.Block
    closure: Environment
    return_type: str


@dataclass
class Builtin:
    name: str
    arity: int
    impl: Callable[[list[object]], object]
    max_arity: int | None = None


class Cell:
    __slots__ = ("value",)

    def __init__(self, value: object = None):
        self.value = value

    def __repr__(self) -> str:
        return f"Cell({self.value!r})"


@dataclass
class Closure:
    code: CodeObject
    upvalues: list[Cell] = field(default_factory=list)


def is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def type_name(v: object) -> str:
    if v is None: return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "map"
    if isinstance(v, (Function, Builtin, Closure, CodeObject)):
        return "function"
    return type(v).__name__


def format_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Function):
        return f"<fn {v.name}>"
    if isinstance(v, Builtin):
        return f"<builtin {v.name}>"
    if isinstance(v, Closure):
        return f"<fn {v.code.name}>"
    if isinstance(v, CodeObject):
        return f"<fn {v.name}>"
    if isinstance(v, list):
        return "[" + ", ".join(format_value(e) for e in v) + "]"
    if isinstance(v, dict):
        parts = [f"{format_value(k)}: {format_value(val)}" for k, val in v.items()]
        return "{" + ", ".join(parts) + "}"
    return str(v)