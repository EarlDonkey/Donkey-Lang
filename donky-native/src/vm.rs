use crate::ast::{Expr, Stmt};
use crate::lexer::{TokenType, Lexer};
use crate::parser::Parser;
use crate::heap::{Value, MapKey, Heap, HeapObject};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::sync::{Mutex, OnceLock};
use std::net::{TcpListener, TcpStream};
use std::io::{Read, Write};

static CLIENTS: OnceLock<Mutex<HashMap<usize, TcpStream>>> = OnceLock::new();
static SERVERS: OnceLock<Mutex<HashMap<usize, TcpListener>>> = OnceLock::new();
static COUNTER: OnceLock<Mutex<usize>> = OnceLock::new();

fn get_clients() -> &'static Mutex<HashMap<usize, TcpStream>> { CLIENTS.get_or_init(|| Mutex::new(HashMap::new())) }
fn get_servers() -> &'static Mutex<HashMap<usize, TcpListener>> { SERVERS.get_or_init(|| Mutex::new(HashMap::new())) }
fn get_counter() -> &'static Mutex<usize> { COUNTER.get_or_init(|| Mutex::new(1)) }

#[derive(Debug, Clone)]
pub enum OpCode {
    Constant(Value), Add, Sub, Mul, Div, Eq, NotEq, Lt, Gt, LtEq, GtEq,
    Negate, Not,
    Print, Jump(usize), JumpIfFalse(usize), GetLocal(usize), SetLocal(usize),
    DefineFunction(String, usize, usize),
    Call(usize), Builtin(String, usize), MethodCall(String, usize),
    Return, Array(usize), Map(usize), Struct(String, Vec<String>),
    FieldAccess(String), FieldSet(String),
    Index, IndexSet,
    Interpolate(usize),
    TryStart(usize), TryEnd, Throw,
    Dup, Pop, Halt,
    // Round 1 superinstructions
    BinLocals(TokenType, u32, u32),
    IncLocal(u32, f64),
    AddLocalConst(u32, f64, u32),
    // Round 2 superinstructions
    JumpIfLocalCmpFalse(TokenType, u32, u32, usize),
    AddLocalMulLocal(u32, u32, u32),
    IncLocalJump(u32, f64, usize),
}

// ===================== PEEPHOLE =====================

fn bin_op_of(op: &OpCode) -> Option<TokenType> {
    match op {
        OpCode::Add => Some(TokenType::Plus),
        OpCode::Sub => Some(TokenType::Minus),
        OpCode::Mul => Some(TokenType::Star),
        OpCode::Div => Some(TokenType::Slash),
        OpCode::Eq => Some(TokenType::EqEq),
        OpCode::NotEq => Some(TokenType::NotEq),
        OpCode::Lt => Some(TokenType::Lt),
        OpCode::Gt => Some(TokenType::Gt),
        OpCode::LtEq => Some(TokenType::LtEq),
        OpCode::GtEq => Some(TokenType::GtEq),
        _ => None,
    }
}

fn is_comparison(op: &TokenType) -> bool {
    matches!(op, TokenType::EqEq | TokenType::NotEq | TokenType::Lt | TokenType::Gt | TokenType::LtEq | TokenType::GtEq)
}

