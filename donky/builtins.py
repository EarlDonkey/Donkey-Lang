import socket
import itertools
import threading
import urllib.parse
import json
import time as py_time
import ipaddress
import subprocess

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

def _to_json(args: list[object]) -> object:
    try:
        return json.dumps(args[0])
    except Exception as e:
        raise DonkyRuntimeError(f"to_json failed: {e}")

def _from_json(args: list[object]) -> object:
    try:
        return json.loads(args[0])
    except Exception as e:
        raise DonkyRuntimeError(f"from_json failed: {e}")

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

def _tcp_connect(args: list[object]) -> object:
    ip = args[0]
    port = args[1]
    timeout = args[2] if len(args) > 2 else 1.0
    if not isinstance(ip, str) or not isinstance(port, int):
        raise DonkyRuntimeError("tcp_connect() expects (ip_str, port_int, [timeout_float])")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        result = s.connect_ex((ip, port))
        s.close()
        return result == 0 # Returns true if open
    except Exception:
        return False

def _sleep(args: list[object]) -> object:
    sec = args[0]
    if not isinstance(sec, (int, float)):
        raise DonkyRuntimeError("sleep() expects a number")
    py_time.sleep(sec)
    return None

def _time(args: list[object]) -> object:
    return py_time.time()

def _ip_to_list(args: list[object]) -> object:
    cidr = args[0]
    if not isinstance(cidr, str):
        raise DonkyRuntimeError("ip_to_list() expects a string CIDR")
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        # .hosts() excludes network and broadcast addresses automatically
        return [str(ip) for ip in net.hosts()]
    except Exception as e:
        raise DonkyRuntimeError(f"ip_to_list() failed: {e}")

def _get_mac(args: list[object]) -> object:
    ip = args[0]
    if not isinstance(ip, str):
        raise DonkyRuntimeError("get_mac() expects string IP")
    try:
        # Runs the Windows ARP command and parses the output
        output = subprocess.check_output(["arp", "-a", ip], text=True, errors="ignore")
        for line in output.splitlines():
            if ip in line:
                parts = line.split()
                for part in parts:
                    # Look for standard MAC formats (XX-XX-XX-XX-XX-XX or XX:XX:XX:XX:XX:XX)
                    if len(part) == 17 and (part.count('-') == 5 or part.count(':') == 5):
                        return part.replace(":", "-")
        return "Unknown"
    except Exception:
        return "Unknown"

def _get_local_ip(args: list[object]) -> object:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def _dns_lookup(args: list[object]) -> object:
    ip = args[0]
    if not isinstance(ip, str):
        raise DonkyRuntimeError("dns_lookup() expects string IP")
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return "Unknown"

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
    raise DonkyRuntimeError("spawn() not supported in this execution mode")

def _http_get(args: list[object]) -> object:
    url = args[0]
    if not isinstance(url, str):
        raise DonkyRuntimeError("http_get() expects string URL")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Donky-Lang/3.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        raise DonkyRuntimeError(f"http_get failed: {e}")

def _ws_accept(args: list[object]) -> object:
    import hashlib, base64
    fd = args[0]
    key = args[1]
    if not isinstance(key, str): raise DonkyRuntimeError("ws_accept() expects string key")
    s = SOCKETS.get(fd)
    if not s: raise DonkyRuntimeError("invalid client socket")
    accept_key = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
    response = f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {accept_key}\r\n\r\n"
    try:
        s.sendall(response.encode())
        return None
    except Exception as e:
        raise DonkyRuntimeError(f"ws_accept failed: {e}")

def _ws_read(args: list[object]) -> object:
    fd = args[0]
    s = SOCKETS.get(fd)
    if not s: raise DonkyRuntimeError("invalid client socket")
    try:
        header = s.recv(2)
        if len(header) < 2: return ""
        opcode = header[0] & 0x0F
        masked = (header[1] & 0x80) != 0
        length = header[1] & 0x7F
        
        if length == 126: length = int.from_bytes(s.recv(2), 'big')
        elif length == 127: length = int.from_bytes(s.recv(8), 'big')
            
        mask = s.recv(4) if masked else b''
        payload = s.recv(length)
        
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            
        if opcode == 8: return ""
        return payload.decode('utf-8', errors='replace')
    except Exception:
        return ""

def _ws_write(args: list[object]) -> object:
    fd = args[0]
    msg = args[1]
    if not isinstance(msg, str): raise DonkyRuntimeError("ws_write() expects string")
    s = SOCKETS.get(fd)
    if not s: raise DonkyRuntimeError("invalid client socket")
    try:
        payload = msg.encode('utf-8')
        length = len(payload)
        if length < 126: header = bytes([0x81, length])
        elif length < 65536: header = bytes([0x81, 126]) + length.to_bytes(2, 'big')
        else: header = bytes([0x81, 127]) + length.to_bytes(8, 'big')
        s.sendall(header + payload)
        return None
    except Exception as e:
        raise DonkyRuntimeError(f"ws_write failed: {e}")

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
    ("to_json",    1, _to_json,      1),
    ("from_json",  1, _from_json,    1),
    ("tcp_listen", 1, _tcp_listen,   1),
    ("tcp_accept", 1, _tcp_accept,   1),
    ("tcp_read",   1, _tcp_read,     2),
    ("tcp_write",  2, _tcp_write,    2),
    ("tcp_close",  1, _tcp_close,    1),
    ("url_decode", 1, _url_decode,   1),
    ("mime_type",  1, _mime_type,    1),
    ("spawn",      1, _spawn,        1),
    ("http_get",   1, _http_get,     1),
    ("ws_accept", 2, _ws_accept, 2),
    ("ws_read",   1, _ws_read,   1),
    ("ws_write",  2, _ws_write,  2),
    ("tcp_connect", 2, _tcp_connect, 3),
    ("get_local_ip", 0, _get_local_ip, 0),
    ("dns_lookup", 1, _dns_lookup, 1),
    ("sleep",      1, _sleep,        1),
    ("time",       0, _time,         0),
    ("ip_to_list", 1, _ip_to_list,   1),
    ("get_mac",    1, _get_mac,      1),
    
]

def install_builtins(env: Environment, args: list[str] | None = None) -> None:
    for name, arity, impl, max_arity in BUILTINS:
        env.define(name, Builtin(name, arity, impl, max_arity))
    env.define("args", list(args) if args else [])