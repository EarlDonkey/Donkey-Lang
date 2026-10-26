use std::collections::HashMap;
use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;

pub struct CodeGen {
    output: String,
    variables: HashMap<String, usize>,
    next_slot: usize,
    label_count: usize,
}

impl CodeGen {
    pub fn new() -> Self {
        CodeGen {
            output: String::new(),
            variables: HashMap::new(),
            next_slot: 0,
            label_count: 0,
        }
    }

    fn emit(&mut self, line: &str) {
        self.output.push_str(line);
        self.output.push('\n');
    }

    fn new_label(&mut self) -> String {
        let label = format!(".L{}", self.label_count);
        self.label_count += 1;
        label
    }

    pub fn compile(&mut self, stmts: Vec<Stmt>) -> String {
        self.emit("bits 64");
        self.emit("default rel");
        self.emit("extern printf");
        self.emit("extern ExitProcess");
        self.emit("global main");
        self.emit("");
        self.emit("section .data");
        self.emit("    fmt_int db '%d', 10, 0");
        self.emit("");
        self.emit("section .text");
        self.emit("main:");
        self.emit("    push rbp");
        self.emit("    mov rbp, rsp");
        self.emit("    sub rsp, 1024 ; Allocate stack space for variables");
        
        for stmt in stmts {
            self.gen_stmt(stmt);
        }

        self.emit("    xor ecx, ecx ; Exit code 0");
        self.emit("    call ExitProcess");
        self.emit("    leave");
        self.emit("    ret");
        
        self.output.clone()
    }

    fn gen_stmt(&mut self, stmt: Stmt) {
        match stmt {
            Stmt::Let(name, expr) => {
                self.gen_expr(expr);
                let offset = self.next_slot * 8 + 8;
                self.next_slot += 1;
                self.variables.insert(name, offset);
                self.emit(&format!("    mov [rbp - {}], rax", offset));
            }
            Stmt::Assign(name, expr) => {
                self.gen_expr(expr);
                if let Some(offset) = self.variables.get(&name) {
                    self.emit(&format!("    mov [rbp - {}], rax", offset));
                }
            }
            Stmt::Print(expr) => {
                self.gen_expr(expr);
                self.emit("    mov rdx, rax ; 2nd arg: value");
                self.emit("    lea rcx, [rel fmt_int] ; 1st arg: format string");
                self.emit("    sub rsp, 32 ; Shadow space for Windows API");
                self.emit("    call printf");
                self.emit("    add rsp, 32");
            }
            Stmt::If(cond, then_b, else_b) => {
                let else_label = self.new_label();
                let end_label = self.new_label();
                
                self.gen_expr(cond);
                self.emit("    cmp rax, 0");
                self.emit(&format!("    je {}", else_label));
                
                self.gen_stmt(*then_b);
                self.emit(&format!("    jmp {}", end_label));
                
                self.emit(&format!("{}:", else_label));
                if let Some(eb) = else_b {
                    self.gen_stmt(*eb);
                }
                self.emit(&format!("{}:", end_label));
            }
            Stmt::While(cond, body) => {
                let start_label = self.new_label();
                let end_label = self.new_label();
                
                self.emit(&format!("{}:", start_label));
                self.gen_expr(cond);
                self.emit("    cmp rax, 0");
                self.emit(&format!("    je {}", end_label));
                
                self.gen_stmt(*body);
                self.emit(&format!("    jmp {}", start_label));
                self.emit(&format!("{}:", end_label));
            }
            Stmt::Block(stmts) => {
                for s in stmts { self.gen_stmt(s); }
            }
            _ => {}
        }
    }

    fn gen_expr(&mut self, expr: Expr) {
        match expr {
            Expr::Number(n) => {
                self.emit(&format!("    mov rax, {}", n as i64));
            }
            Expr::Bool(b) => {
                self.emit(&format!("    mov rax, {}", if b { 1 } else { 0 }));
            }
            Expr::Ident(name) => {
                if let Some(offset) = self.variables.get(&name) {
                    self.emit(&format!("    mov rax, [rbp - {}]", offset));
                }
            }
            Expr::Unary(op, right) => {
                self.gen_expr(*right);
                if let TokenType::Minus = op {
                    self.emit("    neg rax");
                }
            }
            Expr::Binary(left, op, right) => {
                self.gen_expr(*left);
                self.emit("    push rax");
                self.gen_expr(*right);
                self.emit("    pop rcx"); // rcx now holds left operand
                
                match op {
                    TokenType::Plus => self.emit("    add rax, rcx"),
                    TokenType::Minus => {
                        self.emit("    sub rcx, rax");
                        self.emit("    mov rax, rcx");
                    }
                    TokenType::Star => self.emit("    imul rax, rcx"),
                    TokenType::Slash | TokenType::Div => {
                        self.emit("    mov rbx, rax");
                        self.emit("    mov rax, rcx");
                        self.emit("    cqo");
                        self.emit("    idiv rbx");
                    }
                    TokenType::EqEq => {
                        self.emit("    cmp rcx, rax");
                        self.emit("    sete al");
                        self.emit("    movzx rax, al");
                    }
                    TokenType::Lt => {
                        self.emit("    cmp rcx, rax");
                        self.emit("    setl al");
                        self.emit("    movzx rax, al");
                    }
                    TokenType::Gt => {
                        self.emit("    cmp rcx, rax");
                        self.emit("    setg al");
                        self.emit("    movzx rax, al");
                    }
                    _ => {}
                }
            }
            _ => {}
        }
    }
}