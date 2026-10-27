# CONTEXT: The Donky Programming Language Project

## 1. Project Overview
Donky is a custom, general-purpose, dynamically typed programming language built from scratch. The project features a native Rust engine, a Bytecode VM, a self-hosted compiler, and a 64-bit bare-metal operating system that can run a subset of Donky code at runtime.

**Environment:** Windows 11, PowerShell (Admin).
**Toolchain:** Python 3.12, Rust/Cargo, NASM, GCC/MinGW, `rust-lld`, QEMU.

## 2. The Three Implementations
- **Python Engine (`donky/`)**: The original reference implementation.
- **Rust Engine (`donky-native/`)**: A native 3MB `.exe`. Contains a Tree-Walking Interpreter, a Bytecode VM, a SHA-256 Package Manager, and TCP/HTTP networking.
- **Self-Hosted Kernel Compiler (`compiler/`)**: Written in Donky. `codegen_kernel.donk` compiles Donky to x86_64 assembly.

## 3. The Bare-Metal OS (Donky OS v3.0)
- **Bootloader:** 32-bit to 64-bit Long Mode transition.
- **Hardware:** VGA Text Mode, Keyboard (Shift support), ATA PIO Disk Driver, e1000 Network Driver (PCI scanning).
- **Self-Hosting (Donky-on-Donky):** The OS features a built-in math evaluator (`os_eval`) written purely in Donky, proving self-hosted evaluation on bare metal.
- **Inline Assembly:** The OS supports raw assembly via `asm("instruction");`.
- **Commands:** `help`, `sysinfo`, `eval <num> <op> <num>`, `asmtest`, `clear`, `reboot`, `shutdown`.

## 4. Language Features
- **Variables:** `let x = 10;`
- **Functions:** `fn add(a, b) -> num { return a + b; }`
- **Control Flow:** `if`, `while`, `for`, `break`, `continue`.
- **Data:** Structs, Maps (`{}`), Arrays (`[]`), String Interpolation (`${x}`).
- **Inline Assembly (New):** `asm("mov rax, 42");` (Executed in OS, ignored in native).

## 5. CRITICAL: Known Bugs & Pitfalls
1. **The `\r` Bug:** QEMU sends `\r` (13) and `\n` (10) on Enter. The OS assembly `read_line` MUST ignore `13` (`cmp al, 13; je .read_loop`), or string comparisons will fail.
2. **NASM Overflow:** The compiler converts `0x80000000` to `-2147483648` to prevent NASM errors.
3. **No Native Execution of `asm`:** The Rust engine parses `asm("...")` but ignores it. It is purely for the OS.
4. **Array Indexing in OS:** Do not use `arr[0]` inside `kernel.donk`. Use `mem_read8(addr)` to avoid compiler crashes.
5. **Linking:** Always use `rust-lld -flavor gnu -T linker.ld` (MinGW `ld` produces PE binaries).

## 6. Build Commands (PowerShell)
```powershell
# Rust Engine Build:
cd C:\Users\user\Desktop\Donky-Lang\donky-native
cargo build --release

# Kernel Build:
cd C:\Users\user\Desktop\Donky-Lang\compiler
$lld = "C:\Users\user\.rustup\toolchains\stable-x86_64-pc-windows-msvc\lib\rustlib\x86_64-pc-windows-msvc\bin\rust-lld.exe"
..\donky-native\target\release\donky-native.exe compile_kernel.donk kernel.donk
nasm -f elf64 kernel.asm -o kernel.o
& $lld -flavor gnu -T linker.ld kernel.o -o kernel.elf

# Boot:
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



