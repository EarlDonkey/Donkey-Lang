What Donky is
A small, statically-shaped (dynamically typed at runtime), educational programming language implemented in Python. It has:

A lexer, Pratt parser, and AST with source positions

Two execution engines: a tree-walking interpreter and a bytecode compiler + stack VM with closures

A differential test suite proving both engines agree on every test

A REPL, a disassembler, and a CLI runner

The language is deliberately small: types are number (int or float), string, bool, array, function. There is no null, no maps, no user-defined types, no modules, no imports. It exists to be extended.

Quick start
powershell
# Setup (once)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pytest

# Run a program (interpreter)
python -m donky.run examples/hello.donk

# Run a program (VM)
python -m donky.run --bytecode examples/hello.donk

# Pass arguments
python -m donky.run examples/facts.donk 42

# Start the REPL
python -m donky

# Disassemble a program (see bytecode)
python -m donky.compile examples/hello.donk

# Run the test suite
pytest -q
Lexical grammar
Comments: // to end of line

Whitespace: skipped between tokens

BOM: stripped if present (handles PowerShell Out-File -Encoding utf8)

Numbers: 123, 45.6. No scientific notation, no hex, no leading . (.5 errors).

Strings: "hello" with escapes \n, \t, \", \\. No raw strings, no multi-line literals (use \n).

Identifiers: letters, digits, _; must start with letter or _.

Keywords: let, fn, if, else, while, return, print, true, false, div.

Punctuation: (, ), {, }, [, ], ;, ,

Operators: + - * / % == != < <= > >= = && || !

