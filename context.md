# CONTEXT: The Donky Programming Language Project

## 1. Project Overview
Donky is a custom, dynamically typed language. Three implementations:
- **Python Engine** (`donky/`) - reference
- **Rust Engine** (`donky-native/`) - 3MB native binary with **Tree-Walker** AND **Bytecode VM**
- **Self-Hosted Kernel Compiler** (`compiler/`) - x86_64 codegen + bare-metal OS

**Environment:** Windows 11, PowerShell (Admin)
**Toolchain:** Rust/Cargo, NASM, GCC/MinGW, `rust-lld`, QEMU

## 2. Rust Engine Architecture
Uses a **custom Mark-and-Sweep GC** instead of `Rc<RefCell>` for heap objects (arrays, maps, structs).

- **`heap.rs`**:
  - `Heap { objects: Vec<Option<HeapObject>>, marks: Vec<bool>, next_gc: usize }`
  - `HeapObject`: `Array(Vec<Value>)`, `Map(HashMap<MapKey, Value>)`, `Struct(String, HashMap<String, Value>)`
  - `Value::Function { params, body, captured: Option<Rc<RefCell<Vec<HashMap<String, Value>>>>> }` — the captured env is a scope-chain snapshot. GC traces through it.
- **`interpreter.rs`** (Tree-Walker):
  - `Environment { scopes: Vec<HashMap<String, Value>>, structs: ... }` — lexical scope chain
  - `invoke_function()` — saves caller scopes, installs captured/fresh scopes, executes, writes back to captured env if present, restores caller scopes
  - Anonymous `Expr::Function` captures a **snapshot** of the current env at creation
  - Named `Stmt::Function` uses `captured: None` → globals-only (see bug #10)
- **`vm.rs`** (Bytecode VM):
  - Stack + `locals` + `frames: Vec<Vec<Value>>` (call frame stack) + `call_stack`
  - Non-capturing functions only (compiled to `Value::Number(idx)` referencing `self.functions`)
  - **PERFORMANCE: ~9× faster than the Tree-Walker** on `bench.donk` (394ms vs 3495ms for 1M-iteration sum-of-squares). Verified empirically.

## 3. Language Features (Both Engines)
- `let x = 10;`, `fn add(a, b) -> num { ... }`
- `if` / `else` / `while` / `for x in arr` (with `break` / `continue`)
- **Structs + Methods** — `fn Point.move(self, dx, dy)`, auto-injects `self` if not present
- **Pattern Matching:** `match x { 200 { ... } 404 { ... } _ { ... } }`
- **Compound Assignment:** `+=`, `-=`, `*=`, `/=`, `++`, `--`
- **Ternary:** `let x = cond ? a : b;`
- **Anonymous Functions (closures):** `let f = fn(x) -> num { return x + bias; };` — **captures by snapshot**, both engines
- **String Interpolation:** `"Hello ${name + '!'}"` — any expression inside `${...}`
- **Try/Catch/Throw** — both engines, full handler stack unwinding
- **Imports** — both engines, recursive compile/execute
- **Maps, Arrays, Structs**

## 4. Built-ins (Both Engines)
`str` `num` `type` `len` `push` `pop` `keys` `split` `join` `upper` `lower` `trim` `replace` `contains` `str_eq` `char_code` `byte_at` `byte_substr` `bytes_to_str` `read_file` `write_file` `file_exists` `list_dir` `mkdir` `random` `clear_screen` `print_str` `print_char` `read_line` `input` `tcp_listen` `tcp_accept` `tcp_read` `tcp_write` `tcp_close` `http_get`

## 5. Performance Benchmarks
`bench.donk` = sum of squares 1..1,000,000, while loop:
- Tree-Walker: **3494.62 ms** (~3.5 µs/iter)
- Bytecode VM: **393.78 ms** (~0.39 µs/iter)
- **Speedup: 8.87×**

Next-level optimizations for the VM (future Path D):
1. Avoid `.clone()` on Number/Bool pop — they're `Copy`
2. Superinstructions (`GetLocal; Constant; Add; SetLocal` → `IncLocal(slot, k)`)
3. Inline caching for variable slots
4. Hoist `needs_gc()` out of the dispatch loop
5. Register-based opcodes instead of stack
6. Constant pooling for string literals

## 6. CRITICAL: Known Bugs & Pitfalls

1. **The `\r` Bug (OS only):** QEMU sends `\r` and `\n`. OS `read_line` MUST ignore `13`.
2. **Linking (OS only):** Always `rust-lld -flavor gnu -T linker.ld` (MinGW `ld` produces PE).
3. **Array Indexing (OS only):** Avoid `arr[0]` in `kernel.donk`. Use `mem_read8(addr)`.
4. **VM Unary:** MUST have `OpCode::Negate` and `OpCode::Not`. Without them, `-5` silently drops from the stack and breaks method calls.
5. **VM Frame Stack:** On `Call`/`MethodCall`, push caller's `locals` to `frames`, set `locals = args`. On `Return`, restore from `frames`. **Never share locals across calls.**
6. **VM Arg Order:** Compiler emits args **reversed** (`for arg in args.iter().rev()`). VM must **NOT** reverse again after popping. `Array`/`Map` are pushed *forward*, so those **do** need `.reverse()` in the VM. Double-reversal breaks non-commutative calls (`move(5, -5)` becomes `move(-5, 5)`).
7. **Parser: `TokenType::Fn` in `prefix()`** — required for anonymous functions in expression position.
8. **Parser: compound assignment on `FieldAccess`/`Index`** — the fallback path in `statement()` checks for `+=`/`-=`/etc. after `expression(0)`.
9. **Struct `self` injection:** Compiler auto-injects `self` as first param *only if* `params.first() != "self"`.
10. **Named functions don't capture:** `Stmt::Function` uses `captured: None` → they see only globals. Nested named functions (`fn outer() { let x = 10; fn inner() { return x; } }`) fail with `Undefined variable 'x'`. **Workaround:** use `let inner = fn() { return x; };` (anonymous, captures correctly). The real fix requires `Rc<RefCell<HashMap>>` globals + `Stmt::Function` capturing the env, but it's non-blocking for most code.
11. **Closure snapshot semantics:** `let x = 10; let f = fn() { return x; }; x = 20; f()` returns `10`, not `20`. Closures capture a snapshot of their environment at creation. For live bindings, `Environment.scopes` would need to be shared via `Rc<RefCell<...>>`.
12. **No chained calls:** `f(1)(2)` is a parse error. `Call(String, ...)` requires a bare identifier. Workaround: intermediate `let`s, or add `Expr::CallOn(Box<Expr>, Vec<Expr>)` to the AST + postfix `(` handling + `OpCode::DynamicCall` in the VM.

## 7. Build Commands

```powershell
cd C:\Users\user\Desktop\Donky-Lang\donky-native
cargo build --release
.\target\release\donky-native.exe script.donk       # Tree-Walker
.\target\release\donky-native.exe vm script.donk    # Bytecode VM

# Kernel
cd C:\Users\user\Desktop\Donky-Lang\compiler
$lld = "C:\Users\user\.rustup\toolchains\stable-x86_64-pc-windows-msvc\lib\rustlib\x86_64-pc-windows-msvc\bin\rust-lld.exe"
..\donky-native\target\release\donky-native.exe compile_kernel.donk kernel.donk
nasm -f elf64 kernel.asm -o kernel.o
& $lld -flavor gnu -T linker.ld kernel.o -o kernel.elf
& "C:\Program Files\qemu\qemu-system-x86_64.exe" -kernel kernel.elf -drive file=disk.img,format=raw,if=ide

Kernel Build \& Boot

cd C:\\Users\\user\\Desktop\\Donky-Lang\\compiler

$lld = "C:\\Users\\user\\.rustup\\toolchains\\stable-x86\_64-pc-windows-msvc\\lib\\rustlib\\x86\_64-pc-windows-msvc\\bin\\rust-lld.exe"



\# 1. Compile Donky to Assembly

..\\donky-native\\target\\release\\donky-native.exe compile\_kernel.donk kernel.donk



\# 2. Assemble and Link

nasm -f elf64 kernel.asm -o kernel.o

\& $lld -flavor gnu -T linker.ld kernel.o -o kernel.elf



\# 3. Boot in QEMU (with disk)

\& "C:\\Program Files\\qemu\\qemu-system-x86\_64.exe" -kernel kernel.elf -drive file=disk.img,format=raw,if=ide

User's Working Style

Repaste Entire Files: Do not give snippets of code to insert at specific line numbers. The user's local files often drift. Always repaste the complete file.



Namespace Collisions: Because Donky merges imported files into one global scope, functions collide. Use prefixes (p\_ for parser, gen\_ for codegen).



Short-circuiting: The Rust interpreter now short-circuits \&\& and ||, but earlier bugs required explicitly checking contains(map, key) before indexing to avoid crashes.



Tone: Collaborative, technical, ready to dive into deep systems programming.


7. VM Gaps (Not Yet Implemented)
Stmt::Import

Stmt::Try/Catch/Throw

Stmt::For loops (only while)

Closures

Many built-ins (only a subset is implemented in the VM)

Expr::Function (anonymous functions in expression position)

8. User's Working Style
Repaste full files. Never snippets.

Incremental. Add one feature at a time, test, commit.

Tone: Collaborative, technical, systems-focused.

text

---

### What next? Three solid options:

**Option A — Fill the VM gaps.**
Right now the VM is a "second-class citizen" — it can't do imports, try/catch, for loops, or closures. Every gap means any real Donky program (github_dash, markdown, JSON) can't run on the fast VM. Closing these would make the VM as powerful as the Tree-Walker and unblock future performance work.

**Option B — Build a real app.**
Pick a project (a JSON parser in Donky, a markdown SSG, an HTTP server, a text adventure game) and write it entirely in Donky. You'll hit new edge cases that reveal language design flaws. This is where languages actually get hardened.

**Option C — Back to the OS.**
The kernel is stuck at the disk driver bug. We could either fix it properly or pivot to adding networking, sound, graphics, etc.

**My recommendation:** Option A. You just finished unifying two engines — capitalizing on that by making the VM feature-complete is the natural next step. Once the VM can run anything the Tree-Walker can, you can benchmark and decide whether the VM is actually faster (usually yes, 2-10x on real workloads) and then throw away the Tree-Walker or keep both.

But if you're burnt out on compilers, Option B is a nice change of pace — writing `github_dash.donk` in Donky and watching it fly on both engines would be very satisfying.


7. Only Remaining Language Gap: Closures
fn(x) -> num { return x + outer_var; } will fail at runtime because Value::Function { params, body } doesn't capture the defining environment. Implementing closures requires:

Changing Value::Function to include captured_env: Rc<RefCell<Vec<HashMap<String, Value>>>>

The compiler emitting the captured variables at function-creation time

The Call handler populating self.locals with captured vars + args

Both engines

This is the last big language-level feature before Donky is "feature-complete" by modern standards.

8. Parallel Tracks (For Next Session)
Path B: Write github_dash.donk and json.donk and run them on the VM (not just Tree-Walker). Should be 2-10x faster. Verify by benchmarking test_gc.donk.

Path C: Kernel has a stalled ATA disk driver. The last known good state is a shell that prints but does not persist files. The exact bug: disk_read/disk_write work but ls after touch returns empty. Likely a sector indexing issue in the OS.

Path D: Fill in lib/list.donk, lib/strings.donk, lib/json.donk (all written in pure Donky) to make the stdlib match a real language.

9. User's Working Style
Repaste full files. Never snippets.

Incremental. One feature at a time, test, iterate.

Tone: Collaborative, technical, systems-focused.

Screenshot-driven. User shares terminal output; AI diagnoses from exact error messages.

text

What's next?

1. **Closures** — the last language feature
2. **Benchmarks** — prove the VM is actually faster than the Tree-Walker on real Donky code
3. **Kernel** — unfreeze the ATA driver
4. **Real apps** — write something practical (JSON parser, markdown compiler, HTTP server) and dogfood it

My vote: **Closures** then **Benchmarks**. Once closures work, Donky matches Ruby/Python in capability, and the benchmark gap gives you a real performance story for the README. But if you're burnt out on compilers, **Kernel** is a nice reset — it's low-level systems work, totally different energy.

## 7. Build Commands

```powershell
cd C:\Users\user\Desktop\Donky-Lang\donky-native
cargo build --release
.\target\release\donky-native.exe script.donk       # Tree-Walker
.\target\release\donky-native.exe vm script.donk    # Bytecode VM

# Kernel
cd C:\Users\user\Desktop\Donky-Lang\compiler
$lld = "C:\Users\user\.rustup\toolchains\stable-x86_64-pc-windows-msvc\lib\rustlib\x86_64-pc-windows-msvc\bin\rust-lld.exe"
..\donky-native\target\release\donky-native.exe compile_kernel.donk kernel.donk
nasm -f elf64 kernel.asm -o kernel.o
& $lld -flavor gnu -T linker.ld kernel.o -o kernel.elf
& "C:\Program Files\qemu\qemu-system-x86_64.exe" -kernel kernel.elf -drive file=disk.img,format=raw,if=ide
8. Remaining Gaps & Follow-Ups
Language:

Chained calls (f(1)(2)) — small parser + AST + VM change

Named function closure capture (bug #10)

Live binding closures (bug #11)

Optional chaining, pipe operator, destructuring — advanced

VM optimization (Path D):

5–8× potential speedup from cheap optimizations

Benchmark: bench.donk for loops, test_gc.donk for allocations

OS (Path C):

Kernel stuck at ATA disk driver — disk_read/disk_write work but ls after touch returns empty. Likely a sector indexing or buffer-pointer issue.

Last known good state: shell prints, but file persistence broken

Applications (Path B):

Write github_dash.donk on the VM (currently only works on Tree-Walker)

Build a web server, markdown compiler, or JSON parser fully in Donky

Benchmark real workloads

9. Test Files (Should All Pass on Both Engines)
test_interp.donk — math, arrays, maps, loops, functions

test_advanced.donk — structs + methods + match + compound assignment

test_vm_parity.donk — for/break/continue, anon fn, interpolation, try/catch, method calls

test_closures.donk — counter closures, adder factories, nested closures

test_gc.donk — allocates 5000 arrays, triggers GC sweep

bench.donk — sum of squares 1..1M (perf test)

10. User's Working Style
Repaste full files. Never line-numbered snippets.

Incremental. One feature at a time, test, iterate.

Tone: Collaborative, technical, systems-focused.

Screenshot-driven. Shares exact terminal output; AI diagnoses from error messages.

Ambitious. Wants parity across engines, fast execution, and eventually a bare-metal OS.