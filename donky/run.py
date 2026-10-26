import sys

from donky.compiler import CompileError, Compiler
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import LexError, Lexer
from donky.parser import ParseError, Parser
from donky.vm import VM


def main() -> None:
    argv = sys.argv[1:]
    use_bytecode = False
    if "--bytecode" in argv:
        use_bytecode = True
        argv.remove("--bytecode")

    path = argv[0] if argv else "examples/hello.donk"
    script_args = argv[1:]

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
            VM(args=script_args).run(code)
        else:
            Interpreter(args=script_args).run(prog)
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