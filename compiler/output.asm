bits 64
default rel
extern printf
extern ExitProcess
global main

section .text
main:
    push rbp
    mov rbp, rsp
    sub rsp, 1024
    mov rax, 10
    push rax
    mov rax, 20
    push rax
    pop rdx
    pop rcx
    sub rsp, 32
    call add
    add rsp, 32
    mov rdx, rax
    lea rcx, [rel fmt_int]
    sub rsp, 32
    call printf
    add rsp, 32
    lea rax, [rel str_0]
    mov rdx, rax
    lea rcx, [rel fmt_str]
    sub rsp, 32
    call printf
    add rsp, 32
    mov rax, 10
    push rax
    pop rcx
    sub rsp, 32
    call fib
    add rsp, 32
    mov rdx, rax
    lea rcx, [rel fmt_int]
    sub rsp, 32
    call printf
    add rsp, 32
    mov rax, 5
    mov [rbp - 8], rax
    mov rax, 7
    mov [rbp - 16], rax
    mov rax, [rbp - 8]
    push rax
    mov rax, [rbp - 16]
    pop rcx
    imul rax, rcx
    mov rdx, rax
    lea rcx, [rel fmt_int]
    sub rsp, 32
    call printf
    add rsp, 32
    xor ecx, ecx
    call ExitProcess
    leave
    ret

add:
    push rbp
    mov rbp, rsp
    sub rsp, 256
    mov [rbp - 8], rcx
    mov [rbp - 16], rdx
    mov rax, [rbp - 8]
    push rax
    mov rax, [rbp - 16]
    pop rcx
    add rax, rcx
    leave
    ret
    mov rax, 0
    leave
    ret

fib:
    push rbp
    mov rbp, rsp
    sub rsp, 256
    mov [rbp - 8], rcx
    mov rax, [rbp - 8]
    push rax
    mov rax, 2
    pop rcx
    cmp rcx, rax
    setl al
    movzx rax, al
    cmp rax, 0
    je .L0
    mov rax, [rbp - 8]
    leave
    ret
    jmp .L1
.L0:
.L1:
    mov rax, [rbp - 8]
    push rax
    mov rax, 1
    pop rcx
    sub rcx, rax
    mov rax, rcx
    push rax
    pop rcx
    sub rsp, 32
    call fib
    add rsp, 32
    push rax
    mov rax, [rbp - 8]
    push rax
    mov rax, 2
    pop rcx
    sub rcx, rax
    mov rax, rcx
    push rax
    pop rcx
    sub rsp, 32
    call fib
    add rsp, 32
    pop rcx
    add rax, rcx
    leave
    ret
    mov rax, 0
    leave
    ret

section .data
    fmt_int db '%d', 10, 0
    fmt_str db '%s', 10, 0
    str_0 db 72, 101, 108, 108, 111, 44, 32, 68, 111, 110, 107, 121, 33, 0
