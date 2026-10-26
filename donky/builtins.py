import os

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


def _read_file(args: list[object]) -> object:
    path = args[0]
    if not isinstance(path, str):
        raise DonkyRuntimeError(
            f"read_file() expects string path, got {type_name(path)}"
        )
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except OSError as e:
        raise DonkyRuntimeError(
            f"read_file: cannot open {path!r}: {e.strerror or e}"
        )


def _write_file(args: list[object]) -> object:
    path, content = args
    if not isinstance(path, str):
        raise DonkyRuntimeError(
            f"write_file() expects string path, got {type_name(path)}"
        )
    if not isinstance(content, str):
        raise DonkyRuntimeError(
            f"write_file() expects string content, got {type_name(content)}"
        )
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
    except OSError as e:
        raise DonkyRuntimeError(
            f"write_file: cannot write {path!r}: {e.strerror or e}"
        )
    return None


BUILTINS = [
    ("len",        1, _len),
    ("str",        1, _str),
    ("num",        1, _num),
    ("type",       1, _type),
    ("push",       2, _push),
    ("pop",        1, _pop),
    ("read_file",  1, _read_file),
    ("write_file", 2, _write_file),
]


def install_builtins(env: Environment, args: list[str] | None = None) -> None:
    for name, arity, impl in BUILTINS:
        env.define(name, Builtin(name, arity, impl))
    env.define("args", list(args) if args else [])