fn peephole(code: Vec<OpCode>) -> Vec<OpCode> {
    let mut targets: HashSet<usize> = HashSet::new();
    for op in &code {
        match op {
            OpCode::Jump(t) | OpCode::JumpIfFalse(t) | OpCode::TryStart(t)
            | OpCode::JumpIfLocalCmpFalse(_, _, _, t) | OpCode::IncLocalJump(_, _, t) => { targets.insert(*t); }
            _ => {}
        }
    }

    let mut new_code: Vec<OpCode> = Vec::with_capacity(code.len());
    let mut old_to_new: Vec<usize> = vec![0; code.len() + 1];
    let mut i = 0;
    while i < code.len() {
        old_to_new[i] = new_code.len();

        let clean = |i: usize, n: usize| -> bool {
            !(1..n).any(|j| i + j < code.len() && targets.contains(&(i + j)))
        };

        // Fusion A: GetLocal(a); GetLocal(b); <binop> -> BinLocals(op, a, b)
        if i + 2 < code.len() && clean(i, 3) {
            if let (OpCode::GetLocal(a), OpCode::GetLocal(b)) = (&code[i], &code[i + 1]) {
                if let Some(tok) = bin_op_of(&code[i + 2]) {
                    new_code.push(OpCode::BinLocals(tok, *a as u32, *b as u32));
                    i += 3;
                    continue;
                }
            }
        }

        // Fusion D: BinLocals(cmp, a, b); JumpIfFalse(target) -> JumpIfLocalCmpFalse(cmp, a, b, target)
        if i + 1 < code.len() && clean(i, 2) {
            if let OpCode::BinLocals(op, a, b) = &code[i] {
                if is_comparison(op) {
                    if let OpCode::JumpIfFalse(target) = &code[i + 1] {
                        new_code.push(OpCode::JumpIfLocalCmpFalse(op.clone(), *a, *b, *target));
                        i += 2;
                        continue;
                    }
                }
            }
        }

        // Fusion E: GetLocal(dst); BinLocals(Mul, a, b); Add; SetLocal(dst) -> AddLocalMulLocal(dst, a, b)
        if i + 3 < code.len() && clean(i, 4) {
            if let (OpCode::GetLocal(dst), OpCode::BinLocals(TokenType::Star, a, b), OpCode::Add, OpCode::SetLocal(dst2)) =
                (&code[i], &code[i + 1], &code[i + 2], &code[i + 3])
            {
                if dst == dst2 {
                    new_code.push(OpCode::AddLocalMulLocal(*dst as u32, *a as u32, *b as u32));
                    i += 4;
                    continue;
                }
            }
        }

        // Fusion F: IncLocal(slot, delta); Jump(target) -> IncLocalJump(slot, delta, target)
        if i + 1 < code.len() && clean(i, 2) {
            if let (OpCode::IncLocal(slot, delta), OpCode::Jump(target)) = (&code[i], &code[i + 1]) {
                new_code.push(OpCode::IncLocalJump(*slot, *delta, *target));
                i += 2;
                continue;
            }
        }

        // Fusion B: GetLocal(a); Constant(Number(k)); Add|Sub; SetLocal(a) -> IncLocal(a, ±k)
        if i + 3 < code.len() && clean(i, 4) {
            if let (OpCode::GetLocal(a), OpCode::Constant(Value::Number(k)), OpCode::SetLocal(b)) =
                (&code[i], &code[i + 1], &code[i + 3])
            {
                if a == b {
                    match &code[i + 2] {
                        OpCode::Add => { new_code.push(OpCode::IncLocal(*a as u32, *k)); i += 4; continue; }
                        OpCode::Sub => { new_code.push(OpCode::IncLocal(*a as u32, -*k)); i += 4; continue; }
                        _ => {}
                    }
                }
            }
        }

        // Fusion C: GetLocal(a); Constant(Number(k)); Add|Sub; SetLocal(b) -> AddLocalConst(a, ±k, b)
        if i + 3 < code.len() && clean(i, 4) {
            if let (OpCode::GetLocal(a), OpCode::Constant(Value::Number(k)), OpCode::SetLocal(b)) =
                (&code[i], &code[i + 1], &code[i + 3])
            {
                if a != b {
                    match &code[i + 2] {
                        OpCode::Add => { new_code.push(OpCode::AddLocalConst(*a as u32, *k, *b as u32)); i += 4; continue; }
                        OpCode::Sub => { new_code.push(OpCode::AddLocalConst(*a as u32, -*k, *b as u32)); i += 4; continue; }
                        _ => {}
                    }
                }
            }
        }

        new_code.push(code[i].clone());
        i += 1;
    }
    old_to_new[code.len()] = new_code.len();

    for op in new_code.iter_mut() {
        match op {
            OpCode::Jump(t) | OpCode::JumpIfFalse(t) | OpCode::TryStart(t) => {
                if *t <= code.len() { *t = old_to_new[*t]; }
            }
            OpCode::JumpIfLocalCmpFalse(_, _, _, t) => {
                if *t <= code.len() { *t = old_to_new[*t]; }
            }
            OpCode::IncLocalJump(_, _, t) => {
                if *t <= code.len() { *t = old_to_new[*t]; }
            }
            _ => {}
        }
    }
    new_code
}

// ===================== COMPILER =====================

struct LoopContext { continue_jumps: Vec<usize>, break_jumps: Vec<usize> }

pub struct Compiler {
    code: Vec<OpCode>,
    locals: HashMap<String, usize>,
    next_local: usize,
    functions: Vec<Vec<OpCode>>,
    loop_stack: Vec<LoopContext>,
}

impl Compiler {
    pub fn new() -> Self {
        Compiler { code: Vec::new(), locals: HashMap::new(), next_local: 0, functions: Vec::new(), loop_stack: Vec::new() }
    }

    pub fn compile(mut self, stmts: Vec<Stmt>) -> (Vec<OpCode>, Vec<Vec<OpCode>>) {
        for stmt in stmts { self.compile_stmt(stmt); }
        self.code.push(OpCode::Halt);
        let before_main = self.code.len();
        let main = peephole(self.code);
        if std::env::var("DONKY_DEBUG").is_ok() {
            eprintln!("[PEEPHOLE] main {} -> {}", before_main, main.len());
        }
        let funcs: Vec<Vec<OpCode>> = self.functions.into_iter().map(|f| {
            let before = f.len();
            let after = peephole(f);
            if std::env::var("DONKY_DEBUG").is_ok() {
                eprintln!("[PEEPHOLE] func {} -> {}", before, after.len());
            }
            after
        }).collect();
        (main, funcs)
    }

