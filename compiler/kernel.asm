global _start
section .bss
align 4096
pml4: resb 4096
pdpt: resb 4096
pd:   resb 4096
pd2:  resb 4096
pd3:  resb 4096
pd4:  resb 4096
section .text
bits 32
_start:
    mov edi, pml4
    mov cr3, edi
    xor eax, eax
    mov ecx, 7 * 4096 / 4
    rep stosd
    mov edi, pml4
    mov eax, pdpt
    or eax, 3
    mov [edi], eax
    mov edi, pdpt
    mov eax, pd
    or eax, 3
    mov [edi], eax
    add eax, 4096
    mov [edi + 8], eax
    add eax, 4096
    mov [edi + 16], eax
    add eax, 4096
    mov [edi + 24], eax
    mov edi, pd
    mov eax, 0x83
    mov ecx, 512
.map_loop:
    mov [edi], eax
    add eax, 0x200000
    add edi, 8
    loop .map_loop
    mov edi, pd2
    mov ecx, 512
.map_loop2:
    mov [edi], eax
    add eax, 0x200000
    add edi, 8
    loop .map_loop2
    mov edi, pd3
    mov ecx, 512
.map_loop3:
    mov [edi], eax
    add eax, 0x200000
    add edi, 8
    loop .map_loop3
    mov edi, pd4
    mov ecx, 512
.map_loop4:
    mov [edi], eax
    add eax, 0x200000
    add edi, 8
    loop .map_loop4
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
    mov rax, 512
    mov rdi, rax
    call alloc
    mov [rbp - 16], rax
    mov rax, 4096
    mov rdi, rax
    call alloc
    mov [rbp - 24], rax
    mov rax, 2048
    mov rdi, rax
    call alloc
    mov [rbp - 32], rax
    lea rax, [rel str_1]
    mov rdi, rax
    call print_str
    call print_newline
    mov rax, 0
    mov [rbp - 40], rax
    lea rax, [rel str_2]
    mov rdi, rax
    call print_str
    call print_newline
    mov rax, [rbp - 40]
    push rax
    mov rax, 0
    mov rbx, rax
    pop rax
    add rax, rbx
    mov rdi, rax
    call mem_read32
    mov [rbp - 48], rax
    mov rax, [rbp - 40]
    push rax
    mov rax, 0
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, [rbp - 48]
    push rax
    mov rax, [rbp - 48]
    push rax
    mov rax, 32
    mov rbx, rax
    pop rax
    xor rdx, rdx
    div rbx
    mov rax, rdx
    mov rbx, rax
    pop rax
    sub rax, rbx
    push rax
    mov rax, [rbp - 48]
    push rax
    mov rax, 16
    mov rbx, rax
    pop rax
    xor rdx, rdx
    div rbx
    mov rax, rdx
    mov rbx, rax
    pop rax
    add rax, rbx
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, 2
    push rax
    mov rax, 8
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 256
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 262144
    mov rbx, rax
    pop rax
    add rax, rbx
    mov [rbp - 56], rax
    mov rax, [rbp - 40]
    push rax
    mov rax, 1024
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, [rbp - 56]
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 40]
    push rax
    mov rax, 14336
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, [rbp - 24]
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 40]
    push rax
    mov rax, 14340
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 0
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 40]
    push rax
    mov rax, 14344
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 128
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 40]
    push rax
    mov rax, 14352
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 0
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 40]
    push rax
    mov rax, 14360
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 0
    mov rsi, rax
    pop rdi
    call mem_write32
    lea rax, [rel str_3]
    mov rdi, rax
    call print_str
    call print_newline
    mov rax, [rbp - 32]
    push rax
    mov rax, 0
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 305419858
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 32]
    push rax
    mov rax, 4
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 1465263122
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 32]
    push rax
    mov rax, 8
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 134217728
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 32]
    push rax
    mov rax, 14
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    lea rax, [rel str_4]
    mov rsi, rax
    pop rdi
    call str_copy
    mov rax, [rbp - 24]
    push rax
    mov rax, 0
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, [rbp - 32]
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 24]
    push rax
    mov rax, 4
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 0
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 24]
    push rax
    mov rax, 8
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 36
    push rax
    mov rax, 184549376
    mov rbx, rax
    pop rax
    add rax, rbx
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 40]
    push rax
    mov rax, 14360
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 1
    mov rsi, rax
    pop rdi
    call mem_write32
    lea rax, [rel str_5]
    mov rdi, rax
    call print_str
    call print_newline
    call print_newline
    lea rax, [rel str_6]
    mov rdi, rax
    call print_str
    call print_newline
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
    lea rax, [rel str_7]
    mov rdi, rax
    call print_str
    mov rax, [rbp - 8]
    mov rdi, rax
    call read_line
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
    je L2
    lea rax, [rel str_9]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L3
L2:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_10]
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
    lea rax, [rel str_11]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L5
L4:
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
    je L6
    call clear_screen
    lea rax, [rel str_13]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L7
