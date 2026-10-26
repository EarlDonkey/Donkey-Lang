use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;
use crate::interpreter::Value;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub enum OpCode {
    Constant(Value),
    Add, Sub, Mul, Div,
    Eq, NotEq, Lt, Gt, LtEq, GtEq,
    Print,
    Jump(usize),
    JumpIfFalse(usize),
    GetLocal(usize),
    SetLocal(usize),
    Halt,
}

pub struct Compiler {
    code: Vec<OpCode>,
    locals: HashMap<String, usize>,
    next_local: usize,
}

impl Compiler {
    pub fn new() -> Self {
        Compiler { code: Vec::new(), locals: HashMap::new(), next_local: 0 }
    }

    pub fn compile(mut self, stmts: Vec<Stmt>) -> Vec<OpCode> {
        for stmt in stmts { self.compile_stmt(stmt); }
        self.code.push(OpCode::Halt);
        self.code
    }

    fn compile_stmt(&mut self, stmt: Stmt) {
        match stmt {
            Stmt::Block(stmts) => { for s in stmts { self.compile_stmt(s); } }
            Stmt::Let(name, expr) => {
                self.compile_expr(expr);
                let slot = self.next_local;
                self.locals.insert(name, slot);
                self.next_local += 1;
                self.code.push(OpCode::SetLocal(slot));
            }
            Stmt::Print(expr) => {
                self.compile_expr(expr);
                self.code.push(OpCode::Print);
            }
            Stmt::Assign(name, expr) => {
                self.compile_expr(expr);
                if let Some(&slot) = self.locals.get(&name) { self.code.push(OpCode::SetLocal(slot)); }
            }
            Stmt::ExprStmt(expr) => { self.compile_expr(expr); }
            Stmt::If(cond, then_b, else_b) => {
                self.compile_expr(cond);
                let jump_if_false = self.code.len();
                self.code.push(OpCode::JumpIfFalse(0));
                self.compile_stmt(*then_b);
                
                if let Some(eb) = else_b {
                    let jump_over = self.code.len();
                    self.code.push(OpCode::Jump(0));
                    let else_target = self.code.len();
                    self.code[jump_if_false] = OpCode::JumpIfFalse(else_target);
                    self.compile_stmt(*eb);
                    let end = self.code.len();
                    self.code[jump_over] = OpCode::Jump(end);
                } else {
                    let end = self.code.len();
                    self.code[jump_if_false] = OpCode::JumpIfFalse(end);
                }
            }
            Stmt::While(cond, body) => {
                let loop_start = self.code.len();
                self.compile_expr(cond);
                let jump_if_false = self.code.len();
                self.code.push(OpCode::JumpIfFalse(0));
                self.compile_stmt(*body);
                self.code.push(OpCode::Jump(loop_start));
                let loop_end = self.code.len();
                self.code[jump_if_false] = OpCode::JumpIfFalse(loop_end);
            }
            _ => {}
        }
    }

    fn compile_expr(&mut self, expr: Expr) {
        match expr {
            Expr::Number(n) => self.code.push(OpCode::Constant(Value::Number(n))),
            Expr::String(s) => self.code.push(OpCode::Constant(Value::String(s))),
            Expr::Bool(b) => self.code.push(OpCode::Constant(Value::Bool(b))),
            Expr::Ident(name) => {
                if let Some(&slot) = self.locals.get(&name) { 
                    self.code.push(OpCode::GetLocal(slot)); 
                } else {
                    self.code.push(OpCode::Constant(Value::Null));
                }
            }
            Expr::Binary(left, op, right) => {
                self.compile_expr(*left);
                self.compile_expr(*right);
                match op {
                    TokenType::Plus => self.code.push(OpCode::Add),
                    TokenType::Minus => self.code.push(OpCode::Sub),
                    TokenType::Star => self.code.push(OpCode::Mul),
                    TokenType::Slash => self.code.push(OpCode::Div),
                    TokenType::EqEq => self.code.push(OpCode::Eq),
                    TokenType::NotEq => self.code.push(OpCode::NotEq),
                    TokenType::Lt => self.code.push(OpCode::Lt),
                    TokenType::Gt => self.code.push(OpCode::Gt),
                    TokenType::LtEq => self.code.push(OpCode::LtEq),
                    TokenType::GtEq => self.code.push(OpCode::GtEq),
                    _ => {}
                }
            }
            _ => {}
        }
    }
}

pub struct VM { stack: Vec<Value>, locals: Vec<Value> }

impl VM {
    pub fn new() -> Self { VM { stack: Vec::new(), locals: Vec::new() } }

    pub fn run(&mut self, code: Vec<OpCode>) {
        let mut ip = 0;
        while ip < code.len() {
            match &code[ip] {
                OpCode::Constant(v) => self.stack.push(v.clone()),
                OpCode::Add => {
                    let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null);
                    match (a, b) {
                        (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Number(x + y)),
                        (Value::String(x), Value::String(y)) => self.stack.push(Value::String(format!("{}{}", x, y))),
                        _ => self.stack.push(Value::Null),
                    }
                }
                OpCode::Sub => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); if let (Value::Number(x), Value::Number(y)) = (a, b) { self.stack.push(Value::Number(x - y)); } }
                OpCode::Mul => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); if let (Value::Number(x), Value::Number(y)) = (a, b) { self.stack.push(Value::Number(x * y)); } }
                OpCode::Div => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); if let (Value::Number(x), Value::Number(y)) = (a, b) { self.stack.push(Value::Number(x / y)); } }
                OpCode::Eq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() == b.to_string())); }
                OpCode::NotEq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() != b.to_string())); }
                OpCode::Lt => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() < b.to_string())); }
                OpCode::Gt => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() > b.to_string())); }
                OpCode::LtEq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() <= b.to_string())); }
                OpCode::GtEq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() >= b.to_string())); }
                OpCode::Print => { let val = self.stack.pop().unwrap_or(Value::Null); println!("{}", val.to_string()); }
                OpCode::SetLocal(slot) => { 
                    let val = self.stack.pop().unwrap_or(Value::Null); 
                    if self.locals.len() <= *slot { self.locals.resize(*slot + 1, Value::Null); } 
                    self.locals[*slot] = val; 
                }
                OpCode::GetLocal(slot) => self.stack.push(self.locals[*slot].clone()),
                OpCode::Jump(target) => { ip = *target; continue; }
                OpCode::JumpIfFalse(target) => { 
                    let val = self.stack.pop().unwrap_or(Value::Null); 
                    if !val.is_truthy() { ip = *target; continue; } 
                }
                OpCode::Halt => break,
            }
            ip += 1;
        }
    }
}