    fn compile_stmt(&mut self, stmt: Stmt) {
        match stmt {
            Stmt::Asm(_) => {}
            Stmt::Import(path) => {
                let content = match fs::read_to_string(&path) { Ok(c) => c, Err(_) => return };
                let mut lex = Lexer::new(&content);
                let tokens = match lex.tokenize() { Ok(t) => t, Err(_) => return };
                let mut parser = Parser::new(tokens);
                let imported = match parser.parse() { Ok(a) => a, Err(_) => return };
                for s in imported { self.compile_stmt(s); }
            }
            Stmt::Block(stmts) => {
                let saved = self.locals.clone();
                for s in stmts { self.compile_stmt(s); }
                self.locals = saved;
            }
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
                self.compile_expr(obj_expr); self.compile_expr(val_expr);
                self.code.push(OpCode::FieldSet(field));
            }
            Stmt::IndexSet(name, idx_expr, val_expr) => {
                if let Some(&slot) = self.locals.get(&name) { self.code.push(OpCode::GetLocal(slot)); }
                else { self.code.push(OpCode::Constant(Value::Null)); }
                self.compile_expr(idx_expr); self.compile_expr(val_expr);
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
                self.loop_stack.push(LoopContext { continue_jumps: Vec::new(), break_jumps: Vec::new() });
                self.compile_stmt(*body);
                let ctx = self.loop_stack.pop().unwrap();
                self.code.push(OpCode::Jump(loop_start));
                let loop_end = self.code.len();
                self.code[jump_if_false] = OpCode::JumpIfFalse(loop_end);
                for j in ctx.continue_jumps { self.code[j] = OpCode::Jump(loop_start); }
                for j in ctx.break_jumps { self.code[j] = OpCode::Jump(loop_end); }
            }
            Stmt::For(name, iter_expr, body) => {
                let saved = self.locals.clone();
                let iter_slot = self.next_local; self.next_local += 1;
                let idx_slot = self.next_local; self.next_local += 1;
                let x_slot = self.next_local; self.next_local += 1;

                self.compile_expr(iter_expr);
                self.code.push(OpCode::SetLocal(iter_slot));
                self.code.push(OpCode::Constant(Value::Number(0.0)));
                self.code.push(OpCode::SetLocal(idx_slot));

                let loop_start = self.code.len();
                self.code.push(OpCode::GetLocal(idx_slot));
                self.code.push(OpCode::GetLocal(iter_slot));
                self.code.push(OpCode::Builtin("len".to_string(), 1));
                self.code.push(OpCode::Lt);
                let jump_if_false = self.code.len();
                self.code.push(OpCode::JumpIfFalse(0));

                self.code.push(OpCode::GetLocal(iter_slot));
                self.code.push(OpCode::GetLocal(idx_slot));
                self.code.push(OpCode::Index);
                self.code.push(OpCode::SetLocal(x_slot));
                self.locals.insert(name.clone(), x_slot);

                self.loop_stack.push(LoopContext { continue_jumps: Vec::new(), break_jumps: Vec::new() });
                self.compile_stmt(*body);
                let ctx = self.loop_stack.pop().unwrap();

                let incr_start = self.code.len();
                self.code.push(OpCode::IncLocal(idx_slot as u32, 1.0));
                self.code.push(OpCode::Jump(loop_start));
                let end = self.code.len();
                self.code[jump_if_false] = OpCode::JumpIfFalse(end);
                for j in ctx.continue_jumps { self.code[j] = OpCode::Jump(incr_start); }
                for j in ctx.break_jumps { self.code[j] = OpCode::Jump(end); }
                self.locals = saved;
            }
            Stmt::Break => {
                if let Some(ctx) = self.loop_stack.last_mut() {
                    let jump = self.code.len();
                    self.code.push(OpCode::Jump(0));
                    ctx.break_jumps.push(jump);
                }
            }
            Stmt::Continue => {
                if let Some(ctx) = self.loop_stack.last_mut() {
                    let jump = self.code.len();
                    self.code.push(OpCode::Jump(0));
                    ctx.continue_jumps.push(jump);
                }
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
                let mut sub = Compiler::new();
                let mut final_params = params;
                if name.contains('.') {
                    if final_params.first().map_or(true, |p| p != "self") {
                        final_params.insert(0, "self".to_string());
                    }
                }
                for (i, p) in final_params.iter().enumerate() { sub.locals.insert(p.clone(), i); }
                sub.next_local = final_params.len();
                sub.compile_stmt(*body);
                sub.code.push(OpCode::Return);
                let idx = self.functions.len();
                self.functions.push(sub.code);
                let slot = self.next_local;
                self.locals.insert(name.clone(), slot);
                self.next_local += 1;
                self.code.push(OpCode::DefineFunction(name, idx, slot));
            }
            Stmt::Return(expr) => {
                if let Some(e) = expr { self.compile_expr(e); } else { self.code.push(OpCode::Constant(Value::Null)); }
                self.code.push(OpCode::Return);
            }
            Stmt::Throw(expr) => { self.compile_expr(expr); self.code.push(OpCode::Throw); }
            Stmt::Try(try_block, err_name, catch_block) => {
                let try_start = self.code.len();
                self.code.push(OpCode::TryStart(0));
                self.compile_stmt(*try_block);
                self.code.push(OpCode::TryEnd);
                let jump_over = self.code.len();
                self.code.push(OpCode::Jump(0));
                let handler_start = self.code.len();
                self.code[try_start] = OpCode::TryStart(handler_start);

                let err_slot = self.next_local; self.next_local += 1;
                let saved = self.locals.insert(err_name.clone(), err_slot);
                self.code.push(OpCode::SetLocal(err_slot));
                self.compile_stmt(*catch_block);
                let end = self.code.len();
                self.code[jump_over] = OpCode::Jump(end);
                match saved {
                    Some(old) => { self.locals.insert(err_name, old); }
                    None => { self.locals.remove(&err_name); }
                }
            }
            Stmt::StructDef(_, _) => {}
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
            Expr::InterpolatedString(parts) => {
                let n = parts.len();
                for p in parts { self.compile_expr(p); }
                self.code.push(OpCode::Interpolate(n));
            }
            Expr::Function(params, body) => {
                let mut sub = Compiler::new();
                for (i, p) in params.iter().enumerate() { sub.locals.insert(p.clone(), i); }
                sub.next_local = params.len();
                sub.compile_stmt(*body);
                sub.code.push(OpCode::Return);
                let idx = self.functions.len();
                self.functions.push(sub.code);
                self.code.push(OpCode::Constant(Value::Number(idx as f64)));
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
                for (f_name, f_val) in fields { self.compile_expr(f_val); field_names.push(f_name); }
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
                if is_builtin(&name) {
                    self.code.push(OpCode::Builtin(name, args.len()));
                } else if let Some(&slot) = self.locals.get(&name) {
                    self.code.push(OpCode::GetLocal(slot));
                    self.code.push(OpCode::Call(args.len()));
                } else {
                    for _ in 0..args.len() { self.code.push(OpCode::Pop); }
                    self.code.push(OpCode::Constant(Value::Null));
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
        }
    }
}

fn is_builtin(name: &str) -> bool {
    matches!(name,
        "str" | "num" | "type" | "len" | "push" | "pop" | "keys"
        | "split" | "join" | "upper" | "lower" | "trim" | "replace" | "contains"
        | "str_eq" | "char_code" | "byte_at" | "byte_substr" | "bytes_to_str"
        | "read_file" | "write_file" | "file_exists" | "list_dir" | "mkdir"
        | "random" | "clear_screen" | "print_str" | "print_char" | "read_line" | "input"
        | "tcp_listen" | "tcp_accept" | "tcp_read" | "tcp_write" | "tcp_close" | "http_get"
    )
}

// ===================== VM =====================

struct Handler {
    ip: usize,
    locals: Vec<Value>,
    frames: Vec<Vec<Value>>,
    call_stack: Vec<(usize, usize)>,
    stack: Vec<Value>,
}

pub struct VM {
    stack: Vec<Value>,
    locals: Vec<Value>,
    frames: Vec<Vec<Value>>,
    functions: Vec<Vec<OpCode>>,
    functions_by_name: HashMap<String, usize>,
    call_stack: Vec<(usize, usize)>,
    handlers: Vec<Handler>,
    pub heap: Heap,
}

impl VM {
    pub fn new() -> Self {
        VM {
            stack: Vec::new(), locals: Vec::new(), frames: Vec::new(),
            functions: Vec::new(), functions_by_name: HashMap::new(),
            call_stack: Vec::new(), handlers: Vec::new(), heap: Heap::new(),
        }
    }

