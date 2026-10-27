use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;
use crate::interpreter::{Value, MapKey};
use std::collections::HashMap;
use std::rc::Rc;
use std::cell::RefCell;

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
    Call(usize),
    Return,
    Array(usize),
    Map(usize),
    Struct(String, Vec<String>),
    FieldAccess(String),
    Index,
    Halt,
}

pub struct Compiler {
    code: Vec<OpCode>,
    locals: HashMap<String, usize>,
    next_local: usize,
    functions: Vec<Vec<OpCode>>,
}

impl Compiler {
    pub fn new() -> Self {
        Compiler { code: Vec::new(), locals: HashMap::new(), next_local: 0, functions: Vec::new() }
    }

    pub fn compile(mut self, stmts: Vec<Stmt>) -> (Vec<OpCode>, Vec<Vec<OpCode>>) {
        for stmt in stmts { self.compile_stmt(stmt); }
        self.code.push(OpCode::Halt);
        (self.code, self.functions)
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
            Stmt::Function(name, params, body) => {
                let mut sub_compiler = Compiler::new();
                for (i, p) in params.iter().enumerate() { sub_compiler.locals.insert(p.clone(), i); }
                sub_compiler.next_local = params.len();
                sub_compiler.compile_stmt(*body);
                sub_compiler.code.push(OpCode::Return);

                let idx = self.functions.len();
                self.functions.push(sub_compiler.code);

                let slot = self.next_local;
                self.locals.insert(name, slot);
                self.next_local += 1;
                self.code.push(OpCode::Constant(Value::Number(idx as f64)));
                self.code.push(OpCode::SetLocal(slot));
            }
            Stmt::Return(expr) => {
                if let Some(e) = expr { self.compile_expr(e); } else { self.code.push(OpCode::Constant(Value::Null)); }
                self.code.push(OpCode::Return);
            }
            Stmt::StructDef(_, _) => {} // Handled at runtime by StructInit
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
            Expr::Array(elements) => {
                let len = elements.len();
                for el in elements { self.compile_expr(el); }
                self.code.push(OpCode::Array(len));
            }
            Expr::Map(pairs) => {
                let len = pairs.len();
                for (k, v) in pairs {
                    self.compile_expr(k);
                    self.compile_expr(v);
                }
                self.code.push(OpCode::Map(len));
            }
            Expr::StructInit(name, fields) => {
                let mut field_names = Vec::new();
                for (f_name, f_val) in fields {
                    self.compile_expr(f_val);
                    field_names.push(f_name);
                }
                self.code.push(OpCode::Struct(name, field_names));
            }
            Expr::FieldAccess(obj, field) => {
                self.compile_expr(*obj);
                self.code.push(OpCode::FieldAccess(field));
            }
            Expr::Index(target, index) => {
                self.compile_expr(*target);
                self.compile_expr(*index);
                self.code.push(OpCode::Index);
            }
            Expr::Call(name, args) => {
                for arg in args.iter().rev() { self.compile_expr(arg.clone()); }
                if let Some(&slot) = self.locals.get(&name) {
                    self.code.push(OpCode::GetLocal(slot));
                    self.code.push(OpCode::Call(args.len()));
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

pub struct VM { 
    stack: Vec<Value>, 
    locals: Vec<Value>, 
    functions: Vec<Vec<OpCode>>, 
    call_stack: Vec<(usize, usize)> 
}

impl VM {
    pub fn new() -> Self { 
        VM { stack: Vec::new(), locals: Vec::new(), functions: Vec::new(), call_stack: Vec::new() } 
    }

    pub fn run(&mut self, code: Vec<OpCode>, funcs: Vec<Vec<OpCode>>) {
        self.functions = funcs;
        let mut ip = 0;
        let mut current_code = code.clone();

        while ip < current_code.len() {
            match &current_code[ip] {
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
                OpCode::Call(arg_count) => {
                    let func_idx_val = self.stack.pop().unwrap_or(Value::Null);
                    if let Value::Number(idx) = func_idx_val {
                        self.call_stack.push((ip, self.locals.len()));
                        let new_locals: Vec<Value> = (0..*arg_count).map(|_| self.stack.pop().unwrap_or(Value::Null)).collect();
                        self.locals.extend(new_locals.into_iter()); 
                        current_code = self.functions[idx as usize].clone();
                        ip = 0;
                        continue;
                    }
                }
                OpCode::Return => {
                    let ret_val = self.stack.pop().unwrap_or(Value::Null);
                    if let Some((ret_ip, ret_locals_len)) = self.call_stack.pop() {
                        self.locals.truncate(ret_locals_len);
                        self.stack.push(ret_val);
                        current_code = code.clone();
                        ip = ret_ip;
                    } else {
                        break;
                    }
                }
                OpCode::Array(size) => {
                    let mut elements = Vec::new();
                    for _ in 0..*size { elements.push(self.stack.pop().unwrap_or(Value::Null)); }
                    elements.reverse();
                    self.stack.push(Value::Array(Rc::new(RefCell::new(elements))));
                }
                OpCode::Map(size) => {
                    let mut map = HashMap::new();
                    for _ in 0..*size {
                        let v = self.stack.pop().unwrap_or(Value::Null);
                        let k = self.stack.pop().unwrap_or(Value::Null);
                        if let Ok(key) = MapKey::from_value(&k) { map.insert(key, v); }
                    }
                    self.stack.push(Value::Map(Rc::new(RefCell::new(map))));
                }
                OpCode::Struct(name, fields) => {
                    let mut map = HashMap::new();
                    for f in fields.iter().rev() {
                        let v = self.stack.pop().unwrap_or(Value::Null);
                        map.insert(f.clone(), v);
                    }
                    self.stack.push(Value::Struct(name.clone(), Rc::new(RefCell::new(map))));
                }
                OpCode::FieldAccess(field) => {
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    match target {
                        Value::Struct(_, map) => {
                            let borrowed = map.borrow();
                            if let Some(v) = borrowed.get(field) { self.stack.push(v.clone()); } else { self.stack.push(Value::Null); }
                        }
                        _ => self.stack.push(Value::Null),
                    }
                }
                OpCode::Index => {
                    let idx = self.stack.pop().unwrap_or(Value::Null);
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    match (target, idx) {
                        (Value::Array(arr), Value::Number(n)) => {
                            let i = n as usize;
                            let borrowed = arr.borrow();
                            if i < borrowed.len() { self.stack.push(borrowed[i].clone()); } else { self.stack.push(Value::Null); }
                        }
                        (Value::Map(map), k) => {
                            if let Ok(key) = MapKey::from_value(&k) {
                                let borrowed = map.borrow();
                                if let Some(v) = borrowed.get(&key) { self.stack.push(v.clone()); } else { self.stack.push(Value::Null); }
                            } else { self.stack.push(Value::Null); }
                        }
                        _ => self.stack.push(Value::Null),
                    }
                }
                OpCode::Halt => break,
            }
            ip += 1;
        }
    }
}