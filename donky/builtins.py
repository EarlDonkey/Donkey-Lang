from donky.errors import DonkyRuntimeError
from donky.values import (
    Builtin, Environment, format_value, is_number, type_name,
)


def _len(args: list[object]) -> object:
    v = args[0]
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return len(v)
    raise DonkyRuntimeError(
        f"len() expects string or array, got {type_name(v)}"
    )


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


def _push(args: list[object]) -> object:
    arr, val = args
    if not isinstance(arr, list):
        raise DonkyRuntimeError(
            f"push() expects array as first argument, got {type_name(arr)}"
        )
    arr.append(val)
    return None


def _pop(args: list[object]) -> object:
    arr = args[0]
    if not isinstance(arr, list):
        raise DonkyRuntimeError(
            f"pop() expects array, got {type_name(arr)}"
        )
    if not arr:
        raise DonkyRuntimeError("pop() from empty array")
    return arr.pop()


BUILTINS = [
    ("len",  1, _len),
    ("str",  1, _str),
    ("num",  1, _num),
    ("type", 1, _type),
    ("push", 2, _push),
    ("pop",  1, _pop),
]


def install_builtins(env: Environment) -> None:
    for name, arity, impl in BUILTINS:
        env.define(name, Builtin(name, arity, impl))