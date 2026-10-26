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


def test_map():
    src = (
        'import "lib/list.donk";'
        'print(map([1, 2, 3], fn(x) -> num { return x * 2; }));'
    )
    assert run(src) == "[2, 4, 6]\n"


def test_map_empty():
    src = 'import "lib/list.donk"; print(map([], fn(x) -> num { return x; }));'
    assert run(src) == "[]\n"


def test_filter():
    src = (
        'import "lib/list.donk";'
        'print(filter([1, 2, 3, 4], fn(x) -> bool { return x % 2 == 0; }));'
    )
    assert run(src) == "[2, 4]\n"


def test_reduce_sum():
    src = (
        'import "lib/list.donk";'
        'print(reduce([1, 2, 3, 4], fn(a, b) -> num { return a + b; }, 0));'
    )
    assert run(src) == "10\n"


def test_reduce_product():
    src = (
        'import "lib/list.donk";'
        'print(reduce([2, 3, 4], fn(a, b) -> num { return a * b; }, 1));'
    )
    assert run(src) == "24\n"


def test_reverse():
    src = 'import "lib/list.donk"; print(reverse([1, 2, 3]));'
    assert run(src) == "[3, 2, 1]\n"


def test_reverse_non_mutating():
    src = (
        'import "lib/list.donk";'
        'let a = [1, 2, 3];'
        'let b = reverse(a);'
        'print(a); print(b);'
    )
    assert run(src) == "[1, 2, 3]\n[3, 2, 1]\n"


def test_unique():
    src = 'import "lib/list.donk"; print(unique([1, 2, 1, 3, 2, 4]));'
    assert run(src) == "[1, 2, 3, 4]\n"


def test_any_true():
    src = (
        'import "lib/list.donk";'
        'print(any([1, 2, 3], fn(x) -> bool { return x > 2; }));'
    )
    assert run(src) == "true\n"


def test_any_false():
    src = (
        'import "lib/list.donk";'
        'print(any([1, 2, 3], fn(x) -> bool { return x > 10; }));'
    )
    assert run(src) == "false\n"


def test_all_true():
    src = (
        'import "lib/list.donk";'
        'print(all([2, 4, 6], fn(x) -> bool { return x % 2 == 0; }));'
    )
    assert run(src) == "true\n"


def test_all_false():
    src = (
        'import "lib/list.donk";'
        'print(all([2, 3, 4], fn(x) -> bool { return x % 2 == 0; }));'
    )
    assert run(src) == "false\n"


def test_all_empty():
    src = 'import "lib/list.donk"; print(all([], fn(x) -> bool { return false; }));'
    assert run(src) == "true\n"


def test_count():
    src = (
        'import "lib/list.donk";'
        'print(count([1, 2, 3, 4, 5], fn(x) -> bool { return x > 2; }));'
    )
    assert run(src) == "3\n"


def test_chained_map_filter():
    src = (
        'import "lib/list.donk";'
        'let result = filter(map([1, 2, 3, 4], fn(x) -> num { return x * x; }), '
        '  fn(x) -> bool { return x > 5; });'
        'print(result);'
    )
    assert run(src) == "[9, 16]\n"
    
def test_sort_by_numbers():
    src = (
        'import "lib/list.donk";'
        'let a = [3, 1, 2];'
        'print(sort_by(a, fn(x) -> num { return x; }));'
    )
    assert run(src) == "[1, 2, 3]\n"


def test_sort_by_empty():
    src = 'import "lib/list.donk"; print(sort_by([], fn(x) -> num { return x; }));'
    assert run(src) == "[]\n"


def test_sort_by_single():
    src = 'import "lib/list.donk"; print(sort_by([5], fn(x) -> num { return x; }));'
    assert run(src) == "[5]\n"


def test_sort_by_strings():
    src = (
        'import "lib/list.donk";'
        'print(sort_by(["c", "a", "b"], fn(s) -> str { return s; }));'
    )
    assert run(src) == "[a, b, c]\n"


def test_sort_by_derived_key():
    src = (
        'import "lib/list.donk";'
        'let words = ["banana", "kiwi", "apple"];'
        'let by_len = sort_by(words, fn(w) -> num { return len(w); });'
        'print(by_len);'
    )
    assert run(src) == "[kiwi, apple, banana]\n"


def test_sort_by_non_mutating():
    src = (
        'import "lib/list.donk";'
        'let a = [3, 1, 2];'
        'let b = sort_by(a, fn(x) -> num { return x; });'
        'print(a); print(b);'
    )
    assert run(src) == "[3, 1, 2]\n[1, 2, 3]\n"


def test_sort_by_stable():
    src = (
        'import "lib/list.donk";'
        'let pairs = [[1, "a"], [2, "b"], [1, "c"], [2, "d"]];'
        'let sorted = sort_by(pairs, fn(p) -> num { return p[0]; });'
        'print(sorted);'
    )
    assert run(src) == "[[1, a], [1, c], [2, b], [2, d]]\n"


def test_sort_by_reverse_for_desc():
    src = (
        'import "lib/list.donk";'
        'let a = [1, 3, 2];'
        'let desc = reverse(sort_by(a, fn(x) -> num { return x; }));'
        'print(desc);'
    )
    assert run(src) == "[3, 2, 1]\n"