Integer division: div (keyword, not // since // is a comment)

Type system
Type	Example	Notes
number	42, 3.14	Python int or float. bool is NOT a number — 1 + true errors.
string	"hi"	UTF-8, immutable. Concatenation with +.
bool	true, false	Distinct from numbers. Conditions must be bool.
array	[1, 2, 3]	Mutable, reference type. Mixed-type allowed.
function	fn f() -> num { ... }	First-class; closures capture by reference.
No null. Functions with no return implicitly return None (prints as None, but there's no literal for it). This is a known wart — either add null or change the implicit-return convention in a future session.

Operator precedence (loosest to tightest)
Level	Operators	Associativity
1	||	left
2	&&	left
3	== !=	left
4	< <= > >=	left
6	+ -	left
7	* / % div	left
8	unary - !	prefix
9	postfix [i]	chainable
Parentheses override everything. && and || short-circuit. Assignment = is a statement, not an expression — it never appears inside a larger expression.

Statements
All statements end in ; (required). All blocks use { } (required, even for single statements).

text
let x = 10;                    // declaration, creates new binding
x = 20;                        // reassignment; errors if x undefined
a[0] = 5;                      // array index assignment; errors on strings
print(expr);                   // print with trailing newline
if cond { ... } else { ... }   // else is optional
while cond { ... }             // cond must be bool
fn name(a, b) -> type { ... }  // type is the return type annotation
return expr;                   // only inside fn
return;                        // return without value (implicit None)
{ stmt1; stmt2; }              // bare block creates a new scope
Not supported: for, break, continue, match, ternary ?:, compound assignment (+=).

Expressions
text
42                     // number
3.14                   // float
"hello"                // string
true                   // bool
x                      // variable reference
a + b                  // arithmetic
-a                     // unary minus
!flag                  // logical not (bool only)
[1, 2, 3]              // array literal
a[0]                   // array or string index
"hi"[0]                // → "h"
f(1, 2)                // function call
Scoping
Donky has block scoping with lexical resolution:

Top-level let / fn → global

Any let inside { } (function body, if body, while body, bare block) → local to that block

Reading a name: search local scopes outward, then upvalues (enclosing function), then globals

Assignment x = v finds the innermost binding of x in scope

Shadowing works — an inner let hides an outer of the same name

Functions
text
fn add(a, b) -> num {
    return a + b;
}
Return type is parsed but not checked (a type checker is planned).

Parameters are untyped.

Functions are first-class values — store in variables, pass as arguments, return from functions.

Recursion is supported (functions resolve themselves through globals or upvalues).

Closures capture by reference — mutating a captured variable is visible to all closures sharing it.

text
fn make_counter() -> any {
    let n = 0;
    fn inc() -> num { n = n + 1; return n; }
    return inc;
}

let c = make_counter();
print(c());     // 1
print(c());     // 2
(any as a return type annotation is a placeholder — accepted by the parser, ignored by the runtime.)

Arrays
Literals: [1, 2, 3], []. No trailing comma.

Indexing: a[0]. Index must be int (not float, not bool, not negative).

Bounds: 0 <= i < len(a). Same error for negative and out-of-range.

Mutation: a[0] = 5 mutates in place. push(a, v) and pop(a) also mutate.

Reference semantics: let b = a — b and a are the same array.

Nested: [[1, 2], [3, 4]] works; m[1][0] is 3.

Heterogeneous: [1, "hi", true] is allowed.

Strings
Literal: "..." with escapes \n, \t, \", \\

Immutable — s[0] = "x" errors

Index: s[0] returns a single-character string. 0 <= i < len(s).

Concatenation: "a" + "b" → "ab"

Length: len(s)

Comparison: <, <=, >, >= work lexicographically between two strings

Equality: ==, != work on all types

Not supported: slicing (s[1:3]), string iteration without indexing, multi-line literals. Note: \n in a string literal is a real newline, and Windows paths in Donky source must use / or escaped \\ — "C:\temp" is C: emp (tab + emp).

Builtins reference
Name	Arity	Signature	Errors
len(x)	1	string or array → number	other types
str(x)	1	any → string (uses print formatting: true→"true", [1,2]→"[1, 2]")	—
num(x)	1	number → same; string → parsed int or float	non-numeric string, bool, array
type(x)	1	any → "number", "string", "bool", "array", "function"	—
push(arr, v)	2	mutates, returns None	non-array first arg
pop(arr)	1	removes and returns last	non-array, empty array
read_file(path)	1	whole file as string (BOM-stripped)	missing file, non-string path
write_file(path, s)	2	overwrites file, returns None	unwritable path, non-string args
split(s, sep)	2	string → array of strings	non-string args, empty sep
join(arr, sep)	2	array of strings + sep → string	non-array, non-string elements/sep
contains(s, sub)	2	bool	non-string args
upper(s)	1	string	non-string
lower(s)	1	string	non-string
trim(s)	1	strip leading/trailing whitespace	non-string
replace(s, old, new)	3	replace all occurrences	non-string args, empty old
Special global: args — array of strings from the command line after the script path. Set at startup, shadowable with let args = ....

No: map, filter, reduce, sort, range, exit, input. map/filter can be written in Donky using closures.

Execution: interpreter vs VM
Both engines implement identical semantics, verified by a differential test suite (tests/test_vm.py::test_diff_*). Run either via the CLI:

powershell
python -m donky.run script.donk           # tree-walker
python -m donky.run --bytecode script.donk # compiler + VM
Tree-walking interpreter (donky/interpreter.py):

Directly evaluates the AST via match cases

Environments are Python dicts, chained via parent pointers

Closures hold a reference to the defining Environment

Positions come from AST node fields

Bytecode compiler + VM (donky/compiler.py, donky/vm.py, donky/bytecode.py):

Compiler walks AST, emits a list of (op, arg...) tuples per CodeObject

CodeObject has instructions, constants (deduplicated), positions (parallel to instructions), functions (nested), upvalues (capture descriptors), slot_count

Variables: locals in numbered Cell slots (LOAD_LOCAL/STORE_LOCAL), globals in a name-keyed dict (LOAD_GLOBAL/STORE_GLOBAL), upvalues in the closure's upvalues list (LOAD_UPVALUE/STORE_UPVALUE)

Values on a stack; instructions pop operands and push results

Closures: CAPTURE_LOCAL/CAPTURE_UPVALUE push Cell refs; CLOSURE idx, n bundles them

Control flow: JUMP/JUMP_IF_FALSE with absolute target indices; short-circuit uses JUMP_IF_*_PEEK (peek, don't pop)

Positions: parallel positions list, read by _execute before each instruction for error messages

The differential test file (tests/test_vm.py) runs every scenario through both engines and asserts identical output (or identical error message). Adding a new language feature requires:

Adding a test to test_interpreter.py (interpreter behavior)

Adding a test_diff_* to test_vm.py (both engines must agree)

If the VM diverges, fixing the VM

Bytecode instruction set (24 opcodes)
text
CONST idx          push constants[idx]
TRUE/FALSE         push literal
POP                discard top of stack
LOAD_LOCAL slot    push frame.slots[slot].value
STORE_LOCAL slot   frame.slots[slot].value = pop
LOAD_UPVALUE i     push frame.closure.upvalues[i].value
STORE_UPVALUE i    frame.closure.upvalues[i].value = pop
CAPTURE_LOCAL slot push frame.slots[slot] (the Cell)
CAPTURE_UPVALUE i  push frame.closure.upvalues[i] (the Cell)
DEFINE_GLOBAL name globals.define(name, pop)
LOAD_GLOBAL name   push globals.get(name)
STORE_GLOBAL name  globals.assign(name, pop)
ADD/SUB/MUL/DIV/MOD/FLOOR_DIV  arithmetic (pop 2, push 1)
NEG/NOT            unary (pop 1, push 1)
EQ/NE/LT/LE/GT/GE  comparison (pop 2, push bool)
JUMP target        ip = target
JUMP_IF_FALSE target  pop; if falsy, ip = target (errors if not bool)
JUMP_IF_FALSE_PEEK target  peek; if falsy, ip = target (no pop)
JUMP_IF_TRUE_PEEK target   peek; if truthy, ip = target (no pop)
CLOSURE idx, n     pop n cells, push Closure(functions[idx], cells)
CALL argc name     pop argc args and callee, push result
RETURN             pop, return to caller
PRINT              pop and print with trailing newline
NEW_ARRAY n        pop n values, push list
INDEX_GET          pop idx, pop arr, push arr[idx]
INDEX_SET          pop val, pop idx, pop arr, arr[idx] = val
Project structure
text
donky-lang/
├── donky/
│   ├── __init__.py
│   ├── __main__.py          # `python -m donky` → REPL
│   ├── lexer.py             # TokenType, Token, Lexer, LexError
│   ├── ast_nodes.py         # dataclasses for every AST node
│   ├── parser.py            # Parser, ParseError, INFX_BP
│   ├── ast_print.py         # show(node) → tree string
│   ├── parse.py             # CLI: print AST of a file
│   ├── errors.py            # DonkyRuntimeError (message, line, col)
│   ├── values.py            # Environment, Function, Builtin, Cell, Closure, helpers
│   ├── builtins.py          # len, str, num, type, push, pop, I/O, strings
│   ├── interpreter.py       # tree-walker
│   ├── bytecode.py          # Op enum, CodeObject, disassemble
│   ├── compiler.py          # AST → CodeObject, CompileError
│   ├── vm.py                # Frame, VM
│   ├── compile.py           # CLI: print disassembly
│   ├── run.py               # CLI: run a .donk file (interp or --bytecode)
│   └── repl.py              # interactive REPL
├── examples/
│   ├── hello.donk
│   ├── fib.donk
│   ├── scopes.donk
│   ├── collatz.donk
│   ├── roman.donk
│   ├── digit_sum.donk
│   ├── arrays.donk
│   ├── closure.donk
│   ├── args.donk
│   ├── greet.donk
│   ├── facts.donk
│   ├── strings.donk
│   └── wordcount.donk
├── tests/
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_compiler.py
│   ├── test_interpreter.py
│   ├── test_errors.py
│   ├── test_io.py
│   ├── test_string.py
│   ├── test_repl.py
│   └── test_vm.py            # includes all test_diff_* differential tests
├── docs/
│   └── DONKY.md              # ← this file
└── TODO.md
Known limitations / TODOs
Ordered by likely value:

None is a real value but has no literal. Functions without return yield None, and print shows it. Either add a null keyword or make "no return value" an error when used in an expression context.

No slicing (s[1:3], a[1:3]).

No for loops — only while. Iterating arrays is while i < len(a) { ... a[i] ... }.

No break/continue.

No maps/dictionaries.

No sort, map, filter, reduce. The latter three can be written in Donky using closures; sort would need a comparator or a builtin.

No type checker. Return type annotations are parsed but ignored. Adding a checker is a Path A milestone.

Python RecursionError leaks through. fib(30) will raise Python's error, not a Donky one. Catch and re-raise as DonkyRuntimeError("recursion too deep").

No raw strings. Windows paths need forward slashes or escaped backslashes.

No write_file append mode. Overwrites only.

split with leading/trailing delimiter produces empty strings. "a,,b".split(",") → ["a", "", "b"]. Callers must filter.

String assignment errors are explicit — s[0] = "x" errors with cannot assign to string index (strings are immutable).

args cannot be mutated by the runtime. It's just a list built at startup.

Adding a new feature — the checklist
When extending Donky, the order of edits is:

lexer.py — new tokens (add to TokenType); if a keyword, add to KEYWORDS

ast_nodes.py — new node dataclass with line: int = 0, col: int = 0 as trailing fields

parser.py — new parse method; add to parse_statement or parse_prefix or INFX_BP

bytecode.py — new opcode(s) if this feature compiles; extend _format_instr and disassemble if the op has unusual tuple shape

compiler.py — handle the new AST node in compile_expr or compile_stmt

values.py — extend type_name/format_value if a new runtime type is introduced

interpreter.py — handle the new node in eval_expr or exec_stmt

vm.py — handle the new opcode in _dispatch

builtins.py — add builtin functions if needed

Tests — test_interpreter.py (interpreter behavior) and test_vm.py::test_diff_* (both engines agree)

examples/ — add a demo that shows the feature

Instructions for the next AI assistant
You're continuing a project that already has ~292 tests and two working engines. Read this doc fully before suggesting changes. Key invariants to preserve:

The differential test suite is sacred. Every new feature must add both an interpreter test and a test_diff_* VM test. If the VM doesn't handle a feature, that's a bug to fix, not a test to skip.

Position tracking matters. Every runtime error from either engine must include [line:col]. DonkyRuntimeError carries line/col; use self._err(node, msg) (interpreter) or self._err(msg) (VM, uses self.position) so positions are attached.

Positions come from AST nodes (interpreter) or from CodeObject.positions (VM). Both must agree.

bool is not a number. isinstance(True, int) is a Python trap; always use is_number() or is_int() helpers.

Strings are immutable in both engines. s[0] = "x" must error with a clear message.

BOM stripping happens in the lexer (__init__) and files are opened with utf-8-sig — keep both.

newline="" on write_file — do not let Python translate \n → \r\n.

The compiler uses absolute jump targets, patched after emission (_patch_jump).

Slots are Cell objects, not raw values. STORE_LOCAL sets .value, not the slot itself.

When the user asks "add feature X", follow the checklist above. Verify with pytest -q before declaring done. If a differential test fails, that's a real bug in one engine — investigate before touching tests.

When the user asks "write a program in Donky", remember the limitations: no for, no maps, no sort, no slicing, no string mutation. Programs must be written within those limits.