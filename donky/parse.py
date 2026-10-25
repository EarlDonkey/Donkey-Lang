import sys
from donky.lexer import Lexer
from donky.parser import Parser
from donky.ast_print import show


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/hello.donk"
    with open(path, encoding="utf-8-sig") as f:
        src = f.read()
    toks = Lexer(src).tokenize()
    program = Parser(toks).parse()
    print(show(program))


if __name__ == "__main__":
    main()