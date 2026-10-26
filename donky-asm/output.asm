bits 64
default rel
extern printf
extern ExitProcess
global main

section .data
    fmt_int db '%d', 10, 0

section .text
main:
    push rbp
    mov rbp, rsp
    sub rsp, 1024 ; Allocate stack space for variables
    mov rax, 10
    mov [rbp - 8], rax
    mov rax, 20
    mov [rbp - 16], rax
    mov rax, [rbp - 8]
    push rax
    mov rax, [rbp - 16]
    pop rcx
    add rax, rcx
    mov rdx, rax ; 2nd arg: value
    lea rcx, [rel fmt_int] ; 1st arg: format string
    sub rsp, 32 ; Shadow space for Windows API
    call printf
    add rsp, 32
    mov rax, [rbp - 8]
    push rax
    mov rax, [rbp - 16]
    pop rcx
    cmp rcx, rax
    setl al
    movzx rax, al
    cmp rax, 0
    je .L0
    mov rax, 111
    mov rdx, rax ; 2nd arg: value
    lea rcx, [rel fmt_int] ; 1st arg: format string
    sub rsp, 32 ; Shadow space for Windows API
    call printf
    add rsp, 32
    jmp .L1
.L0:
    mov rax, 222
    mov rdx, rax ; 2nd arg: value
    lea rcx, [rel fmt_int] ; 1st arg: format string
    sub rsp, 32 ; Shadow space for Windows API
    call printf
    add rsp, 32
.L1:
    mov rax, 0
    mov [rbp - 24], rax
.L2:
    mov rax, [rbp - 24]
    push rax
    mov rax, 3
    pop rcx
    cmp rcx, rax
    setl al
    movzx rax, al
    cmp rax, 0
    je .L3
    mov rax, [rbp - 24]
    mov rdx, rax ; 2nd arg: value
    lea rcx, [rel fmt_int] ; 1st arg: format string
    sub rsp, 32 ; Shadow space for Windows API
    call printf
    add rsp, 32
    mov rax, [rbp - 24]
    push rax
    mov rax, 1
    pop rcx
    add rax, rcx
    mov [rbp - 24], rax
    jmp .L2
.L3:
    xor ecx, ecx ; Exit code 0
    call ExitProcess
    leave
    ret
