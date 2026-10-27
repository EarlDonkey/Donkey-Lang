# CONTEXT: The Donky Programming Language Project

## 1. Project Overview
Donky is a custom, dynamically typed language built from scratch. The project has 3 implementations:
- **Python Engine** (`donky/`) - reference
- **Rust Engine** (`donky-native/`) - 3MB native binary with **Tree-Walker** AND **Bytecode VM**
- **Self-Hosted Kernel Compiler** (`compiler/`) - x86_64 codegen + bare-metal OS

**Environment:** Windows 11, PowerShell (Admin)
**Toolchain:** Rust/Cargo, NASM, GCC/MinGW, `rust-lld`, QEMU

## 2. Rust Engine Architecture
Uses a **custom Mark-and-Sweep Garbage Collector** instead of `Rc<RefCell>`:
- **`heap.rs`**: `Heap` with `Vec<Option<HeapObject>>`, `marks: Vec<bool>`, `next_gc: usize`. Methods: `alloc()`, `get()`, `get_mut()`, `needs_gc()`, `collect_garbage(roots)`.
- **`Value`**: heap indices (`usize`). Variants: `Number`, `String`, `Bool`, `Function`, `Array(usize)`, `Map(usize)`, `Struct(usize)`, `Null`.
- **`HeapObject`**: `Array(Vec<Value>)`, `Map(HashMap<MapKey, Value>)`, `Struct(String, HashMap<String, Value>)` — the String is the struct name (for method resolution).

Two engines:
- **Tree-Walker** (`interpreter.rs`): `Environment` (scoped HashMap) + `Heap`. ALL built-ins implemented. Handles try/catch/throw, for loops, imports.
- **Bytecode VM** (`vm.rs`): compiles AST to `OpCode`. Executes with `stack`, `locals`, `frames: Vec<Vec<Value>>` (call frame stack), `functions`, `functions_by_name`, `call_stack`. Uses proper frame stack — critical for method calls.

Both engines produce identical output for the test suite.

## 3. Language Features (Both Engines)
- `let x = 10;`
- `fn add(a, b) -> num { return a + b; }`
- `if`/`else`/`while`/`for x in arr`
- **Structs + Methods:** `fn Point.move(self, dx, dy) { self.x += dx; }`
- **Pattern Matching:** `match x { 200 { ... } 404 { ... } _ { ... } }`
- **Compound Assignment:** `+=`, `-=`, `*=`, `/=`
- **Increment/Decrement:** `++`, `--`
- **Ternary:** `let x = cond ? a : b;`
- **Anonymous Functions:** `let f = fn(x) -> num { return x * 2; };`
- **String Interpolation:** `"Hello ${name}"`
- **Maps, Arrays**
- **Try/Catch/Throw** (Tree-Walker only)
- **Imports** (Tree-Walker only)
- **Closures** (Tree-Walker only)

## 4. Built-ins (Both Engines)
- `str(x)`, `num(s)`, `len(x)`
- `push(arr, v)`, `pop(arr)`, `split(s, sep)`, `join(arr, sep)`
- `upper(s)`, `lower(s)`, `trim(s)`, `replace(s, o, n)`, `contains(x, y)`
- `keys(map)`, `str_eq(a, b)`, `char_code(s)`, `byte_at(s, i)`, `byte_substr(s, a, b)`, `bytes_to_str(arr)`
- `read_file(p)`, `write_file(p, c)`, `file_exists(p)`, `list_dir(p)`, `mkdir(p)`
- `random(max)`, `clear_screen()`, `print_str(s)`, `print_char(c)`, `read_line()`, `input(prompt)`
- `tcp_listen(port)`, `tcp_accept(id)`, `tcp_read(id, max)`, `tcp_write(id, data)`, `tcp_close(id)`, `http_get(url)`

## 5. CRITICAL: Known Bugs & Pitfalls
1. **The `\r` Bug (OS only):** QEMU sends `\r` and `\n` on Enter. OS `read_line` MUST ignore `13`.
2. **Linking (OS only):** Always `rust-lld -flavor gnu -T linker.ld` (MinGW `ld` produces PE).
3. **Array Indexing (OS only):** Avoid `arr[0]` in `kernel.donk`. Use `mem_read8(addr)`.
4. **VM Unary:** MUST have `OpCode::Negate` and `OpCode::Not`. Without these, negative args (like `p.move(5, -5)`) silently drop from the stack, breaking method calls.
5. **VM Frame Stack:** On `Call`/`MethodCall`, push caller's `locals` to `frames` and set `locals = args`. On `Return`, restore from `frames`. Never share `locals` across calls.
6. **Struct Methods `self`:** Compiler auto-injects `self` as first param if not present. Handles both `fn Point.move(self, dx, dy)` and `fn Point.move(dx, dy)`.

## 6. Build Commands
```powershell
cd C:\Users\user\Desktop\Donky-Lang\donky-native
cargo build --release
.\target\release\donky-native.exe script.donk       # Tree-Walker
.\target\release\donky-native.exe vm script.donk    # Bytecode VM

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