L6:
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
    je L8
    lea rax, [rel str_15]
    mov rdi, rax
    call print_str
    call print_newline
    mov rax, 1
    push rax
    mov rax, [rbp - 16]
    mov rsi, rax
    pop rdi
    call disk_read
    mov rax, [rbp - 16]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L9
L8:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_16]
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
    mov rax, [rbp - 8]
    push rax
    mov rax, 6
    mov rsi, rax
    pop rdi
    call str_skip
    mov [rbp - 64], rax
    lea rax, [rel str_17]
    mov rdi, rax
    call print_str
    mov rax, [rbp - 64]
    mov rdi, rax
    call print_str
    mov rax, 1
    push rax
    mov rax, [rbp - 16]
    mov rsi, rax
    pop rdi
    call disk_read
    mov rax, [rbp - 16]
    push rax
    mov rax, 10
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, [rbp - 64]
    mov rsi, rax
    pop rdi
    call str_copy
    mov rax, 1
    push rax
    mov rax, [rbp - 16]
    mov rsi, rax
    pop rdi
    call disk_write
    call print_newline
    jmp L11
L10:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_18]
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
    lea rax, [rel str_19]
    mov rdi, rax
    call print_str
    mov rax, 0
    mov [rbp - 72], rax
L13:
    mov rax, [rbp - 72]
    push rax
    mov rax, 512
    mov rbx, rax
    pop rax
    cmp rax, rbx
    setl al
    movzx rax, al
    cmp rax, 0
    je L14
    mov rax, [rbp - 16]
    push rax
    mov rax, [rbp - 72]
    mov rbx, rax
    pop rax
    add rax, rbx
    push rax
    mov rax, 0
    mov rsi, rax
    pop rdi
    call mem_write32
    mov rax, [rbp - 72]
    push rax
    mov rax, 4
    mov rbx, rax
    pop rax
    add rax, rbx
    mov [rbp - 72], rax
    jmp L13
L14:
    mov rax, [rbp - 16]
    push rax
    lea rax, [rel str_20]
    mov rsi, rax
    pop rdi
    call str_copy
    mov rax, 1
    push rax
    mov rax, [rbp - 16]
    mov rsi, rax
    pop rdi
    call disk_write
    lea rax, [rel str_21]
    mov rdi, rax
    call print_str
    call print_newline
    jmp L15
L12:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_22]
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
    je L16
    lea rax, [rel str_23]
    mov rdi, rax
    call print_str
    call reboot
    jmp L17
L16:
    mov rax, [rbp - 8]
    push rax
    lea rax, [rel str_24]
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
    je L18
    lea rax, [rel str_25]
    mov rdi, rax
    call print_str
    call shutdown
    jmp L19
L18:
    lea rax, [rel str_26]
    mov rdi, rax
    call print_str
    call print_newline
L19:
L17:
L15:
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

str_copy:
    push rax
.copy_loop:
    mov al, [rsi]
    mov [rdi], al
    test al, al
    jz .copy_done
    inc rdi
    inc rsi
    jmp .copy_loop
.copy_done:
    pop rax
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

pci_read32:
    push rbx
    shl rdi, 16
    shl rsi, 11
    shl rdx, 8
    mov rbx, rdi
    or rbx, rsi
    or rbx, rdx
    or rbx, rcx
    or rbx, 0x80000000
    mov dx, 0xCF8
    mov eax, ebx
    out dx, eax
    mov dx, 0xCFC
    in eax, dx
    pop rbx
    ret

pci_write32:
    push rbx
    shl rdi, 16
    shl rsi, 11
    shl rdx, 8
    mov rbx, rdi
    or rbx, rsi
    or rbx, rdx
    or rbx, rcx
    or rbx, 0x80000000
    mov dx, 0xCF8
    mov eax, ebx
    out dx, eax
    mov dx, 0xCFC
    mov eax, r8d
    out dx, eax
    pop rbx
    ret

mem_read32:
    mov eax, [rdi]
    ret

mem_write32:
    mov [rdi], esi
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
    cmp al, 0x2A
    je .shift_down
    cmp al, 0x36
    je .shift_down
    cmp al, 0xAA
    je .shift_up
    cmp al, 0xB6
    je .shift_up
    test al, 0x80
    jnz .wait_ascii
    movzx rax, al
    cmp byte [rel shift_pressed], 1
    je .use_shift
    lea r8, [rel scancode_map]
    jmp .lookup
.use_shift:
    lea r8, [rel scancode_map_shift]
.lookup:
    movzx rax, byte [r8 + rax]
    test rax, rax
    jz .wait_ascii
    ret
.shift_down:
    mov byte [rel shift_pressed], 1
    jmp .wait_ascii
.shift_up:
    mov byte [rel shift_pressed], 0
    jmp .wait_ascii

alloc:
    mov rax, [rel heap_ptr]
    add [rel heap_ptr], rdi
    ret

disk_read:
    push rbx
    push rcx
    push rdx
    push rdi
    push rsi
    mov rbx, rsi
    mov ecx, 256
