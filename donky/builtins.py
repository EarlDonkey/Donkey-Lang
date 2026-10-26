import socket
import itertools
import threading
import urllib.parse
import urllib.request

from donky.errors import DonkyRuntimeError
from donky.values import (
    Builtin, Environment, format_value, is_number, type_name,
)

_socket_counter = itertools.count(1)
SOCKETS: dict[int, socket.socket] = {}

def _len(args: list[object]) -> object:
    v = args[0]
    if isinstance(v, str): return len(v)
    if isinstance(v, list): return len(v)
    if isinstance(v, dict): return len(v)
    raise DonkyRuntimeError(f"len() expects string, array, or map, got {type_name(v)}")

def _str(args: list[object]) -> object:
    return format_value(args[0])

def _num(args: list[object]) -> object:
    v = args[0]
    if is_number(v): return v
    if isinstance(v, bool):
        raise DonkyRuntimeError("num() expects string or number, got bool")
    if not isinstance(v, str):
        raise DonkyRuntimeError(f"num() expects string or number, got {type_name(v)}")
    try: return int(v)
    except ValueError: pass
    try: return float(v)
    except ValueError: raise DonkyRuntimeError(f"num() cannot parse {v!r}")

def _type(args: list[object]) -> object:
    return type_name(args[0])

def _push(args: list[object]) -> object:
    arr, val = args
    if not isinstance(arr, list):
        raise DonkyRuntimeError(f"push() expects array, got {type_name(arr)}")
    arr.append(val)
    return None

def _pop(args: list[object]) -> object:
    arr = args[0]
    if not isinstance(arr, list):
        raise DonkyRuntimeError(f"pop() expects array, got {type_name(arr)}")
    if not arr: raise DonkyRuntimeError("pop() from empty array")
    return arr.pop()

def _read_file(args: list[object]) -> object:
    path = args[0]
    if not isinstance(path, str):
        raise DonkyRuntimeError(f"read_file() expects string, got {type_name(path)}")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except OSError as e:
        raise DonkyRuntimeError(f"read_file: cannot open {path!r}: {e.strerror or e}")

def _write_file(args: list[object]) -> object:
    path, content = args
    if not isinstance(path, str):
        raise DonkyRuntimeError(f"write_file() expects string, got {type_name(path)}")
    if not isinstance(content, str):
        raise DonkyRuntimeError(f"write_file() expects string, got {type_name(content)}")
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
    except OSError as e:
        raise DonkyRuntimeError(f"write_file: cannot write {path!r}: {e.strerror or e}")
    return None

def _file_exists(args: list[object]) -> object:
    import os
    path = args[0]
    if not isinstance(path, str):
        raise DonkyRuntimeError(f"file_exists() expects string, got {type_name(path)}")
    return os.path.exists(path)

def _split(args: list[object]) -> object:
    s, sep = args
    if not isinstance(s, str) or not isinstance(sep, str):
        raise DonkyRuntimeError("split() expects strings")
    if sep == "": raise DonkyRuntimeError("split() separator cannot be empty")
    return s.split(sep)

def _join(args: list[object]) -> object:
    arr, sep = args
    if not isinstance(arr, list) or not isinstance(sep, str):
        raise DonkyRuntimeError("join() expects array and string")
    parts = []
    for i, e in enumerate(arr):
        if not isinstance(e, str):
            raise DonkyRuntimeError(f"join() element {i} is {type_name(e)}, expected string")
        parts.append(e)
    return sep.join(parts)

def _contains(args: list[object]) -> object:
    container, item = args
    if isinstance(container, str) and isinstance(item, str): return item in container
    if isinstance(container, list): return item in container
    if isinstance(container, dict): return item in container
    raise DonkyRuntimeError(f"contains() expects string, array, or map, got {type_name(container)}")

def _keys(args: list[object]) -> object:
    m = args[0]
    if not isinstance(m, dict):
        raise DonkyRuntimeError(f"keys() expects map, got {type_name(m)}")
    return list(m.keys())

def _upper(args: list[object]) -> object:
    if not isinstance(args[0], str):
        raise DonkyRuntimeError(f"upper() expects string, got {type_name(args[0])}")
    return args[0].upper()

def _lower(args: list[object]) -> object:
    if not isinstance(args[0], str):
        raise DonkyRuntimeError(f"lower() expects string, got {type_name(args[0])}")
    return args[0].lower()

def _trim(args: list[object]) -> object:
    if not isinstance(args[0], str):
        raise DonkyRuntimeError(f"trim() expects string, got {type_name(args[0])}")
    return args[0].strip()

def _replace(args: list[object]) -> object:
    s, old, new = args
    if not isinstance(s, str) or not isinstance(old, str) or not isinstance(new, str):
        raise DonkyRuntimeError("replace() expects three strings")
    if old == "": raise DonkyRuntimeError("replace() old cannot be empty")
    return s.replace(old, new)

def _input(args: list[object]) -> object:
    prompt = args[0] if args else ""
    if not isinstance(prompt, str):
        raise DonkyRuntimeError("input() expects string prompt")
    try: return input(prompt)
    except EOFError: raise DonkyRuntimeError("input(): end of input")