    fn get_roots(&self) -> Vec<Value> {
        let mut r = Vec::new();
        r.extend(self.stack.clone());
        r.extend(self.locals.clone());
        r
    }

    fn builtin(&mut self, name: &str, args: Vec<Value>) -> Result<Value, String> {
        match name {
            "str" => Ok(Value::String(args.get(0).unwrap_or(&Value::Null).to_string())),
            "num" => match args.get(0).unwrap_or(&Value::Null) {
                Value::Number(n) => Ok(Value::Number(*n)),
                Value::String(s) => s.parse::<f64>().map(Value::Number).map_err(|_| format!("num() cannot parse {:?}", s)),
                _ => Err("num() expects string or number".to_string()),
            },
            "type" => {
                let t = match args.get(0).unwrap_or(&Value::Null) {
                    Value::Number(_) => "number", Value::String(_) => "string", Value::Bool(_) => "bool",
                    Value::Array(_) => "array", Value::Map(_) => "map", Value::Struct(..) => "struct",
                    Value::Function { .. } => "function", Value::Null => "null",
                };
                Ok(Value::String(t.to_string()))
            }
            "len" => match args.get(0).unwrap_or(&Value::Null) {
                Value::String(s) => Ok(Value::Number(s.len() as f64)),
                Value::Array(idx) => if let HeapObject::Array(arr) = self.heap.get(*idx) { Ok(Value::Number(arr.len() as f64)) } else { Err("Not array".to_string()) },
                Value::Map(idx) => if let HeapObject::Map(map) = self.heap.get(*idx) { Ok(Value::Number(map.len() as f64)) } else { Err("Not map".to_string()) },
                _ => Err("len() expects collection".to_string()),
            },
            "push" => {
                let v = args.get(1).cloned().unwrap_or(Value::Null);
                if let Some(Value::Array(idx)) = args.get(0) {
                    if let HeapObject::Array(arr) = self.heap.get_mut(*idx) { arr.push(v); }
                }
                Ok(Value::Null)
            }
            "pop" => {
                if let Some(Value::Array(idx)) = args.get(0) {
                    if let HeapObject::Array(arr) = self.heap.get_mut(*idx) { return Ok(arr.pop().unwrap_or(Value::Null)); }
                }
                Err("pop() expects array".to_string())
            }
            "keys" => {
                if let Some(Value::Map(idx)) = args.get(0) {
                    let mut keys = Vec::new();
                    if let HeapObject::Map(map) = self.heap.get(*idx) {
                        for k in map.keys() {
                            let kv = match k {
                                MapKey::String(s) => Value::String(s.clone()),
                                MapKey::Number(n) => Value::Number(f64::from_bits(*n as u64)),
                                MapKey::Bool(b) => Value::Bool(*b),
                            };
                            keys.push(kv);
                        }
                    }
                    let out = self.heap.alloc(HeapObject::Array(keys));
                    return Ok(Value::Array(out));
                }
                Err("keys() expects map".to_string())
            }
            "split" => {
                if let (Some(Value::String(sv)), Some(Value::String(sep))) = (args.get(0), args.get(1)) {
                    if sep.is_empty() { return Err("split() sep empty".to_string()); }
                    let parts: Vec<Value> = sv.split(sep.as_str()).map(|p| Value::String(p.to_string())).collect();
                    let idx = self.heap.alloc(HeapObject::Array(parts));
                    Ok(Value::Array(idx))
                } else { Err("split() expects two strings".to_string()) }
            }
            "join" => {
                if let (Some(Value::Array(idx)), Some(Value::String(sep))) = (args.get(0), args.get(1)) {
                    if let HeapObject::Array(arr) = self.heap.get(*idx) {
                        let mut parts = Vec::new();
                        for item in arr.iter() {
                            if let Value::String(s) = item { parts.push(s.clone()); }
                            else { return Err("join() expects strings".to_string()); }
                        }
                        return Ok(Value::String(parts.join(sep)));
                    }
                }
                Err("join() expects array and string".to_string())
            }
            "upper" => match args.get(0) { Some(Value::String(s)) => Ok(Value::String(s.to_uppercase())), _ => Err("upper()".to_string()) },
            "lower" => match args.get(0) { Some(Value::String(s)) => Ok(Value::String(s.to_lowercase())), _ => Err("lower()".to_string()) },
            "trim" => match args.get(0) { Some(Value::String(s)) => Ok(Value::String(s.trim().to_string())), _ => Err("trim()".to_string()) },
            "replace" => {
                if let (Some(Value::String(sv)), Some(Value::String(ov)), Some(Value::String(nv))) = (args.get(0), args.get(1), args.get(2)) {
                    Ok(Value::String(sv.replace(ov, nv)))
                } else { Err("replace()".to_string()) }
            }
            "contains" => match (args.get(0), args.get(1)) {
                (Some(Value::String(s)), Some(Value::String(sub))) => Ok(Value::Bool(s.contains(sub))),
                (Some(Value::Array(idx)), Some(v)) => {
                    if let HeapObject::Array(arr) = self.heap.get(*idx) {
                        Ok(Value::Bool(arr.iter().any(|x| x.to_string() == v.to_string())))
                    } else { Err("Not array".to_string()) }
                }
                (Some(Value::Map(idx)), Some(v)) => {
                    if let Ok(k) = MapKey::from_value(v) {
                        if let HeapObject::Map(map) = self.heap.get(*idx) { return Ok(Value::Bool(map.contains_key(&k))); }
                    }
                    Ok(Value::Bool(false))
                }
                _ => Err("contains()".to_string()),
            },
            "str_eq" => {
                let a = args.get(0).cloned().unwrap_or(Value::Null);
                let b = args.get(1).cloned().unwrap_or(Value::Null);
                Ok(Value::Number(if a.to_string() == b.to_string() { 1.0 } else { 0.0 }))
            }
            "char_code" => match args.get(0) {
                Some(Value::String(s)) if s.as_bytes().len() == 1 => Ok(Value::Number(s.as_bytes()[0] as f64)),
                _ => Err("char_code()".to_string()),
            },
            "byte_at" => {
                if let (Some(Value::String(sv)), Some(Value::Number(n))) = (args.get(0), args.get(1)) {
                    let idx = *n as isize; let bytes = sv.as_bytes();
                    if idx < 0 || idx as usize >= bytes.len() { return Ok(Value::Number(-1.0)); }
                    return Ok(Value::Number(bytes[idx as usize] as f64));
                }
                Err("byte_at()".to_string())
            }
            "byte_substr" => {
                if let (Some(Value::String(sv)), Some(Value::Number(a)), Some(Value::Number(b))) = (args.get(0), args.get(1), args.get(2)) {
                    let bytes = sv.as_bytes();
                    let mut start = if *a < 0.0 { 0 } else { *a as usize };
                    let mut end = if *b < 0.0 { 0 } else { *b as usize };
                    if start > bytes.len() { start = bytes.len(); }
                    if end > bytes.len() { end = bytes.len(); }
                    if start > end { start = end; }
                    return Ok(Value::String(String::from_utf8_lossy(&bytes[start..end]).to_string()));
                }
                Err("byte_substr()".to_string())
            }
            "bytes_to_str" => {
                if let Some(Value::Array(idx)) = args.get(0) {
                    if let HeapObject::Array(arr) = self.heap.get(*idx) {
                        let mut buf = Vec::with_capacity(arr.len());
                        for v in arr.iter() {
                            if let Value::Number(n) = v {
                                let b = *n as i64;
                                if !(0..=255).contains(&b) { return Err(format!("byte out of range: {}", b)); }
                                buf.push(b as u8);
                            } else { return Err("bytes_to_str()".to_string()); }
                        }
                        return Ok(Value::String(String::from_utf8_lossy(&buf).to_string()));
                    }
                }
                Err("bytes_to_str()".to_string())
            }
            "read_file" => match args.get(0) {
                Some(Value::String(p)) => Ok(Value::String(fs::read_to_string(p).map_err(|e| e.to_string())?)),
                _ => Err("read_file()".to_string()),
            },
            "write_file" => {
                if let (Some(Value::String(p)), Some(Value::String(c))) = (args.get(0), args.get(1)) {
                    fs::write(p, c).map_err(|e| e.to_string())?;
                    Ok(Value::Null)
                } else { Err("write_file()".to_string()) }
            }
            "file_exists" => match args.get(0) {
                Some(Value::String(p)) => Ok(Value::Bool(Path::new(p).exists())),
                _ => Err("file_exists()".to_string()),
            },
            "list_dir" => {
                if let Some(Value::String(p)) = args.get(0) {
                    let mut files = Vec::new();
                    if let Ok(entries) = fs::read_dir(p) {
                        for entry in entries.flatten() {
                            if let Ok(name) = entry.file_name().into_string() { files.push(Value::String(name)); }
                        }
                    }
                    let idx = self.heap.alloc(HeapObject::Array(files));
                    return Ok(Value::Array(idx));
                }
                Err("list_dir()".to_string())
            }
            "mkdir" => match args.get(0) {
                Some(Value::String(p)) => { let _ = fs::create_dir_all(p); Ok(Value::Null) }
                _ => Err("mkdir()".to_string()),
            },
            "random" => {
                let max = match args.get(0) { Some(Value::Number(n)) => *n as u64, _ => 100 };
                use std::time::{SystemTime, UNIX_EPOCH};
                let nanos = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().subsec_nanos() as u64;
                Ok(Value::Number(((nanos * 1103515245 + 12345) % max) as f64))
            }
            "clear_screen" => {
                print!("\x1b[2J\x1b[1;1H");
                use std::io::Write; std::io::stdout().flush().unwrap();
                Ok(Value::Null)
            }
            "print_str" => {
                if let Some(v) = args.get(0) { print!("{}", v.to_string()); use std::io::Write; std::io::stdout().flush().unwrap(); }
                Ok(Value::Null)
            }
            "print_char" => {
                if let Some(Value::Number(n)) = args.get(0) { print!("{}", *n as u8 as char); use std::io::Write; std::io::stdout().flush().unwrap(); }
                Ok(Value::Null)
            }
            "read_line" => {
                let mut input = String::new();
                std::io::stdin().read_line(&mut input).unwrap();
                Ok(Value::String(input.trim().to_string()))
            }
            "input" => {
                let prompt = match args.get(0) { Some(Value::String(s)) => s.clone(), _ => String::new() };
                print!("{}", prompt);
                use std::io::Write; std::io::stdout().flush().unwrap();
                let mut input = String::new();
                std::io::stdin().read_line(&mut input).unwrap();
                Ok(Value::String(input.trim().to_string()))
            }
            "tcp_listen" => {
                if let Some(Value::Number(port)) = args.get(0) {
                    let l = TcpListener::bind(format!("127.0.0.1:{}", port)).map_err(|e| e.to_string())?;
                    let mut c = get_counter().lock().unwrap();
                    let id = *c; *c += 1;
                    get_servers().lock().unwrap().insert(id, l);
                    return Ok(Value::Number(id as f64));
                }
                Err("tcp_listen()".to_string())
            }
            "tcp_accept" => {
                if let Some(Value::Number(id)) = args.get(0) {
                    let servers = get_servers().lock().unwrap();
                    if let Some(l) = servers.get(&(*id as usize)) {
                        match l.accept() {
                            Ok((s, _)) => {
                                let mut c = get_counter().lock().unwrap();
                                let cid = *c; *c += 1;
                                get_clients().lock().unwrap().insert(cid, s);
                                return Ok(Value::Number(cid as f64));
                            }
                            Err(e) => return Err(format!("accept: {}", e)),
                        }
                    }
                }
                Err("tcp_accept()".to_string())
            }
            "tcp_read" => {
                if let Some(Value::Number(id)) = args.get(0) {
                    let max = match args.get(1) { Some(Value::Number(n)) => *n as usize, _ => 4096 };
                    let mut clients = get_clients().lock().unwrap();
                    if let Some(s) = clients.get_mut(&(*id as usize)) {
                        let mut buf = vec![0; max];
                        match s.read(&mut buf) {
                            Ok(n) => { buf.truncate(n); return Ok(Value::String(String::from_utf8_lossy(&buf).to_string())); }
                            Err(e) => return Err(format!("read: {}", e)),
                        }
                    }
                }
                Err("tcp_read()".to_string())
            }
            "tcp_write" => {
                if let (Some(Value::Number(id)), Some(Value::String(msg))) = (args.get(0), args.get(1)) {
                    let mut clients = get_clients().lock().unwrap();
                    if let Some(s) = clients.get_mut(&(*id as usize)) {
                        return s.write_all(msg.as_bytes()).map(|_| Value::Null).map_err(|e| e.to_string());
                    }
                }
                Err("tcp_write()".to_string())
            }
            "tcp_close" => {
                if let Some(Value::Number(id)) = args.get(0) {
                    get_clients().lock().unwrap().remove(&(*id as usize));
                    get_servers().lock().unwrap().remove(&(*id as usize));
                    return Ok(Value::Null);
                }
                Err("tcp_close()".to_string())
            }
            "http_get" => {
                if let Some(Value::String(url)) = args.get(0) {
                    match ureq::get(url).call() {
                        Ok(resp) => return resp.into_string().map(Value::String).map_err(|e| e.to_string()),
                        Err(e) => return Err(format!("http_get: {}", e)),
                    }
                }
                Err("http_get()".to_string())
            }
            _ => Err(format!("Unknown builtin: {}", name)),
        }
    }

