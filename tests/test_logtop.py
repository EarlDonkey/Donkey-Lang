import contextlib
import io
import os

import pytest

from donky import modules
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGTOP = os.path.join(REPO_ROOT, "examples", "logtop.donk")


SAMPLE_LOG = """\
192.168.1.10 - - [10/Oct/2024:13:55:36 -0700] "GET /index.html HTTP/1.0" 200 2326
192.168.1.10 - - [10/Oct/2024:13:55:37 -0700] "GET /about HTTP/1.0" 200 1024
192.168.1.10 - - [10/Oct/2024:13:55:38 -0700] "GET /index.html HTTP/1.0" 200 2326
192.168.1.20 - - [10/Oct/2024:13:55:39 -0700] "GET /index.html HTTP/1.0" 200 2326
192.168.1.20 - - [10/Oct/2024:13:55:40 -0700] "POST /login HTTP/1.0" 401 512
192.168.1.30 - - [10/Oct/2024:13:55:41 -0700] "GET /notfound HTTP/1.0" 404 128
192.168.1.30 - - [10/Oct/2024:13:55:42 -0700] "GET /index.html HTTP/1.0" 200 2326
192.168.1.40 - - [10/Oct/2024:13:55:43 -0700] "GET /about HTTP/1.0" 200 1024
192.168.1.10 - - [10/Oct/2024:13:55:44 -0700] "DELETE /api/user/1 HTTP/1.0" 401 256
192.168.1.50 - - [10/Oct/2024:13:55:45 -0700] "GET / HTTP/1.0" 200 512
"""


def run_logtop(log_path: str, args: list[str]) -> str:
    with open(LOGTOP, encoding="utf-8-sig") as f:
        src = f.read()
    prog = Parser(Lexer(src).tokenize()).parse()
    base_dir = os.path.dirname(os.path.abspath(LOGTOP))
    prog = modules.expand(prog, base_dir)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter(args=[log_path] + args).run(prog)
    return buf.getvalue()


def _write_sample(tmp_path):
    log = tmp_path / "access.log"
    log.write_text(SAMPLE_LOG, encoding="utf-8")
    return str(log)


def test_ip_top(tmp_path):
    out = run_logtop(_write_sample(tmp_path), ["ip", "5"])
    assert "192.168.1.10" in out
    for line in out.split("\n"):
        if "192.168.1.10" in line:
            assert "4" in line
            return
    pytest.fail("192.168.1.10 not found in output")


def test_status_top(tmp_path):
    out = run_logtop(_write_sample(tmp_path), ["status", "5"])
    for line in out.split("\n"):
        if " 200" in line:
            assert "7" in line
            return
    pytest.fail("status 200 not found in output")


def test_method_top(tmp_path):
    out = run_logtop(_write_sample(tmp_path), ["method", "5"])
    for line in out.split("\n"):
        if "GET" in line:
            assert "8" in line
            return
    pytest.fail("method GET not found in output")


def test_limit_respected(tmp_path):
    out = run_logtop(_write_sample(tmp_path), ["ip", "2"])
    data_rows = [l for l in out.split("\n") if l.strip() and not l.startswith("===")]
    assert len(data_rows) == 2


def test_missing_file(tmp_path):
    with pytest.raises(DonkyRuntimeError):
        run_logtop(str(tmp_path / "nope.log"), ["ip", "5"])


def test_unknown_field(tmp_path):
    with pytest.raises(DonkyRuntimeError):
        run_logtop(_write_sample(tmp_path), ["bogus", "5"])