def _sort(args: list[object]) -> object:
    arr = args[0]
    if not isinstance(arr, list):
        raise DonkyRuntimeError(f"sort() expects array, got {type_name(arr)}")
    if not arr:
        return None
    kinds = set()
    for e in arr:
        if isinstance(e, bool):
            kinds.add("bool")
        elif isinstance(e, (int, float)):
            kinds.add("number")
        elif isinstance(e, str):
            kinds.add("string")
        else:
            raise DonkyRuntimeError(f"sort() cannot sort element of type {type_name(e)}")
    if len(kinds) > 1:
        joined = " and ".join(sorted(kinds))
        raise DonkyRuntimeError(f"sort() cannot mix types: {joined}")
    try:
        arr.sort()
    except TypeError as e:
        raise DonkyRuntimeError(f"sort() failed: {e}")
    return None

# ---------- Networking & Web ----------

def _tcp_listen(args: list[object]) -> object:
    port = args[0]
    if not isinstance(port, int) or isinstance(port, bool):
        raise DonkyRuntimeError("tcp_listen() expects integer port")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        s.listen(10)
        fd = next(_socket_counter)
        SOCKETS[fd] = s
        return fd
    except Exception as e:
        raise DonkyRuntimeError(f"tcp_listen failed: {e}")

def _tcp_accept(args: list[object]) -> object:
    fd = args[0]
    s = SOCKETS.get(fd)
    if not s: raise DonkyRuntimeError("invalid server socket")
    try:
        client, _ = s.accept()
        cfd = next(_socket_counter)
        SOCKETS[cfd] = client
        return cfd
    except Exception as e:
        raise DonkyRuntimeError(f"tcp_accept failed: {e}")

def _tcp_read(args: list[object]) -> object:
    fd = args[0]
    max_bytes = args[1] if len(args) > 1 else 4096
    s = SOCKETS.get(fd)
    if not s: raise DonkyRuntimeError("invalid client socket")
    try:
        data = s.recv(max_bytes)
        return data.decode("utf-8", errors="replace")
    except Exception as e:
        raise DonkyRuntimeError(f"tcp_read failed: {e}")

def _tcp_write(args: list[object]) -> object:
    fd = args[0]
    data = args[1]
    if not isinstance(data, str): raise DonkyRuntimeError("tcp_write() expects string")
    s = SOCKETS.get(fd)
    if not s: raise DonkyRuntimeError("invalid client socket")
    try:
        s.sendall(data.encode("utf-8"))
        return None
    except Exception as e:
        raise DonkyRuntimeError(f"tcp_write failed: {e}")

def _tcp_close(args: list[object]) -> object:
    fd = args[0]
    s = SOCKETS.pop(fd, None)
    if s:
        try: s.close()
        except Exception: pass
    return None

def _http_get(args: list[object]) -> object:
    url = args[0]
    if not isinstance(url, str):
        raise DonkyRuntimeError("http_get() expects string URL")
    try:
        # Standard library HTTP request
        req = urllib.request.Request(url, headers={'User-Agent': 'Donky-Lang/3.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        raise DonkyRuntimeError(f"http_get failed: {e}")

def _url_decode(args: list[object]) -> object:
    s = args[0]
    if not isinstance(s, str):
        raise DonkyRuntimeError("url_decode() expects string")
    return urllib.parse.unquote_plus(s)

def _mime_type(args: list[object]) -> object:
    path = args[0]
    if not isinstance(path, str): return "text/plain"
    if path.endswith(".html"): return "text/html"
    if path.endswith(".css"): return "text/css"
    if path.endswith(".js"): return "application/javascript"
    if path.endswith(".png"): return "image/png"
    if path.endswith(".jpg") or path.endswith(".jpeg"): return "image/jpeg"
    if path.endswith(".svg"): return "image/svg+xml"
    return "text/plain"

def _spawn(args: list[object]) -> object:
    # This is intercepted by the Interpreter and VM.
    raise DonkyRuntimeError("spawn() not supported in this execution mode")

BUILTINS = [
    ("len",        1, _len,          1),
    ("str",        1, _str,          1),
    ("num",        1, _num,          1),
    ("type",       1, _type,         1),
    ("push",       2, _push,         2),
    ("pop",        1, _pop,          1),
    ("read_file",  1, _read_file,    1),
    ("write_file", 2, _write_file,   2),
    ("file_exists", 1, _file_exists, 1),
    ("split",      2, _split,        2),
    ("join",       2, _join,         2),
    ("contains",   2, _contains,     2),
    ("keys",       1, _keys,         1),
    ("upper",      1, _upper,        1),
    ("lower",      1, _lower,        1),
    ("trim",       1, _trim,         1),
    ("replace",    3, _replace,      3),
    ("input",      0, _input,        1),
    ("sort",       1, _sort,         1),
    ("tcp_listen", 1, _tcp_listen,   1),
    ("tcp_accept", 1, _tcp_accept,   1),
    ("tcp_read",   1, _tcp_read,     2),
    ("tcp_write",  2, _tcp_write,    2),
    ("tcp_close",  1, _tcp_close,    1),
    ("url_decode", 1, _url_decode,   1),
    ("mime_type",  1, _mime_type,    1),
    ("spawn",      1, _spawn,        1),
    ("http_get",   1, _http_get,     1),
]

def install_builtins(env: Environment, args: list[str] | None = None) -> None:
    for name, arity, impl, max_arity in BUILTINS:
        env.define(name, Builtin(name, arity, impl, max_arity))
    env.define("args", list(args) if args else [])