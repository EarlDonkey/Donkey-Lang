use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;
use crate::heap::{Value, MapKey, Heap, HeapObject};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub enum OpCode {
    Constant(Value), Add, Sub, Mul, Div, Eq, NotEq, Lt, Gt, LtEq, GtEq,
    Print, Jump(usize), JumpIfFalse(usize), GetLocal(usize), SetLocal(usize),
    DefineFunction(String, usize, usize),
    Call(usize), Builtin(String, usize), MethodCall(String, usize),
    Return, Array(usize), Map(usize), Struct(String, Vec<String>),
    FieldAccess(String), FieldSet(String),
    Index, IndexSet,
    Negate, Not,
    Dup, Pop, Halt,
}

pub struct Compiler {
    code: Vec<OpCode>,
    locals: HashMap<String, usize>,
    next_local: usize,
    functions: Vec<Vec<OpCode>>,
}

impl Compiler {
    pub fn new() -> Self { Compiler { code: Vec::new(), locals: HashMap::new(), next_local: 0, functions: Vec::new() } }

    pub fn compile(mut self, stmts: Vec<Stmt>) -> (Vec<OpCode>, Vec<Vec<OpCode>>) {
        for stmt in stmts { self.compile_stmt(stmt); }
        self.code.push(OpCode::Halt);
        (self.code, self.functions)
    }

