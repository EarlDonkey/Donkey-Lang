import sys

from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import LexError, Lexer
from donky.parser import ParseError, Parser


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/hello.donk"
    try:
        with open(path, encoding="utf-8-sig") as f:
            src = f.read()
    except OSError as e:
        print(f"donky: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        toks = Lexer(src).tokenize()
        prog = Parser(toks).parse()
        Interpreter().run(prog)
    except LexError as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)
    except ParseError as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)
    except DonkyRuntimeError as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()