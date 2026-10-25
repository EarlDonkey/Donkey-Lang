import sys

from donky.bytecode import disassemble
from donky.compiler import CompileError, Compiler
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import LexError, Lexer
from donky.parser import ParseError, Parser
from donky.vm import VM


def main() -> None:
    args = sys.argv[1:]
    use_bytecode = False
    if "--bytecode" in args:
        use_bytecode = True
        args.remove("--bytecode")

    path = args[0] if args else "examples/hello.donk"
    try:
        with open(path, encoding="utf-8-sig") as f:
            src = f.read()
    except OSError as e:
        print(f"donky: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        toks = Lexer(src).tokenize()
        prog = Parser(toks).parse()
        if use_bytecode:
            code = Compiler().compile(prog)
            VM().run(code)
        else:
            Interpreter().run(prog)
    except LexError as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)
    except ParseError as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)
    except CompileError as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)
    except DonkyRuntimeError as e:
        print(f"{path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()