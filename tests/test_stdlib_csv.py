import contextlib
import io
import os

from donky import modules
from donky.interpreter import Interpreter
from donky.lexer import Lexer
from donky.parser import Parser


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    prog = modules.expand(prog, REPO_ROOT)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Interpreter().run(prog)
    return buf.getvalue()


def test_parse_line():
    assert run('import "lib/csv.donk"; print(parse_line("a,b,c"));') == "[a, b, c]\n"


def test_parse_line_single():
    assert run('import "lib/csv.donk"; print(parse_line("only"));') == "[only]\n"


def test_format_line():
    assert run('import "lib/csv.donk"; print(format_line(["a", "b", "c"]));') == "a,b,c\n"


def test_parse_table():
    src = 'import "lib/csv.donk"; print(parse_table("a,b\\nc,d"));'
    assert run(src) == "[[a, b], [c, d]]\n"


def test_parse_table_skips_blank_lines():
    src = 'import "lib/csv.donk"; print(len(parse_table("a,b\\n\\nc,d")));'
    assert run(src) == "2\n"


def test_format_table():
    src = 'import "lib/csv.donk"; print(format_table([["a", "b"], ["c", "d"]]));'
    assert run(src) == "a,b\nc,d\n"


def test_roundtrip():
    src = (
        'import "lib/csv.donk";'
        'let t = parse_table("1,2\\n3,4");'
        'print(format_table(t));'
    )
    assert run(src) == "1,2\n3,4\n"