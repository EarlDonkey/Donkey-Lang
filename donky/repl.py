import os
import sys

from donky import modules
from donky.errors import DonkyRuntimeError
from donky.interpreter import Interpreter
from donky.lexer import LexError, Lexer, TokenType
from donky.parser import ParseError, Parser
from donky.values import format_value


PROMPT = "donky> "
CONT_PROMPT = "...> "

BANNER = "Donky REPL (type :help for commands, Ctrl+D or :quit to exit)"


def _brace_delta(line: str) -> int:
    delta = 0
    in_string = False
    i = 0
    while i < len(line):
        c = line[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
        elif c == "/" and i + 1 < len(line) and line[i + 1] == "/":
            break
        elif c == "{":
            delta += 1
        elif c == "}":
            delta -= 1
        i += 1
    return delta


def _read_chunk() -> str | None:
    try:
        first = input(PROMPT)
    except EOFError:
        return None

    lines = [first]
    depth = _brace_delta(first)
    while depth > 0:
        try:
            cont = input(CONT_PROMPT)
        except EOFError:
            break
        lines.append(cont)
        depth += _brace_delta(cont)
    return "\n".join(lines)


def _try_expression(src: str, interp: Interpreter) -> bool:
    try:
        parser = Parser(Lexer(src).tokenize())
        expr = parser.parse_expr()
        if parser._peek().type is not TokenType.EOF:
            return False
        print(format_value(interp.eval_expr(expr)))
        return True
    except (LexError, ParseError, DonkyRuntimeError):
        return False


def _report(src: str, interp: Interpreter, base_dir: str,
            seen: set[str]) -> None:
    if _try_expression(src, interp):
        return

    # Attempt 1: parse as-is, expand modules, run
    try:
        prog = Parser(Lexer(src).tokenize()).parse()
        seen_copy = set(seen)
        prog = modules.expand(prog, base_dir, seen_copy)
        interp.run(prog)
        seen.update(seen_copy)
        return
    except (LexError, ParseError):
        pass
    except DonkyRuntimeError as e:
        print(f"donky: {e}", file=sys.stderr)
        return

    # Attempt 2: retry with ';' appended (statements without trailing semicolon)
    try:
        prog = Parser(Lexer(src + ";").tokenize()).parse()
        seen_copy = set(seen)
        prog = modules.expand(prog, base_dir, seen_copy)
        interp.run(prog)
        seen.update(seen_copy)
        return
    except (LexError, ParseError):
        pass
    except DonkyRuntimeError as e:
        print(f"donky: {e}", file=sys.stderr)
        return

    # All attempts failed — show the first real error
    try:
        Parser(Lexer(src).tokenize()).parse()
    except LexError as e:
        print(f"donky: {e}", file=sys.stderr)
    except ParseError as e:
        print(f"donky: {e}", file=sys.stderr)


def repl() -> None:
    interp = Interpreter()
    base_dir = os.getcwd()
    seen: set[str] = set()
    print(BANNER)

    while True:
        try:
            src = _read_chunk()
        except KeyboardInterrupt:
            print()
            continue
        if src is None:
            print()
            return

        stripped = src.strip()
        if not stripped:
            continue

        if stripped in (":quit", ":q", ":exit"):
            return
        if stripped == ":help":
            print("  :help          show this message")
            print("  :quit / :q     exit")
            print("  <expression>   evaluate and print (e.g. 1 + 2)")
            print("  <statement>;   run a statement (e.g. let x = 1;)")
            print("  { ... }        multi-line blocks are supported")
            print("  import \"...\"   load a module (relative to cwd)")
            continue

        _report(src, interp, base_dir, seen)


def main() -> None:
    repl()


if __name__ == "__main__":
    main()