    fn compile_stmt(&mut self, stmt: Stmt) {
        match stmt {
            Stmt::Asm(_) => {}
            Stmt::Block(stmts) => { for s in stmts { self.compile_stmt(s); } }
            Stmt::Let(name, expr) => {
                self.compile_expr(expr);
                let slot = self.next_local;
                self.locals.insert(name, slot);
                self.next_local += 1;
                self.code.push(OpCode::SetLocal(slot));
            }
            Stmt::Print(expr) => { self.compile_expr(expr); self.code.push(OpCode::Print); }
            Stmt::Assign(name, expr) => {
                self.compile_expr(expr);
                if let Some(&slot) = self.locals.get(&name) { self.code.push(OpCode::SetLocal(slot)); }
            }
            Stmt::FieldSet(obj_expr, field, val_expr) => {
                self.compile_expr(obj_expr);
                self.compile_expr(val_expr);
                self.code.push(OpCode::FieldSet(field));
            }
            Stmt::IndexSet(name, idx_expr, val_expr) => {
                if let Some(&slot) = self.locals.get(&name) {
                    self.code.push(OpCode::GetLocal(slot));
                } else {
                    self.code.push(OpCode::Constant(Value::Null));
                }
                self.compile_expr(idx_expr);
                self.compile_expr(val_expr);
                self.code.push(OpCode::IndexSet);
            }
            Stmt::ExprStmt(expr) => { self.compile_expr(expr); self.code.push(OpCode::Pop); }
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
            Stmt::Match(target, cases, else_block) => {
                self.compile_expr(target);
                let mut end_jumps = Vec::new();
                for (case_val, block) in cases {
                    self.code.push(OpCode::Dup);
                    self.compile_expr(case_val);
                    self.code.push(OpCode::Eq);
                    let jump_if_false = self.code.len();
                    self.code.push(OpCode::JumpIfFalse(0));
                    self.code.push(OpCode::Pop);
                    self.compile_stmt(*block);
                    let end_jump = self.code.len();
                    self.code.push(OpCode::Jump(0));
                    end_jumps.push(end_jump);
                    let next_case = self.code.len();
                    self.code[jump_if_false] = OpCode::JumpIfFalse(next_case);
                }
                self.code.push(OpCode::Pop);
                if let Some(eb) = else_block { self.compile_stmt(*eb); }
                let end = self.code.len();
                for jump in end_jumps { self.code[jump] = OpCode::Jump(end); }
            }
            Stmt::Function(name, params, body) => {
                let mut sub_compiler = Compiler::new();
                let mut final_params = params;
                if name.contains('.') { 
                    if final_params.first().map_or(true, |p| p != "self") {
                        final_params.insert(0, "self".to_string()); 
                    }
                }
                for (i, p) in final_params.iter().enumerate() { sub_compiler.locals.insert(p.clone(), i); }
                sub_compiler.next_local = final_params.len();
                sub_compiler.compile_stmt(*body);
                sub_compiler.code.push(OpCode::Return);
                let idx = self.functions.len();
                self.functions.push(sub_compiler.code);
                let slot = self.next_local;
                self.locals.insert(name.clone(), slot);
                self.next_local += 1;
                self.code.push(OpCode::DefineFunction(name, idx, slot));
            }
            Stmt::Return(expr) => {
                if let Some(e) = expr { self.compile_expr(e); } else { self.code.push(OpCode::Constant(Value::Null)); }
                self.code.push(OpCode::Return);
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
                if let Some(&slot) = self.locals.get(&name) { self.code.push(OpCode::GetLocal(slot)); } 
                else { self.code.push(OpCode::Constant(Value::Null)); }
            }
            Expr::Array(elements) => {
                let len = elements.len();
                for el in elements { self.compile_expr(el); }
                self.code.push(OpCode::Array(len));
            }
            Expr::Map(pairs) => {
                let len = pairs.len();
                for (k, v) in pairs { self.compile_expr(k); self.compile_expr(v); }
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
            Expr::FieldAccess(obj, field) => { self.compile_expr(*obj); self.code.push(OpCode::FieldAccess(field)); }
            Expr::Index(target, index) => { self.compile_expr(*target); self.compile_expr(*index); self.code.push(OpCode::Index); }
            Expr::MethodCall(target, method, args) => {
                self.compile_expr(*target);
                for arg in args.iter().rev() { self.compile_expr(arg.clone()); }
                self.code.push(OpCode::MethodCall(method, args.len()));
            }
            Expr::Call(name, args) => {
                for arg in args.iter().rev() { self.compile_expr(arg.clone()); }
                if name == "str" || name == "len" || name == "push" || name == "pop" || name == "split" || name == "join" || name == "upper" || name == "lower" || name == "trim" || name == "replace" || name == "contains" || name == "keys" {
                    self.code.push(OpCode::Builtin(name, args.len()));
                } else if let Some(&slot) = self.locals.get(&name) {
                    self.code.push(OpCode::GetLocal(slot));
                    self.code.push(OpCode::Call(args.len()));
                }
            }
            Expr::Unary(op, right) => {
                self.compile_expr(*right);
                match op {
                    TokenType::Minus => self.code.push(OpCode::Negate),
                    TokenType::Bang => self.code.push(OpCode::Not),
                    _ => {}
                }
            }
            Expr::Binary(left, op, right) => {
                self.compile_expr(*left); self.compile_expr(*right);
                match op {
                    TokenType::Plus => self.code.push(OpCode::Add), TokenType::Minus => self.code.push(OpCode::Sub),
                    TokenType::Star => self.code.push(OpCode::Mul), TokenType::Slash => self.code.push(OpCode::Div),
                    TokenType::EqEq => self.code.push(OpCode::Eq), TokenType::NotEq => self.code.push(OpCode::NotEq),
                    TokenType::Lt => self.code.push(OpCode::Lt), TokenType::Gt => self.code.push(OpCode::Gt),
                    TokenType::LtEq => self.code.push(OpCode::LtEq), TokenType::GtEq => self.code.push(OpCode::GtEq),
                    _ => {}
                }
            }
            Expr::Ternary(cond, then_b, else_b) => {
                self.compile_expr(*cond);
                let jump_if_false = self.code.len();
                self.code.push(OpCode::JumpIfFalse(0));
                self.compile_expr(*then_b);
                let jump_over = self.code.len();
                self.code.push(OpCode::Jump(0));
                let else_target = self.code.len();
                self.code[jump_if_false] = OpCode::JumpIfFalse(else_target);
                self.compile_expr(*else_b);
                let end = self.code.len();
                self.code[jump_over] = OpCode::Jump(end);
            }
            _ => {}
        }
    }
}

pub struct VM { 
    stack: Vec<Value>, 
    locals: Vec<Value>, 
    frames: Vec<Vec<Value>>,
    functions: Vec<Vec<OpCode>>, 
    functions_by_name: HashMap<String, usize>,
    call_stack: Vec<usize>, 
    pub heap: Heap 
}

impl VM {
    pub fn new() -> Self { 
        VM { 
            stack: Vec::new(), 
            locals: Vec::new(), 
            frames: Vec::new(),
            functions: Vec::new(), 
            functions_by_name: HashMap::new(),
            call_stack: Vec::new(), 
            heap: Heap::new() 
        } 
    }
    
