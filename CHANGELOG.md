# Changelog

All notable changes to Donky are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Donky uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `lib/format.donk` — `format_num`, `repeat`, `pad_left`, `pad_right`

## [1.0.0] - 2026-10-26

First stable release. Donky is a small, complete programming language
with two execution engines (tree-walking interpreter and bytecode VM),
a differential test suite, a type checker, module support, and
PyInstaller packaging.

### Added
- Lexer, Pratt parser, typed AST with source positions
- Tree-walking interpreter
- Bytecode compiler and stack VM
- Closures (upvalues, cells)
- Arrays, maps, strings
- `try` / `catch` / `throw`
- `for` loops over arrays, strings, and maps
- `break` / `continue`
- `else if` chains
- Module system via `import "file.donk";` preprocessing
- Static type checker (catches undefined names, wrong arity,
  return-type mismatches, non-bool conditions, incompatible operands)
- REPL with multi-line input
- Disassembler
- CLI: `run`, `--bytecode`, `--no-types`, `--check-only`
- PyInstaller packaging (`donky.exe`, onedir)
- `lib/list.donk` — `sort_by(arr, f)` (pure Donky, stable, non-mutating)

### Builtins
- `len`, `str`, `num`, `type`
- `push`, `pop`, `sort`
- `split`, `join`, `contains`, `upper`, `lower`, `trim`, `replace`
- `keys`
- `read_file`, `write_file`, `file_exists`
- `input`
- `args` global