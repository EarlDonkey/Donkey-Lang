# Donky Roadmap

Where Donky is going, and what it isn't trying to become.

The scope is deliberately small. Donky is a teaching language that
also happens to be useful for small CLI tools. It is not competing
with Python, Go, or Rust, and it never will.

## Guiding principles

- **Small beats big.** A language that fits in your head is worth
  more than a language that has every feature.
- **Two engines, one spec.** The tree-walker is readable; the VM is
  fast. They must agree. (See "Deferred" for the eventual fate of
  the interpreter.)
- **Stdlib in Donky when possible.** Compiler changes are expensive.
  `.donk` files in `lib/` are cheap and easy to iterate.
- **Every session ends green.** Tests pass, README accurate, commit made.

## Year 1 (next ~6 months of active work)

### v1.1 — Stdlib
- [ ] `lib/list.donk` — `map`, `filter`, `reduce`, `reverse`, `unique`, `flatten`
- [ ] `lib/strings.donk` — `starts_with`, `ends_with`, `index_of`, `slice`, `char_at`
- [ ] `lib/csv.donk` — `parse_line`, `format_line`

### v1.2 — Ergonomics
- [ ] String interpolation `"Hello, ${name}!"`
- [ ] Compound assignment `+=`, `-=`, `*=`, `/=`
- [ ] Range syntax `1..10` for `for` loops
- [x] `sort_by(arr, f)` — shipped in `lib/list.donk`. Promote to a builtin
      (faster sort algorithm) only if real use hits the O(n^2) wall.
- [ ] Better error messages with "did you mean...?" suggestions

### v1.3 — Tooling
- [ ] `donky check file.donk` subcommand
- [ ] `donky fmt file.donk` (pretty-printer / formatter)
- [ ] Bundled stdlib resolved from `sys._MEIPASS` (imports work from the installed exe)

### v2.0 — Structs (breaking change)
- [ ] `struct Point { x: num, y: num }` — records with named fields
- [ ] **Retire the tree-walking interpreter.** All execution goes
      through the VM. Feature cost halves. Differential tests
      retire with it.

## Year 2+

- Namespaced imports (`import "math.donk" as math; math.gcd(...)`)
- Language server (VS Code autocomplete, inline errors, go-to-def)
- Debugger (breakpoints, step-through)
- **Self-hosting** — Donky interpreter written in Donky.
  This is the dream milestone and the North Star.

## Deferred (deliberately not doing)

- Generics
- Macros
- Classes beyond structs
- Concurrency / async
- Package registry
- Web framework
- Compiler speed work

These aren't permanent "no"s, but they'd each individually blow up
the scope. If one becomes essential, that means Donky has grown
past its intended size, and the whole project needs rethinking.

## Cadence

- Small releases (vX.Y) when a group of features is done.
- Breaking changes only in major versions (vX.0).
- Deprecations get one full minor version of warning before removal.
- Gaps of weeks or months are fine. The README, ROADMAP, and
  CHANGELOG exist precisely so returning after a gap is easy.