    fn get_roots(&self) -> Vec<Value> { 
        let mut r = Vec::new(); r.extend(self.stack.clone()); r.extend(self.locals.clone()); r 
    }

    pub fn run(&mut self, code: Vec<OpCode>, funcs: Vec<Vec<OpCode>>) {
        self.functions = funcs;
        let mut ip = 0;
        let mut current_code = code.clone();

        while ip < current_code.len() {
            if self.heap.needs_gc() { let roots = self.get_roots(); self.heap.collect_garbage(&roots); }
            
            match &current_code[ip] {
                OpCode::Constant(v) => self.stack.push(v.clone()),
                OpCode::Add => { 
                    let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); 
                    match (a, b) { 
                        (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Number(x + y)), 
                        (Value::String(x), Value::String(y)) => self.stack.push(Value::String(format!("{}{}", x, y))), 
                        _ => self.stack.push(Value::Null) 
                    } 
                }
                OpCode::Sub => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); if let (Value::Number(x), Value::Number(y)) = (a, b) { self.stack.push(Value::Number(x - y)); } }
                OpCode::Mul => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); if let (Value::Number(x), Value::Number(y)) = (a, b) { self.stack.push(Value::Number(x * y)); } }
                OpCode::Div => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); if let (Value::Number(x), Value::Number(y)) = (a, b) { self.stack.push(Value::Number(x / y)); } }
                OpCode::Eq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() == b.to_string())); }
                OpCode::NotEq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); self.stack.push(Value::Bool(a.to_string() != b.to_string())); }
                OpCode::Lt => { 
                    let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); 
                    match (&a, &b) { 
                        (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x < y)), 
                        _ => self.stack.push(Value::Bool(a.to_string() < b.to_string())) 
                    } 
                }
                OpCode::Gt => { 
                    let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); 
                    match (&a, &b) { 
                        (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x > y)), 
                        _ => self.stack.push(Value::Bool(a.to_string() > b.to_string())) 
                    } 
                }
                OpCode::LtEq => { 
                    let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); 
                    match (&a, &b) { 
                        (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x <= y)), 
                        _ => self.stack.push(Value::Bool(a.to_string() <= b.to_string())) 
                    } 
                }
                OpCode::GtEq => { 
                    let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); 
                    match (&a, &b) { 
                        (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x >= y)), 
                        _ => self.stack.push(Value::Bool(a.to_string() >= b.to_string())) 
                    } 
                }
                OpCode::Negate => {
                    let v = self.stack.pop().unwrap_or(Value::Null);
                    if let Value::Number(n) = v { self.stack.push(Value::Number(-n)); }
                    else { self.stack.push(Value::Null); }
                }
                OpCode::Not => {
                    let v = self.stack.pop().unwrap_or(Value::Null);
                    if let Value::Bool(b) = v { self.stack.push(Value::Bool(!b)); }
                    else { self.stack.push(Value::Null); }
                }
                OpCode::Print => { let val = self.stack.pop().unwrap_or(Value::Null); println!("{}", val.to_string()); }
                
                OpCode::DefineFunction(name, idx, slot) => {
                    if self.locals.len() <= *slot { self.locals.resize(*slot + 1, Value::Null); }
                    self.locals[*slot] = Value::Number(*idx as f64);
                    self.functions_by_name.insert(name.clone(), *idx);
                }
                
                OpCode::Builtin(name, _) => {
                    if name == "str" { 
                        let v = self.stack.pop().unwrap_or(Value::Null); 
                        self.stack.push(Value::String(v.to_string())); 
                    }
                    else if name == "len" { 
                        let v = self.stack.pop().unwrap_or(Value::Null); 
                        if let Value::String(s) = v { self.stack.push(Value::Number(s.len() as f64)); } 
                        else if let Value::Array(idx) = v { 
                            if let HeapObject::Array(arr) = self.heap.get(idx) { self.stack.push(Value::Number(arr.len() as f64)); } 
                            else { self.stack.push(Value::Number(0.0)); }
                        }
                        else { self.stack.push(Value::Number(0.0)); } 
                    }
                    else if name == "push" { 
                        let v = self.stack.pop().unwrap_or(Value::Null); let t = self.stack.pop().unwrap_or(Value::Null);
                        if let Value::Array(idx) = t { 
                            if let HeapObject::Array(arr) = self.heap.get_mut(idx) { arr.push(v); } 
                        } 
                        self.stack.push(Value::Null); 
                    }
                    else if name == "split" { 
                        let sep = self.stack.pop().unwrap_or(Value::Null); let s = self.stack.pop().unwrap_or(Value::Null);
                        if let (Value::String(sv), Value::String(sepv)) = (s, sep) {
                            let parts: Vec<Value> = sv.split(&sepv).map(|p| Value::String(p.to_string())).collect();
                            let idx = self.heap.alloc(HeapObject::Array(parts));
                            self.stack.push(Value::Array(idx));
                        } else { self.stack.push(Value::Null); } 
                    }
                    else if name == "upper" { 
                        let s = self.stack.pop().unwrap_or(Value::Null); 
                        if let Value::String(sv) = s { self.stack.push(Value::String(sv.to_uppercase())); } 
                        else { self.stack.push(Value::Null); } 
                    }
                    else if name == "lower" { 
                        let s = self.stack.pop().unwrap_or(Value::Null); 
                        if let Value::String(sv) = s { self.stack.push(Value::String(sv.to_lowercase())); } 
                        else { self.stack.push(Value::Null); } 
                    }
                    else if name == "trim" {
                        let s = self.stack.pop().unwrap_or(Value::Null);
                        if let Value::String(sv) = s { self.stack.push(Value::String(sv.trim().to_string())); }
                        else { self.stack.push(Value::Null); }
                    }
                }

                OpCode::Dup => { let top = self.stack.last().cloned().unwrap_or(Value::Null); self.stack.push(top); }
                OpCode::Pop => { self.stack.pop(); }
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
                
                OpCode::MethodCall(method, arg_count) => {
                    let mut args = Vec::new();
                    for _ in 0..*arg_count { args.push(self.stack.pop().unwrap_or(Value::Null)); }
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    
                    if let Value::Struct(idx) = target {
                        let struct_name = if let HeapObject::Struct(n, _) = self.heap.get(idx) { n.clone() } else { "".to_string() };
                        let full_name = format!("{}.{}", struct_name, method);
                        if let Some(&func_idx) = self.functions_by_name.get(&full_name) {
                            self.call_stack.push(ip);
                            self.frames.push(std::mem::replace(&mut self.locals, Vec::new()));
                            let mut final_args = vec![Value::Struct(idx)];
                            final_args.extend(args);
                            self.locals = final_args;
                            current_code = self.functions[func_idx].clone();
                            ip = 0; continue;
                        }
                    }
                }
                
                OpCode::Call(arg_count) => {
                    let func_idx_val = self.stack.pop().unwrap_or(Value::Null);
                    if let Value::Number(idx) = func_idx_val {
                        self.call_stack.push(ip);
                        self.frames.push(std::mem::replace(&mut self.locals, Vec::new()));
                        let new_locals: Vec<Value> = (0..*arg_count).map(|_| self.stack.pop().unwrap_or(Value::Null)).collect();
                        self.locals = new_locals;
                        current_code = self.functions[idx as usize].clone();
                        ip = 0; continue;
                    }
                }
                OpCode::Return => {
                    let ret_val = self.stack.pop().unwrap_or(Value::Null);
                    if let Some(ret_ip) = self.call_stack.pop() {
                        self.locals = self.frames.pop().unwrap_or_default();
                        self.stack.push(ret_val);
                        current_code = code.clone();
                        ip = ret_ip;
                    } else { break; }
                }
                OpCode::Array(size) => {
                    let mut elements = Vec::new();
                    for _ in 0..*size { elements.push(self.stack.pop().unwrap_or(Value::Null)); }
                    elements.reverse();
                    let idx = self.heap.alloc(HeapObject::Array(elements));
                    self.stack.push(Value::Array(idx));
                }
                OpCode::Map(size) => {
                    let mut map = HashMap::new();
                    for _ in 0..*size { 
                        let v = self.stack.pop().unwrap_or(Value::Null); let k = self.stack.pop().unwrap_or(Value::Null); 
                        if let Ok(key) = MapKey::from_value(&k) { map.insert(key, v); } 
                    }
                    let idx = self.heap.alloc(HeapObject::Map(map));
                    self.stack.push(Value::Map(idx));
                }
                OpCode::Struct(name, fields) => {
                    let mut map = HashMap::new();
                    for f in fields.iter().rev() { 
                        let v = self.stack.pop().unwrap_or(Value::Null); 
                        map.insert(f.clone(), v); 
                    }
                    let idx = self.heap.alloc(HeapObject::Struct(name.clone(), map));
                    self.stack.push(Value::Struct(idx));
                }
                OpCode::FieldAccess(field) => {
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    if let Value::Struct(idx) = target {
                        if let HeapObject::Struct(_, map) = self.heap.get(idx) {
                            if let Some(v) = map.get(field) { self.stack.push(v.clone()); } else { self.stack.push(Value::Null); }
                        }
                    } else { self.stack.push(Value::Null); }
                }
                OpCode::FieldSet(field) => {
                    let value = self.stack.pop().unwrap_or(Value::Null);
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    if let Value::Struct(idx) = target {
                        if let HeapObject::Struct(_, map) = self.heap.get_mut(idx) {
                            map.insert(field.clone(), value);
                        }
                    }
                    self.stack.push(Value::Null);
                }
                OpCode::Index => {
                    let idx_val = self.stack.pop().unwrap_or(Value::Null);
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    match (target, idx_val) {
                        (Value::Array(arr_idx), Value::Number(n)) => {
                            if let HeapObject::Array(arr) = self.heap.get(arr_idx) {
                                let i = n as usize; if i < arr.len() { self.stack.push(arr[i].clone()); } else { self.stack.push(Value::Null); }
                            } else { self.stack.push(Value::Null); }
                        }
                        (Value::Map(map_idx), k) => {
                            if let Ok(key) = MapKey::from_value(&k) {
                                if let HeapObject::Map(map) = self.heap.get(map_idx) {
                                    if let Some(v) = map.get(&key) { self.stack.push(v.clone()); } else { self.stack.push(Value::Null); }
                                }
                            } else { self.stack.push(Value::Null); }
                        }
                        (Value::Struct(idx), k) => {
                            if let Value::String(key) = k {
                                if let HeapObject::Struct(_, map) = self.heap.get(idx) {
                                    if let Some(v) = map.get(&key) { self.stack.push(v.clone()); } else { self.stack.push(Value::Null); }
                                }
                            } else { self.stack.push(Value::Null); }
                        }
                        _ => self.stack.push(Value::Null),
                    }
                }
                OpCode::IndexSet => {
                    let value = self.stack.pop().unwrap_or(Value::Null);
                    let idx_val = self.stack.pop().unwrap_or(Value::Null);
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    match (target, idx_val) {
                        (Value::Array(arr_idx), Value::Number(n)) => {
                            if let HeapObject::Array(arr) = self.heap.get_mut(arr_idx) {
                                let i = n as usize; if i < arr.len() { arr[i] = value; }
                            }
                        }
                        (Value::Map(map_idx), k) => {
                            if let Ok(key) = MapKey::from_value(&k) {
                                if let HeapObject::Map(map) = self.heap.get_mut(map_idx) {
                                    map.insert(key, value);
                                }
                            }
                        }
                        (Value::Struct(idx), k) => {
                            if let Value::String(key) = k {
                                if let HeapObject::Struct(_, map) = self.heap.get_mut(idx) {
                                    map.insert(key, value);
                                }
                            }
                        }
                        _ => {}
                    }
                    self.stack.push(Value::Null);
                }
                OpCode::Halt => break,
            }
            ip += 1;
        }
    }
}