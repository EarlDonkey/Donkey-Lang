from __future__ import annotations
from dataclasses import dataclass

from donky import ast_nodes as ast
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


def is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def type_name(v: object) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, Function):
        return "function"
    return type(v).__name__


def format_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Function):
        return f"<fn {v.name}>"
    return str(v)