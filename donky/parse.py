import os
import sys

from donky import modules
from donky.ast_print import show
from donky.lexer import Lexer
from donky.parser import Parser


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/hello.donk"
    with open(path, encoding="utf-8-sig") as f:
        src = f.read()
    base_dir = os.path.dirname(os.path.abspath(path))
    toks = Lexer(src).tokenize()
    prog = Parser(toks).parse()
    prog = modules.expand(prog, base_dir)
    print(show(prog))


if __name__ == "__main__":
    main()