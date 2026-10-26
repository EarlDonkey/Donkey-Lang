import sys
import os

from donky import modules
from donky import typecheck
from donky.compiler import CompileError, Compiler
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import LexError, Lexer
from donky.parser import ParseError, Parser
from donky.vm import VM

# Import the package manager
from donky import package


def main() -> None:
    argv = sys.argv[1:]
    
    # --- New Package Manager Logic ---
    if len(argv) > 0 and argv[0] == "install":
        package.install()
        return
    # ---------------------------------

    use_bytecode = False
    use_types = True
    check_only = False
    while argv and argv[0].startswith("--"):
        flag = argv.pop(0)
        if flag == "--bytecode":
            use_bytecode = True
        elif flag == "--no-types":
            use_types = False
        elif flag == "--check-only":
            check_only = True
        else:
            print(f"donky: unknown flag {flag}", file=sys.stderr)
            sys.exit(2)

    if not argv:
        print("donky: no file specified", file=sys.stderr)
        sys.exit(2)

    path = argv[0]
    script_args = argv[1:]

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
        if use_types:
            typecheck.check(prog)
        if check_only:
            return
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
    except typecheck.TypeCheckError as e:
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