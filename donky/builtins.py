from donky.errors import DonkyRuntimeError
from donky.values import (
    Builtin, Environment, format_value, is_number, type_name,
)


def _len(args: list[object]) -> object:
    v = args[0]
    if not isinstance(v, str):
        raise DonkyRuntimeError(f"len() expects string, got {type_name(v)}")
    return len(v)


def _str(args: list[object]) -> object:
    return format_value(args[0])


def _num(args: list[object]) -> object:
    v = args[0]
    if is_number(v):
        return v
    if isinstance(v, bool):
        raise DonkyRuntimeError("num() expects string or number, got bool")
    if not isinstance(v, str):
        raise DonkyRuntimeError(
            f"num() expects string or number, got {type_name(v)}"
        )
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        raise DonkyRuntimeError(f"num() cannot parse {v!r}")


def _type(args: list[object]) -> object:
    return type_name(args[0])


BUILTINS = [
    ("len",  1, _len),
    ("str",  1, _str),
    ("num",  1, _num),
    ("type", 1, _type),
]


def install_builtins(env: Environment) -> None:
    for name, arity, impl in BUILTINS:
        env.define(name, Builtin(name, arity, impl))