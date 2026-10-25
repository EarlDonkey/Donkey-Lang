# TODO

## Lexer
- [ ] Emit a BANG token for bare `!`; then add unary `!` to `parse_prefix`.
- [ ] Error on `123abc` instead of lexing as NUMBER + IDENT.
- [ ] Accept `.5` as `0.5`.
- [ ] Merge `-` followed by `>` (adjacent) into a single ARROW token.

## Parser
- [ ] Move `Assign` to a `Stmt` (currently an `Expr` wrapped in `ExprStmt`).
- [ ] Add `&&` / `||` with their own precedence levels.
- [ ] Track line/col on AST nodes for better runtime error messages.

## Later
- [ ] Type checker (M6).
- [ ] Bytecode compiler + VM (M4).
- [ ] REPL.

## Interpreter
- [ ] `!` unary (needs BANG token from lexer).
- [ ] Catch Python `RecursionError` and report "recursion too deep".
- [ ] Built-ins: `len`, `str`, `num`.
- [ ] `%` (modulo), `&&`, `||`.