    pub fn run(&mut self, code: Vec<OpCode>, funcs: Vec<Vec<OpCode>>) -> Result<(), String> {
        self.functions = funcs;
        let mut ip = 0;
        let mut current_code = code.clone();

        while ip < current_code.len() {
            match &current_code[ip] {
                OpCode::Constant(v) => self.stack.push(v.clone()),
                OpCode::Add => {
                    let b = self.stack.pop().unwrap_or(Value::Null);
                    let a = self.stack.pop().unwrap_or(Value::Null);
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
                OpCode::Lt => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); match (&a, &b) { (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x < y)), _ => self.stack.push(Value::Bool(a.to_string() < b.to_string())) } }
                OpCode::Gt => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); match (&a, &b) { (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x > y)), _ => self.stack.push(Value::Bool(a.to_string() > b.to_string())) } }
                OpCode::LtEq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); match (&a, &b) { (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x <= y)), _ => self.stack.push(Value::Bool(a.to_string() <= b.to_string())) } }
                OpCode::GtEq => { let b = self.stack.pop().unwrap_or(Value::Null); let a = self.stack.pop().unwrap_or(Value::Null); match (&a, &b) { (Value::Number(x), Value::Number(y)) => self.stack.push(Value::Bool(x >= y)), _ => self.stack.push(Value::Bool(a.to_string() >= b.to_string())) } }
                OpCode::Negate => { let v = self.stack.pop().unwrap_or(Value::Null); if let Value::Number(n) = v { self.stack.push(Value::Number(-n)); } else { self.stack.push(Value::Null); } }
                OpCode::Not => { let v = self.stack.pop().unwrap_or(Value::Null); if let Value::Bool(b) = v { self.stack.push(Value::Bool(!b)); } else { self.stack.push(Value::Null); } }
                OpCode::Print => { let val = self.stack.pop().unwrap_or(Value::Null); println!("{}", val.to_string()); }

                // --- Round 1 superinstructions ---
                OpCode::BinLocals(op, a, b) => {
                    let lv = &self.locals[*a as usize];
                    let rv = &self.locals[*b as usize];
                    let res = match op {
                        TokenType::Plus => match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => Value::Number(x + y),
                            (Value::String(x), Value::String(y)) => Value::String(format!("{}{}", x, y)),
                            _ => Value::Null,
                        },
                        TokenType::Minus => match (lv, rv) { (Value::Number(x), Value::Number(y)) => Value::Number(x - y), _ => Value::Null },
                        TokenType::Star => match (lv, rv) { (Value::Number(x), Value::Number(y)) => Value::Number(x * y), _ => Value::Null },
                        TokenType::Slash => match (lv, rv) { (Value::Number(x), Value::Number(y)) => Value::Number(x / y), _ => Value::Null },
                        TokenType::EqEq => Value::Bool(match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => x == y,
                            (Value::String(x), Value::String(y)) => x == y,
                            (Value::Bool(x), Value::Bool(y)) => x == y,
                            _ => false,
                        }),
                        TokenType::NotEq => Value::Bool(match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => x != y,
                            (Value::String(x), Value::String(y)) => x != y,
                            (Value::Bool(x), Value::Bool(y)) => x != y,
                            _ => true,
                        }),
                        TokenType::Lt => match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => Value::Bool(x < y),
                            (Value::String(x), Value::String(y)) => Value::Bool(x < y),
                            _ => Value::Null,
                        },
                        TokenType::Gt => match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => Value::Bool(x > y),
                            (Value::String(x), Value::String(y)) => Value::Bool(x > y),
                            _ => Value::Null,
                        },
                        TokenType::LtEq => match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => Value::Bool(x <= y),
                            (Value::String(x), Value::String(y)) => Value::Bool(x <= y),
                            _ => Value::Null,
                        },
                        TokenType::GtEq => match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => Value::Bool(x >= y),
                            (Value::String(x), Value::String(y)) => Value::Bool(x >= y),
                            _ => Value::Null,
                        },
                        _ => Value::Null,
                    };
                    self.stack.push(res);
                }
                OpCode::IncLocal(slot, delta) => {
                    if let Value::Number(n) = &mut self.locals[*slot as usize] { *n += delta; }
                }
                OpCode::AddLocalConst(a, k, b) => {
                    let res = match &self.locals[*a as usize] {
                        Value::Number(n) => Value::Number(n + k),
                        _ => Value::Null,
                    };
                    self.locals[*b as usize] = res;
                }

                // --- Round 2 superinstructions ---
                OpCode::JumpIfLocalCmpFalse(op, a, b, target) => {
                    let lv = &self.locals[*a as usize];
                    let rv = &self.locals[*b as usize];
                    let cond = match op {
                        TokenType::Lt => match (lv, rv) { (Value::Number(x), Value::Number(y)) => x < y, _ => false },
                        TokenType::LtEq => match (lv, rv) { (Value::Number(x), Value::Number(y)) => x <= y, _ => false },
                        TokenType::Gt => match (lv, rv) { (Value::Number(x), Value::Number(y)) => x > y, _ => false },
                        TokenType::GtEq => match (lv, rv) { (Value::Number(x), Value::Number(y)) => x >= y, _ => false },
                        TokenType::EqEq => match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => x == y,
                            (Value::String(x), Value::String(y)) => x == y,
                            (Value::Bool(x), Value::Bool(y)) => x == y,
                            _ => false,
                        },
                        TokenType::NotEq => match (lv, rv) {
                            (Value::Number(x), Value::Number(y)) => x != y,
                            (Value::String(x), Value::String(y)) => x != y,
                            (Value::Bool(x), Value::Bool(y)) => x != y,
                            _ => true,
                        },
                        _ => false,
                    };
                    if !cond { ip = *target; continue; }
                }
                OpCode::AddLocalMulLocal(dst, a, b) => {
                    let prod = match (&self.locals[*a as usize], &self.locals[*b as usize]) {
                        (Value::Number(x), Value::Number(y)) => Value::Number(x * y),
                        _ => Value::Null,
                    };
                    let sum = match (&self.locals[*dst as usize], &prod) {
                        (Value::Number(x), Value::Number(y)) => Value::Number(x + y),
                        (Value::String(x), Value::String(y)) => Value::String(format!("{}{}", x, y)),
                        _ => Value::Null,
                    };
                    self.locals[*dst as usize] = sum;
                }
                OpCode::IncLocalJump(slot, delta, target) => {
                    if let Value::Number(n) = &mut self.locals[*slot as usize] { *n += delta; }
                    ip = *target;
                    continue;
                }

                OpCode::Interpolate(n) => {
                    if *n == 0 { self.stack.push(Value::String(String::new())); }
                    else {
                        let mut parts = Vec::new();
                        for _ in 0..*n { parts.push(self.stack.pop().unwrap_or(Value::Null)); }
                        parts.reverse();
                        let s: String = parts.iter().map(|v| v.to_string()).collect();
                        self.stack.push(Value::String(s));
                    }
                }

                OpCode::DefineFunction(name, idx, slot) => {
                    if self.locals.len() <= *slot { self.locals.resize(*slot + 1, Value::Null); }
                    self.locals[*slot] = Value::Number(*idx as f64);
                    self.functions_by_name.insert(name.clone(), *idx);
                }

                OpCode::Builtin(name, arg_count) => {
                    if self.heap.needs_gc() {
                        let roots = self.get_roots();
                        self.heap.collect_garbage(&roots);
                    }
                    let mut args = Vec::new();
                    for _ in 0..*arg_count { args.push(self.stack.pop().unwrap_or(Value::Null)); }
                    let res = self.builtin(name, args)?;
                    self.stack.push(res);
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
                            self.call_stack.push((ip, self.handlers.len()));
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
                        self.call_stack.push((ip, self.handlers.len()));
                        self.frames.push(std::mem::replace(&mut self.locals, Vec::new()));
                        let new_locals: Vec<Value> = (0..*arg_count).map(|_| self.stack.pop().unwrap_or(Value::Null)).collect();
                        self.locals = new_locals;
                        current_code = self.functions[idx as usize].clone();
                        ip = 0; continue;
                    }
                }
                OpCode::Return => {
                    let ret_val = self.stack.pop().unwrap_or(Value::Null);
                    if let Some((ret_ip, handlers_len)) = self.call_stack.pop() {
                        self.handlers.truncate(handlers_len);
                        self.locals = self.frames.pop().unwrap_or_default();
                        self.stack.push(ret_val);
                        current_code = code.clone();
                        ip = ret_ip;
                    } else { break; }
                }

                OpCode::TryStart(handler_ip) => {
                    self.handlers.push(Handler {
                        ip: *handler_ip,
                        locals: self.locals.clone(),
                        frames: self.frames.clone(),
                        call_stack: self.call_stack.clone(),
                        stack: self.stack.clone(),
                    });
                }
                OpCode::TryEnd => { self.handlers.pop(); }
                OpCode::Throw => {
                    let exc = self.stack.pop().unwrap_or(Value::Null);
                    if let Some(h) = self.handlers.pop() {
                        self.locals = h.locals;
                        self.frames = h.frames;
                        self.call_stack = h.call_stack;
                        self.stack = h.stack;
                        self.stack.push(exc);
                        current_code = code.clone();
                        ip = h.ip; continue;
                    } else {
                        return Err(format!("Uncaught exception: {}", exc.to_string()));
                    }
                }

                OpCode::Array(size) => {
                    if self.heap.needs_gc() {
                        let roots = self.get_roots();
                        self.heap.collect_garbage(&roots);
                    }
                    let mut elements = Vec::new();
                    for _ in 0..*size { elements.push(self.stack.pop().unwrap_or(Value::Null)); }
                    elements.reverse();
                    let idx = self.heap.alloc(HeapObject::Array(elements));
                    self.stack.push(Value::Array(idx));
                }
                OpCode::Map(size) => {
                    if self.heap.needs_gc() {
                        let roots = self.get_roots();
                        self.heap.collect_garbage(&roots);
                    }
                    let mut map = HashMap::new();
                    for _ in 0..*size {
                        let v = self.stack.pop().unwrap_or(Value::Null);
                        let k = self.stack.pop().unwrap_or(Value::Null);
                        if let Ok(key) = MapKey::from_value(&k) { map.insert(key, v); }
                    }
                    let idx = self.heap.alloc(HeapObject::Map(map));
                    self.stack.push(Value::Map(idx));
                }
                OpCode::Struct(name, fields) => {
                    if self.heap.needs_gc() {
                        let roots = self.get_roots();
                        self.heap.collect_garbage(&roots);
                    }
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
                }
                OpCode::Index => {
                    let idx_val = self.stack.pop().unwrap_or(Value::Null);
                    let target = self.stack.pop().unwrap_or(Value::Null);
                    match (target, idx_val) {
                        (Value::Array(arr_idx), Value::Number(n)) => {
                            if let HeapObject::Array(arr) = self.heap.get(arr_idx) {
                                let i = n as usize;
                                if i < arr.len() { self.stack.push(arr[i].clone()); } else { self.stack.push(Value::Null); }
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
                                let i = n as usize;
                                if i < arr.len() { arr[i] = value; }
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
                }
                OpCode::Halt => break,
            }
            ip += 1;
        }
        Ok(())
    }
}