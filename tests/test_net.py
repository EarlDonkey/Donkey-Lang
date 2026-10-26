import contextlib
import io
import socket
import threading
import time

import pytest

from donky.builtins import SOCKETS
from donky.compiler import Compiler
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser
from donky.vm import VM


def run_src(src: str) -> None:
    prog = Parser(Lexer(src).tokenize()).parse()
    Interpreter().run(prog)


def test_tcp_listen_returns_int():
    src = """
    let s = tcp_listen(0);
    print(type(s));
    tcp_close(s);
    """
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_src(src)
    assert buf.getvalue() == "number\n"


def test_tcp_invalid_socket():
    with pytest.raises(Exception):
        run_src("tcp_accept(9999);")