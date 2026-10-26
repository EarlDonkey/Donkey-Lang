import os
import sys

from donky import modules
from donky.bytecode import disassemble
from donky.compiler import CompileError, Compiler
from donky.errors import DonkyRuntimeError
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

    base_dir = os.path.dirname(os.path.abspath(path))

    try:
        toks = Lexer(src).tokenize()
        prog = Parser(toks).parse()
        prog = modules.expand(prog, base_dir)
        code = Compiler().compile(prog)
        print(disassemble(code))
    except (LexError, ParseError, CompileError, DonkyRuntimeError) as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()