global _start
section .bss
align 4096
pml4: resb 4096
pdpt: resb 4096
pd:   resb 4096
section .text
bits 32
_start:
    mov edi, pml4
    mov cr3, edi
    xor eax, eax
    mov ecx, 3 * 4096 / 4
    rep stosd
    mov edi, pml4
    mov eax, pdpt
    or eax, 3
    mov [edi], eax
    mov edi, pdpt
    mov eax, pd
    or eax, 3
    mov [edi], eax
    mov edi, pd
    mov eax, 0x83
    mov [edi], eax
    mov eax, 0x200083
    mov [edi + 8], eax
    mov eax, 0x400083
    mov [edi + 16], eax
    mov eax, 0x600083
    mov [edi + 24], eax
    mov eax, cr4
    or eax, 0x20
    mov cr4, eax
    mov ecx, 0xC0000080
    rdmsr
    or eax, 0x100
    wrmsr
    mov eax, cr0
    or eax, 0x80000000
    mov cr0, eax
    lgdt [gdt64_ptr]
    jmp 0x08:long_mode

bits 64
long_mode:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov rbp, 0x90000
    mov rsp, rbp
    sub rsp, 4096
    cld
    mov rdi, 0xB8000
    mov rcx, 2000
    mov ax, 0x0F20
    rep stosw

    lea rax, [rel str_0]
    mov rdi, rax
    call print_str
    call print_newline
    call print_newline
    mov rax, 128
    mov rdi, rax
    call alloc
    mov [rbp - 8], rax
L0:
    mov rax, 1
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L1
    lea rax, [rel str_1]
    mov rdi, rax
    call print_str
    mov rax, [rbp - 8]
    mov rdi, rax
    call read_line
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_2]
    mov rsi, rax
    pop rdi
    call str_eq
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L2
    lea rax, [rel str_3]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L3
L2:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_4]
    mov rsi, rax
    pop rdi
    call str_eq
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L4
    call clear_screen
    lea rax, [rel str_5]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L5
L4:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_6]
    mov rsi, rax
    pop rdi
    call str_eq
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L6
    lea rax, [rel str_7]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L7
L6:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_8]
    mov rsi, rax
    pop rdi
    call str_eq
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L8
    lea rax, [rel str_9]
    mov rdi, rax
    call print_str
    call get_heap
    mov rdi, rax
    call print_int
    call print_newline
    jmp L9
L8:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_10]
    mov rsi, rax
    pop rdi
    call str_starts_with
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L10
    lea rax, [rel str_11]
    mov rdi, rax
    call print_str
    mov rax, [rbp - 8]
    push rax
    mov rax, 5
    mov rsi, rax
    pop rdi
    call str_skip
    mov rdi, rax
    call print_str
    call print_newline
    jmp L11
L10:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_12]
    mov rsi, rax
    pop rdi
    call str_eq
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L12
    lea rax, [rel str_13]
    mov rdi, rax
    call print_str
    call reboot
    jmp L13
L12:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_14]
    mov rsi, rax
    pop rdi
    call str_eq
    push rax
    mov rax, 1
    mov rbx, rax
    pop rax
    cmp rax, rbx
    sete al
    movzx rax, al
    cmp rax, 0
    je L14
    lea rax, [rel str_15]
    mov rdi, rax
    call print_str
    call shutdown
    jmp L15
L14:
    lea rax, [rel str_16]
    mov rdi, rax
    call print_str
    mov rax, [rbp - 8]
    mov rdi, rax
    call print_str
    call print_newline
L15:
L13:
L11:
L9:
L7:
L5:
L3:
    jmp L0
L1:
.halt:
    hlt
    jmp .halt

print_int:
    push rax
    push rbx
    push rcx
    push rdx
    push r8
    push r9
    mov rax, rdi
    mov rbx, 10
    xor rcx, rcx
.int_div:
    xor rdx, rdx
    div rbx
    add dl, '0'
    push rdx
    inc rcx
    test rax, rax
    jnz .int_div
.int_print:
    pop rdx
    mov r8d, [rel vga_cursor]
    lea r9, [0xb8000 + r8]
    mov [r9], dl
    mov byte [r9+1], 0x0f
    add r8, 2
    mov [rel vga_cursor], r8d
    dec rcx
    jnz .int_print
    pop r9
    pop r8
    pop rdx
    pop rcx
    pop rbx
    pop rax
    ret

print_str:
    push rax
    push r8
    push r9
.str_loop:
    mov al, [rdi]
    test al, al
    jz .str_done
    mov r8d, [rel vga_cursor]
    lea r9, [0xb8000 + r8]
    mov [r9], al
    mov byte [r9+1], 0x0f
    add r8d, 2
    mov [rel vga_cursor], r8d
    inc rdi
    jmp .str_loop
.str_done:
    pop r9
    pop r8
    pop rax
    ret

print_char:
    cmp dil, 8
    jne .normal_char
    sub dword [rel vga_cursor], 2
    mov r8d, [rel vga_cursor]
    lea r9, [0xb8000 + r8]
    mov byte [r9], ' '
    mov byte [r9+1], 0x0f
    ret
