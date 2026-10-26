bits 64

section .text
global _start
_start:
    ; Write 'D O N K Y' to VGA text buffer at 0xB8000
    mov rdi, 0xB8000
    mov rsi, 0x0F4B0F4E0F4F0F44 ; D O N K Y in white/grey
    mov [rdi], rsi
    
    ; Write 'O K' to the next bytes
    mov rsi, 0x0F4B0F4F
    mov [rdi + 8], rsi

    ; Halt
    hlt
    jmp $

; --- PVH boot note for QEMU -kernel ---
section .note.Xen note alloc
align 4
    dd 4                    ; namesz
    dd 8                    ; descsz
    dd 18                   ; XEN_ELFNOTE_PHYS32_ENTRY
    db "Xen", 0
align 4
    dq _start
align 4