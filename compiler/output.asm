bits 64
default rel
extern printf
extern ExitProcess
extern net_init
extern net_connect
extern net_close
global main

section .text
main:
    push rbp
    mov rbp, rsp
    sub rsp, 1024
    mov rax, 7
    mov [rbp - 8], rax
    mov rax, [rbp - 8]
    mov rdx, rax
    lea rcx, [rel fmt_int]
    sub rsp, 32
    call printf
    add rsp, 32
    mov rax, 12345
    mov [rbp - 16], rax
    mov rax, [rbp - 16]
    mov rdx, rax
    lea rcx, [rel fmt_int]
    sub rsp, 32
    call printf
    add rsp, 32
    mov rax, 10
    push rax
    mov rax, 20
    pop rcx
    add rax, rcx
    mov [rbp - 24], rax
    mov rax, [rbp - 24]
    mov rdx, rax
    lea rcx, [rel fmt_int]
    sub rsp, 32
    call printf
    add rsp, 32
    xor ecx, ecx
    call ExitProcess
    leave
    ret

section .data
    fmt_int db '%d', 10, 0
    fmt_str db '%s', 10, 0