.normal_char:
    mov r8d, [rel vga_cursor]
    lea r9, [0xb8000 + r8]
    mov [r9], dil
    mov byte [r9+1], 0x0f
    add r8d, 2
    mov [rel vga_cursor], r8d
    ret

print_newline:
    push rax
    push rbx
    push rcx
    push rdx
    push r8
    mov r8d, [rel vga_cursor]
    mov eax, r8d
    xor edx, edx
    mov ecx, 160
    div ecx
    inc eax
    mul ecx
    mov [rel vga_cursor], eax
    pop r8
    pop rdx
    pop rcx
    pop rbx
    pop rax
    ret

clear_screen:
    push rax
    push rcx
    push rdi
    cld
    mov rdi, 0xB8000
    mov rcx, 2000
    mov ax, 0x0F20
    rep stosw
    mov dword [rel vga_cursor], 0
    pop rdi
    pop rcx
    pop rax
    ret

read_line:
    push rbx
    push rcx
    push rdx
    push r8
    mov rbx, rdi
    xor rcx, rcx
.read_loop:
    call keyboard_read_ascii
    cmp al, 10
    je .read_done
    cmp al, 8
    jne .read_store
    test rcx, rcx
    jz .read_loop
    dec rcx
    mov rdi, 8
    call print_char
    jmp .read_loop
.read_store:
    mov rdi, rbx
    add rdi, rcx
    mov [rdi], al
    inc rcx
    mov rdi, rax
    call print_char
    jmp .read_loop
.read_done:
    mov rdi, rbx
    add rdi, rcx
    mov byte [rdi], 0
    call print_newline
    pop r8
    pop rdx
    pop rcx
    pop rbx
    ret

str_eq:
    push rbx
.str_eq_loop:
    mov al, [rdi]
    mov bl, [rsi]
    cmp al, bl
    jne .str_eq_no
    test al, al
    jz .str_eq_yes
    inc rdi
    inc rsi
    jmp .str_eq_loop
.str_eq_yes:
    mov rax, 1
    pop rbx
    ret
.str_eq_no:
    mov rax, 0
    pop rbx
    ret

str_starts_with:
    push rbx
.loop_ss:
    mov al, [rsi]
    test al, al
    jz .yes_ss
    mov bl, [rdi]
    cmp al, bl
    jne .no_ss
    inc rdi
    inc rsi
    jmp .loop_ss
.yes_ss:
    mov rax, 1
    pop rbx
    ret
.no_ss:
    mov rax, 0
    pop rbx
    ret

str_skip:
    mov rax, rdi
.skip_loop:
    test rsi, rsi
    jz .skip_done
    inc rax
    dec rsi
    jmp .skip_loop
.skip_done:
    ret

get_heap:
    mov rax, [rel heap_ptr]
    ret

reboot:
    mov al, 0xFE
    out 0x64, al
    ret

shutdown:
    mov dx, 0x604
    mov ax, 0x2000
    out dx, ax
    ret

keyboard_read_ascii:
.wait_ascii:
    mov dx, 0x64
.kbd_wait_ascii:
    in al, dx
    test al, 1
    jz .kbd_wait_ascii
    mov dx, 0x60
    in al, dx
    test al, 0x80
    jnz .wait_ascii
    movzx rax, al
    lea r8, [rel scancode_map]
    movzx rax, byte [r8 + rax]
    test rax, rax
    jz .wait_ascii
    ret

alloc:
    mov rax, [rel heap_ptr]
    add [rel heap_ptr], rdi
    ret

section .data
align 8
vga_cursor: dd 0
heap_ptr:   dq 0x200000
gdt64:
    dq 0
    dq 0x00209A0000000000
    dq 0x0000920000000000
gdt64_ptr:
    dw $ - gdt64 - 1
    dd gdt64

scancode_map: db 0,0,'1','2','3','4','5','6','7','8','9','0','-','=',8,9,'q','w','e','r','t','y','u','i','o','p','[',']',10,0,'a','s','d','f','g','h','j','k','l',';',39,'`',0,92,'z','x','c','v','b','n','m',',','.','/',0,'*',0,' ',0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
str_5: db `Donky OS Shell v1.4`, 0
str_1: db `donky> `, 0
str_9: db `Current Heap Pointer: `, 0
str_10: db `echo `, 0
str_14: db `shutdown`, 0
str_6: db `about`, 0
str_0: db `Donky OS Shell v1.4`, 0
str_13: db `Rebooting...`, 0
str_11: db `Echo: `, 0
str_2: db `help`, 0
str_4: db `clear`, 0
str_8: db `mem`, 0
str_12: db `reboot`, 0
str_16: db `Unknown command: `, 0
str_7: db `Donky OS - The Native Language`, 0
str_15: db `Shutting down...`, 0
str_3: db `Commands: help, clear, about, mem, echo <text>, reboot, shutdown`, 0
section .note.Xen note alloc
align 4
    dd 4
    dd 8
    dd 18
    db "Xen", 0
align 4
    dq _start
align 4