.wait_bsy_read:
    mov dx, 0x1F7
    in al, dx
    test al, 0x80
    jnz .wait_bsy_read
    mov dx, 0x1F6
    mov al, 0xE0
    out dx, al
    mov dx, 0x1F2
    mov al, 1
    out dx, al
    mov dx, 0x1F3
    mov eax, edi
    out dx, al
    mov dx, 0x1F4
    mov eax, edi
    shr eax, 8
    out dx, al
    mov dx, 0x1F5
    mov eax, edi
    shr eax, 16
    out dx, al
    mov dx, 0x1F6
    mov eax, edi
    shr eax, 24
    and al, 0x0F
    or al, 0xE0
    out dx, al
    mov dx, 0x1F7
    mov al, 0x20
    out dx, al
.wait_drq_read:
    in al, dx
    test al, 0x08
    jz .wait_drq_read
    mov dx, 0x1F0
    mov rdi, rbx
.read_loop:
    in ax, dx
    mov [rdi], ax
    add rdi, 2
    dec ecx
    jnz .read_loop
    pop rsi
    pop rdi
    pop rdx
    pop rcx
    pop rbx
    ret

disk_write:
    push rbx
    push rcx
    push rdx
    push rdi
    push rsi
    mov rbx, rsi
    mov ecx, 256
.wait_bsy_write:
    mov dx, 0x1F7
    in al, dx
    test al, 0x80
    jnz .wait_bsy_write
    mov dx, 0x1F6
    mov al, 0xE0
    out dx, al
    mov dx, 0x1F2
    mov al, 1
    out dx, al
    mov dx, 0x1F3
    mov eax, edi
    out dx, al
    mov dx, 0x1F4
    mov eax, edi
    shr eax, 8
    out dx, al
    mov dx, 0x1F5
    mov eax, edi
    shr eax, 16
    out dx, al
    mov dx, 0x1F6
    mov eax, edi
    shr eax, 24
    and al, 0x0F
    or al, 0xE0
    out dx, al
    mov dx, 0x1F7
    mov al, 0x30
    out dx, al
.wait_drq_write:
    in al, dx
    test al, 0x08
    jz .wait_drq_write
    mov dx, 0x1F0
    mov rdi, rbx
.write_loop:
    mov ax, [rdi]
    out dx, ax
    add rdi, 2
    dec ecx
    jnz .write_loop
    pop rsi
    pop rdi
    pop rdx
    pop rcx
    pop rbx
    ret

section .data
align 8
vga_cursor: dd 0
heap_ptr:   dq 0x200000
shift_pressed: db 0
gdt64:
    dq 0
    dq 0x00209A0000000000
    dq 0x0000920000000000
gdt64_ptr:
    dw $ - gdt64 - 1
    dd gdt64

scancode_map: db 0,0,'1','2','3','4','5','6','7','8','9','0','-','=',8,9,'q','w','e','r','t','y','u','i','o','p','[',']',10,0,'a','s','d','f','g','h','j','k','l',';',39,'`',0,92,'z','x','c','v','b','n','m',',','.','/',0,'*',0,' ',0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
scancode_map_shift: db 0,0,'!','@','#','$','%','^','&','*','(',')','_','+',8,9,'Q','W','E','R','T','Y','U','I','O','P','{','}',10,0,'A','S','D','F','G','H','J','K','L',':','"','~',0,'|','Z','X','C','V','B','N','M','<','>','?',0,'*',0,' ',0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
str_1: db `Initializing e1000 at 0xFEB00000...`, 0
str_12: db `clear`, 0
str_11: db `See network output above.`, 0
str_14: db `ls`, 0
str_10: db `net`, 0
str_3: db `Sending packet to host (10.0.2.2)...`, 0
str_20: db `file1.txt (0 bytes)\n`, 0
str_23: db `Rebooting...`, 0
str_24: db `shutdown`, 0
str_25: db `Shutting down...`, 0
str_9: db `Commands: help, clear, about, net, ls, mkfs, reboot, shutdown`, 0
str_18: db `mkfs`, 0
str_8: db `help`, 0
str_13: db `Donky OS Shell v1.7`, 0
str_19: db `Formatting...`, 0
str_22: db `reboot`, 0
str_7: db `donky> `, 0
str_26: db `Unknown command.`, 0
str_16: db `touch `, 0
str_21: db `Formatted Sector 1.`, 0
str_4: db `Hello from Donky e1000!`, 0
str_2: db `Initializing TX Ring...`, 0
str_6: db `Donky OS Shell v1.7 (DonkyFS)`, 0
str_5: db `Packet sent! Check Wireshark.`, 0
str_15: db `Reading directory from Sector 1...`, 0
str_0: db `Donky OS Shell v1.7`, 0
str_17: db `Creating empty file: `, 0
section .note.Xen note alloc
align 4
    dd 4
    dd 8
    dd 18
    db "Xen", 0
align 4
    dq _start
align 4
