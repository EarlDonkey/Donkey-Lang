# Changelog

All notable changes to Donky are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Donky uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `lib/format.donk` — `format_num`, `repeat`, `pad_left`, `pad_right`

## [1.0.0] - 2026-19-26

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


## [1.1.1] - 2026-10-26

Patch release. Fixes packaging so `lib/` ships inside the built `.exe`,
and documents the standard library in the README.

### Fixed
- `donky.spec` now bundles `lib/` into `dist/donky/lib/`. The built
  `donky.exe` can now run any program that does `import "../lib/..."`,
  including all bundled examples.

### Added
- README now has a full "Standard library" section documenting all five
  modules (`list`, `format`, `strings`, `csv`, `math`).

### Changed
- `lib/list.donk` — `sort_by(arr, f)` (stable, non-mutating, O(n^2)).
  For descending order, negate a numeric key rather than reversing.
  Note: `reverse(sort_by(...))` flips ties; use a negated key when
  tie order matters.
