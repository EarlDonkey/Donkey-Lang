use std::collections::HashMap;
use std::rc::Rc;
use std::cell::RefCell;
use std::fs;
use std::path::Path;
use std::sync::{Mutex, OnceLock};
use std::net::{TcpListener, TcpStream};
use std::io::{Read, Write};
use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;

static CLIENTS: OnceLock<Mutex<HashMap<usize, TcpStream>>> = OnceLock::new();
static SERVERS: OnceLock<Mutex<HashMap<usize, TcpListener>>> = OnceLock::new();
static COUNTER: OnceLock<Mutex<usize>> = OnceLock::new();

fn get_clients() -> &'static Mutex<HashMap<usize, TcpStream>> { CLIENTS.get_or_init(|| Mutex::new(HashMap::new())) }
fn get_servers() -> &'static Mutex<HashMap<usize, TcpListener>> { SERVERS.get_or_init(|| Mutex::new(HashMap::new())) }
fn get_counter() -> &'static Mutex<usize> { COUNTER.get_or_init(|| Mutex::new(1)) }

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum MapKey { String(String), Number(usize), Bool(bool) }

impl MapKey {
    fn from_value(v: &Value) -> Result<MapKey, String> {
        match v {
            Value::String(s) => Ok(MapKey::String(s.clone())),
            Value::Number(n) => Ok(MapKey::Number(n.to_bits() as usize)),
            Value::Bool(b) => Ok(MapKey::Bool(*b)),
            _ => Err("Map keys must be strings, numbers, or bools".to_string()),
        }
    }
}

#[derive(Debug, Clone)]
pub enum Value {
    Number(f64), String(String), Bool(bool),
    Function { params: Vec<String>, body: Box<Stmt> },
    Array(Rc<RefCell<Vec<Value>>>),
    Map(Rc<RefCell<HashMap<MapKey, Value>>>),
    Struct(String, Rc<RefCell<HashMap<String, Value>>>),
    Null,
}

impl Value {
    pub fn is_truthy(&self) -> bool { matches!(self, Value::Bool(true)) }
    pub fn to_string(&self) -> String {
        match self {
            Value::Number(n) => if n.fract() == 0.0 { format!("{:.0}", n) } else { n.to_string() },
            Value::String(s) => s.clone(),
            Value::Bool(b) => b.to_string(),
            Value::Function { .. } => "<fn>".to_string(),
            Value::Array(arr) => {
                let list: Vec<String> = arr.borrow().iter().map(|v| v.to_string()).collect();
                format!("[{}]", list.join(", "))
            }
            Value::Map(map) => {
                let mut pairs = Vec::new();
                for (k, v) in map.borrow().iter() {
                    let key_str = match k {
                        MapKey::String(s) => s.clone(),
                        MapKey::Number(n) => Value::Number(f64::from_bits(*n as u64)).to_string(),
                        MapKey::Bool(b) => b.to_string(),
                    };
                    pairs.push(format!("{}: {}", key_str, v.to_string()));
                }
                format!("{{{}}}", pairs.join(", "))
            }
            Value::Struct(_, fields) => {
                let mut pairs = Vec::new();
                for (k, v) in fields.borrow().iter() { pairs.push(format!("{}: {}", k, v.to_string())); }
                format!("{{{}}}", pairs.join(", "))
            }
            Value::Null => "null".to_string(),
        }
    }
}

pub enum ControlFlow {
    Normal, Return(Value), Break, Continue, Throw(Value)
}

pub struct Environment {
    scopes: Vec<HashMap<String, Value>>,
    structs: HashMap<String, HashMap<String, String>>,
}

impl Environment {
    pub fn new() -> Self {
        Environment { scopes: vec![HashMap::new()], structs: HashMap::new() }
    }
    pub fn define(&mut self, name: String, value: Value) { self.scopes.last_mut().unwrap().insert(name, value); }
    pub fn get(&self, name: &str) -> Result<Value, String> {
        for scope in self.scopes.iter().rev() {
            if let Some(v) = scope.get(name) { return Ok(v.clone()); }
        }
        Err(format!("Undefined variable '{}'", name))
    }
    pub fn assign(&mut self, name: &str, value: Value) -> Result<(), String> {
        for scope in self.scopes.iter_mut().rev() {
            if scope.contains_key(name) { scope.insert(name.to_string(), value); return Ok(()); }
        }
        Err(format!("Assignment to undefined variable '{}'", name))
    }
    pub fn push_scope(&mut self) { self.scopes.push(HashMap::new()); }
    pub fn pop_scope(&mut self) { self.scopes.pop(); }
}

pub struct Interpreter { env: Environment }

impl Interpreter {
    pub fn new(script_args: Vec<String>) -> Self {
        let mut env = Environment::new();
        let args_val = script_args.into_iter().map(Value::String).collect();
        env.define("args".to_string(), Value::Array(Rc::new(RefCell::new(args_val))));
        Interpreter { env }
    }

    pub fn interpret(&mut self, statements: Vec<Stmt>) -> Result<(), String> {
        for stmt in statements {
            match self.execute(stmt)? {
                ControlFlow::Normal => {}
                ControlFlow::Throw(v) => return Err(format!("Uncaught exception: {}", v.to_string())),
                _ => return Err("Cannot return/break outside of function/loop".to_string()),
            }
        }
        Ok(())
    }

    fn execute(&mut self, stmt: Stmt) -> Result<ControlFlow, String> {
        match stmt {
            Stmt::Import(path) => {
                let file_content = fs::read_to_string(&path).map_err(|e| e.to_string())?;
                let mut lex = crate::lexer::Lexer::new(&file_content);
                let tokens = lex.tokenize()?;
                let mut parser = crate::parser::Parser::new(tokens);
                let ast = parser.parse()?;
                for s in ast { self.execute(s)?; }
                Ok(ControlFlow::Normal)
            }
            Stmt::Try(try_block, err_name, catch_block) => {
                match self.execute(*try_block) {
                    Ok(ControlFlow::Throw(val)) => {
                        self.env.push_scope();
                        self.env.define(err_name, val);
                        let res = self.execute(*catch_block);
                        self.env.pop_scope();
                        res
                    }
                    Ok(other) => Ok(other),
                    Err(e) => {
                        self.env.push_scope();
                        self.env.define(err_name, Value::String(e));
                        let res = self.execute(*catch_block);
                        self.env.pop_scope();
                        res
                    }
                }
            }
            Stmt::Throw(expr) => {
                let val = self.evaluate(expr)?;
                Ok(ControlFlow::Throw(val))
            }
            Stmt::StructDef(name, fields) => {
                let mut ft = HashMap::new();
                for (f, t) in fields { ft.insert(f, t); }
                self.env.structs.insert(name, ft);
                Ok(ControlFlow::Normal)
            }
            Stmt::Let(name, expr) => { let val = self.evaluate(expr)?; self.env.define(name, val); Ok(ControlFlow::Normal) }
            Stmt::Assign(name, expr) => { let val = self.evaluate(expr)?; self.env.assign(&name, val)?; Ok(ControlFlow::Normal) }
            Stmt::IndexSet(name, idx_expr, val_expr) => {
                let index = self.evaluate(idx_expr)?;
                let value = self.evaluate(val_expr)?;
                
                let target = self.env.get(&name)?;
                match target {
                    Value::Array(arr) => {
                        if let Value::Number(n) = index {
                            let i = n as usize;
                            let mut borrowed = arr.borrow_mut();
                            if i < borrowed.len() { borrowed[i] = value; } else { return Err(format!("Index {} out of range", i)); }
                        } else { return Err("Array index must be a number".to_string()); }
                    }
                    Value::Map(map) => { let key = MapKey::from_value(&index)?; map.borrow_mut().insert(key, value); }
                    Value::Struct(_, fields) => { if let Value::String(k) = index { fields.borrow_mut().insert(k, value); } else { return Err("Struct index must be a string".to_string()); } }
                    _ => return Err("Can only index-assign arrays, maps, or structs".to_string()),
                }
                Ok(ControlFlow::Normal)
            }
            Stmt::FieldSet(obj_expr, field, val_expr) => {
                let obj = self.evaluate(obj_expr)?;
                let value = self.evaluate(val_expr)?;
                match obj {
                    Value::Struct(name, fields) => {
                        if let Some(exp) = self.env.structs.get(&name).and_then(|s| s.get(&field)) {
                            let vt = match &value { Value::Number(_) => "num", Value::String(_) => "str", Value::Bool(_) => "bool", _ => "any" };
                            if exp != "any" && exp != vt { return Err(format!("Field '{}' expects {}, got {}", field, exp, vt)); }
                        }
                        fields.borrow_mut().insert(field, value);
                        Ok(ControlFlow::Normal)
                    }
                    _ => Err("Can only set fields on structs".to_string()),
                }
            }
            Stmt::Print(expr) => { println!("{}", self.evaluate(expr)?.to_string()); Ok(ControlFlow::Normal) }
            Stmt::ExprStmt(expr) => { self.evaluate(expr)?; Ok(ControlFlow::Normal) }
            Stmt::Block(stmts) => {
                self.env.push_scope();
                let mut res = ControlFlow::Normal;
                for s in stmts {
                    res = self.execute(s)?;
                    if !matches!(res, ControlFlow::Normal) { break; }
                }
                self.env.pop_scope();
                Ok(res)
            }
            Stmt::If(cond, then_b, else_b) => {
                if self.evaluate(cond)?.is_truthy() { self.execute(*then_b) }
                else if let Some(eb) = else_b { self.execute(*eb) }
                else { Ok(ControlFlow::Normal) }
            }
            Stmt::While(cond, body) => {
                while self.evaluate(cond.clone())?.is_truthy() {
                    match self.execute((*body).clone())? {
                        ControlFlow::Break => break,
                        ControlFlow::Return(v) => return Ok(ControlFlow::Return(v)),
                        ControlFlow::Throw(v) => return Ok(ControlFlow::Throw(v)),
                        _ => {}
                    }
                }
                Ok(ControlFlow::Normal)
            }
            Stmt::For(name, iter_expr, body) => {
                match self.evaluate(iter_expr)? {
                    Value::Array(arr) => {
                        let items = arr.borrow().clone();
                        for item in items {
                            self.env.push_scope();
                            self.env.define(name.clone(), item);
                            let res = self.execute((*body).clone())?;
                            self.env.pop_scope();
                            match res {
                                ControlFlow::Break => break,
                                ControlFlow::Return(v) => return Ok(ControlFlow::Return(v)),
                                ControlFlow::Throw(v) => return Ok(ControlFlow::Throw(v)),
                                _ => {}
                            }
                        }
                        Ok(ControlFlow::Normal)
                    }
                    _ => Err("Can only iterate over arrays right now".to_string()),
                }
            }
            Stmt::Function(name, params, body) => { let f = Value::Function { params, body }; self.env.define(name, f); Ok(ControlFlow::Normal) }
            Stmt::Return(expr) => { let v = if let Some(e) = expr { self.evaluate(e)? } else { Value::Null }; Ok(ControlFlow::Return(v)) }
            Stmt::Break => Ok(ControlFlow::Break),
            Stmt::Continue => Ok(ControlFlow::Continue),
        }
    }

    fn evaluate(&mut self, expr: Expr) -> Result<Value, String> {
        match expr {
            Expr::Number(n) => Ok(Value::Number(n)),
            Expr::String(s) => Ok(Value::String(s)),
            Expr::Bool(b) => Ok(Value::Bool(b)),
            Expr::Function(params, body) => Ok(Value::Function { params, body }),
            Expr::Ident(name) => self.env.get(&name),
            Expr::InterpolatedString(parts) => {
                let mut res = String::new();
                for p in parts { res.push_str(&self.evaluate(p)?.to_string()); }
                Ok(Value::String(res))
            }
            Expr::StructInit(name, fields) => {
                if !self.env.structs.contains_key(&name) { return Err(format!("Undefined struct '{}'", name)); }
                let mut map = HashMap::new();
                for (f, e) in fields { map.insert(f, self.evaluate(e)?); }
                Ok(Value::Struct(name, Rc::new(RefCell::new(map))))
            }
            Expr::FieldAccess(obj, field) => {
                match self.evaluate(*obj)? {
                    Value::Struct(_, fields) => match fields.borrow().get(&field) {
                        Some(v) => Ok(v.clone()),
                        None => Ok(Value::Null), 
                    },
                    Value::Map(map) => {
                        let key = MapKey::String(field.clone());
                        match map.borrow().get(&key) {
                            Some(v) => Ok(v.clone()),
                            None => Ok(Value::Null), 
                        }
                    }
                    _ => Ok(Value::Null),
                }
            }
            Expr::Array(elements) => {
                let mut arr = Vec::new();
                for el in elements { arr.push(self.evaluate(el)?); }
                Ok(Value::Array(Rc::new(RefCell::new(arr))))
            }
            Expr::Map(pairs) => {
                let mut map = HashMap::new();
                for (k, v) in pairs {
                    let key = MapKey::from_value(&self.evaluate(k)?)?;
                    map.insert(key, self.evaluate(v)?);
                }
                Ok(Value::Map(Rc::new(RefCell::new(map))))
            }
            Expr::Index(target, index) => {
                let target_val = self.evaluate(*target)?;
                let index_val = self.evaluate(*index)?;
                
                match target_val {
                    Value::Array(arr) => {
                        if let Value::Number(n) = index_val {
                            let i = n as usize;
                            let borrowed = arr.borrow();
                            if i < borrowed.len() { Ok(borrowed[i].clone()) } else { Err(format!("Index {} out of range", i)) }
                        } else { Err("Array index must be a number".to_string()) }
                    }
                    Value::Map(map) => {
                        let key = MapKey::from_value(&index_val)?;
                        let borrowed = map.borrow();
                        match borrowed.get(&key) {
                            Some(v) => Ok(v.clone()),
                            None => Err("Key not found in map".to_string()),
                        }
                    }
                    Value::Struct(_, fields) => {
                        if let Value::String(k) = index_val {
                            match fields.borrow().get(&k) {
                                Some(v) => Ok(v.clone()),
                                None => Err(format!("Key '{}' not found in struct", k)),
                            }
                        } else { Err("Struct index must be a string".to_string()) }
                    }
                    Value::String(s) => {
                        if let Value::Number(n) = index_val {
                            let i = n as usize;
                            if i < s.len() {
                                let ch = s.chars().nth(i).unwrap();
                                Ok(Value::String(ch.to_string()))
                            } else { Err(format!("String index {} out of range", i)) }
                        } else { Err("String index must be a number".to_string()) }
                    }
                    _ => Err(format!("Cannot index type '{}'", target_val.to_string())),
                }
            }
            Expr::Call(name, args) => {
                if name == "tcp_listen" {
                    let p = self.evaluate(args[0].clone())?;
                    if let Value::Number(port) = p {
                        let l = TcpListener::bind(format!("127.0.0.1:{}", port)).map_err(|e| e.to_string())?;
                        let mut c = get_counter().lock().unwrap();
                        let id = *c; *c += 1;
                        get_servers().lock().unwrap().insert(id, l);
                        return Ok(Value::Number(id as f64));
                    }
                    return Err("tcp_listen expects port number".to_string());
                }
                if name == "tcp_accept" {
                    let id = self.evaluate(args[0].clone())?;
                    if let Value::Number(id_n) = id {
                        let servers = get_servers().lock().unwrap();
                        if let Some(l) = servers.get(&(id_n as usize)) {
                            match l.accept() {
                                Ok((s, _)) => {
                                    let mut c = get_counter().lock().unwrap();
                                    let cid = *c; *c += 1;
                                    get_clients().lock().unwrap().insert(cid, s);
                                    return Ok(Value::Number(cid as f64));
                                }
                                Err(e) => return Err(format!("accept failed: {}", e)),
                            }
                        }
                    }
                    return Err("Invalid server socket".to_string());
                }
                if name == "tcp_read" {
                    let id = self.evaluate(args[0].clone())?;
                    let max = if args.len() > 1 { if let Value::Number(n) = self.evaluate(args[1].clone())? { n as usize } else { 4096 } } else { 4096 };
                    if let Value::Number(id_n) = id {
                        let mut clients = get_clients().lock().unwrap();
                        if let Some(s) = clients.get_mut(&(id_n as usize)) {
                            let mut buf = vec![0; max];
                            match s.read(&mut buf) {
                                Ok(n) => { buf.truncate(n); return Ok(Value::String(String::from_utf8_lossy(&buf).to_string())); }
                                Err(e) => return Err(format!("read failed: {}", e)),
                            }
                        }
                    }
                    return Err("Invalid client socket".to_string());
                }
                if name == "tcp_write" {
                    let id = self.evaluate(args[0].clone())?;
                    let msg = self.evaluate(args[1].clone())?;
                    if let (Value::Number(id_n), Value::String(m)) = (id, msg) {
                        let mut clients = get_clients().lock().unwrap();
                        if let Some(s) = clients.get_mut(&(id_n as usize)) {
                            match s.write_all(m.as_bytes()) { Ok(_) => return Ok(Value::Null), Err(e) => return Err(format!("write failed: {}", e)) }
                        }
                    }
                    return Err("Invalid arguments to tcp_write".to_string());
                }
                if name == "tcp_close" {
                    let id = self.evaluate(args[0].clone())?;
                    if let Value::Number(id_n) = id {
                        get_clients().lock().unwrap().remove(&(id_n as usize));
                        get_servers().lock().unwrap().remove(&(id_n as usize));
                        return Ok(Value::Null);
                    }
                    return Err("Invalid socket id".to_string());
                }
                if name == "http_get" {
                    let url = self.evaluate(args[0].clone())?;
                    if let Value::String(u) = url {
                        match ureq::get(&u).call() {
                            Ok(resp) => {
                                match resp.into_string() {
                                    Ok(body) => return Ok(Value::String(body)),
                                    Err(e) => return Err(format!("http_get body failed: {}", e)),
                                }
                            }
                            Err(e) => return Err(format!("http_get failed: {}", e)),
                        }
                    }
                    return Err("http_get expects string URL".to_string());
                }
                if name == "char_code" {
                    if let Value::String(s) = self.evaluate(args[0].clone())? {
                        let bytes = s.as_bytes();
                        if bytes.len() == 1 { return Ok(Value::Number(bytes[0] as f64)); }
                    }
                    return Err("char_code() expects single character".to_string());
                }
                if name == "clear_screen" {
                    print!("\x1b[2J\x1b[1;1H");
                    use std::io::Write;
                    std::io::stdout().flush().unwrap();
                    return Ok(Value::Null);
                }
                if name == "str_eq" {
                    let a = self.evaluate(args[0].clone())?;
                    let b = self.evaluate(args[1].clone())?;
                    return Ok(Value::Number(if a.to_string() == b.to_string() { 1.0 } else { 0.0 }));
                }
                if name == "print_char" {
                    let c = self.evaluate(args[0].clone())?;
                    if let Value::Number(n) = c {
                        print!("{}", n as u8 as char);
                        use std::io::Write;
                        std::io::stdout().flush().unwrap();
                    }
                    return Ok(Value::Null);
                }
                if name == "print_str" {
                    let s = self.evaluate(args[0].clone())?;
                    print!("{}", s.to_string());
                    use std::io::Write;
                    std::io::stdout().flush().unwrap();
                    return Ok(Value::Null);
                }
                if name == "read_line" {
                    let mut input = String::new();
                    std::io::stdin().read_line(&mut input).unwrap();
                    return Ok(Value::String(input.trim().to_string()));
                }
                if name == "random" {
                    let max = if args.len() > 0 {
                        if let Value::Number(n) = self.evaluate(args[0].clone())? { n as u64 } else { 100 }
                    } else { 100 };
                    use std::time::{SystemTime, UNIX_EPOCH};
                    let nanos = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().subsec_nanos() as u64;
                    let rand_val = (nanos * 1103515245 + 12345) % max;
                    return Ok(Value::Number(rand_val as f64));
                }
                if name == "list_dir" {
                    if let Value::String(p) = self.evaluate(args[0].clone())? {
                        let mut files = Vec::new();
                        if let Ok(entries) = fs::read_dir(&p) {
                            for entry in entries.flatten() {
                                if let Ok(name) = entry.file_name().into_string() { files.push(Value::String(name)); }
                            }
                        }
                        return Ok(Value::Array(Rc::new(RefCell::new(files))));
                    }
                    return Err("list_dir() expects string".to_string());
                }
                if name == "mkdir" {
                    if let Value::String(p) = self.evaluate(args[0].clone())? {
                        let _ = fs::create_dir_all(&p);
                        return Ok(Value::Null);
                    }
                    return Err("mkdir() expects string".to_string());
                }
                if name == "len" {
                    let a = self.evaluate(args[0].clone())?;
                    match a {
                        Value::String(s) => return Ok(Value::Number(s.len() as f64)),
                        Value::Array(a) => return Ok(Value::Number(a.borrow().len() as f64)),
                        Value::Map(m) => return Ok(Value::Number(m.borrow().len() as f64)),
                        _ => return Err("len() expects string, array, or map".to_string()),
                    }
                }
                if name == "push" {
                    let t = self.evaluate(args[0].clone())?;
                    let v = self.evaluate(args[1].clone())?;
                    if let Value::Array(a) = t { a.borrow_mut().push(v); return Ok(Value::Null); }
                    return Err("push() expects an array".to_string());
                }
                if name == "pop" {
                    let t = self.evaluate(args[0].clone())?;
                    if let Value::Array(a) = t { return Ok(a.borrow_mut().pop().unwrap_or(Value::Null)); }
                    return Err("pop() expects an array".to_string());
                }
                if name == "input" {
                    let prompt = if args.len() > 0 {
                        if let Value::String(s) = self.evaluate(args[0].clone())? { s } else { "".to_string() }
                    } else { "".to_string() };
                    print!("{}", prompt);
                    use std::io::Write;
                    std::io::stdout().flush().unwrap();
                    let mut input = String::new();
                    std::io::stdin().read_line(&mut input).unwrap();
                    return Ok(Value::String(input.trim().to_string()));
                }
                if name == "str" { return Ok(Value::String(self.evaluate(args[0].clone())?.to_string())); }
                if name == "num" {
                    let val = self.evaluate(args[0].clone())?;
                    match val {
                        Value::Number(n) => return Ok(Value::Number(n)),
                        Value::String(s) => {
                            if let Ok(n) = s.parse::<f64>() { return Ok(Value::Number(n)); }
                            return Err(format!("num() cannot parse {:?}", s));
                        }
                        _ => return Err("num() expects string or number".to_string()),
                    }
                }
                if name == "type" {
                    let t = match self.evaluate(args[0].clone())? {
                        Value::Number(_) => "number", Value::String(_) => "string", Value::Bool(_) => "bool",
                        Value::Array(_) => "array", Value::Map(_) => "map", Value::Struct(..) => "struct",
                        Value::Function { .. } => "function", Value::Null => "null",
                    };
                    return Ok(Value::String(t.to_string()));
                }
                if name == "upper" { if let Value::String(s) = self.evaluate(args[0].clone())? { return Ok(Value::String(s.to_uppercase())); } return Err("upper() expects string".to_string()); }
                if name == "lower" { if let Value::String(s) = self.evaluate(args[0].clone())? { return Ok(Value::String(s.to_lowercase())); } return Err("lower() expects string".to_string()); }
                if name == "trim" { if let Value::String(s) = self.evaluate(args[0].clone())? { return Ok(Value::String(s.trim().to_string())); } return Err("trim() expects string".to_string()); }
                if name == "replace" {
                    let s = self.evaluate(args[0].clone())?; let o = self.evaluate(args[1].clone())?; let n = self.evaluate(args[2].clone())?;
                    if let (Value::String(sv), Value::String(ov), Value::String(nv)) = (s, o, n) { return Ok(Value::String(sv.replace(&ov, &nv))); }
                    return Err("replace() expects three strings".to_string());
                }
                if name == "contains" {
                    let t = self.evaluate(args[0].clone())?; let i = self.evaluate(args[1].clone())?;
                    match (t, i) {
                        (Value::String(s), Value::String(sub)) => return Ok(Value::Bool(s.contains(&sub))),
                        (Value::Array(a), v) => { let b = a.borrow(); return Ok(Value::Bool(b.iter().any(|x| x.to_string() == v.to_string()))); }
                        (Value::Map(m), v) => { if let Ok(k) = MapKey::from_value(&v) { return Ok(Value::Bool(m.borrow().contains_key(&k))); } }
                        _ => return Err("contains() expects compatible types".to_string()),
                    }
                }
                if name == "split" {
                    let s = self.evaluate(args[0].clone())?; let sep = self.evaluate(args[1].clone())?;
                    if let (Value::String(sv), Value::String(sepv)) = (s, sep) {
                        if sepv.is_empty() { return Err("split() separator cannot be empty".to_string()); }
                        let parts: Vec<Value> = sv.split(&sepv).map(|p| Value::String(p.to_string())).collect();
                        return Ok(Value::Array(Rc::new(RefCell::new(parts))));
                    }
                    return Err("split() expects two strings".to_string());
                }
                if name == "join" {
                    let a = self.evaluate(args[0].clone())?; let sep = self.evaluate(args[1].clone())?;
                    if let (Value::Array(av), Value::String(sepv)) = (a, sep) {
                        let b = av.borrow(); let mut parts = Vec::new();
                        for item in b.iter() { if let Value::String(s) = item { parts.push(s.clone()); } else { return Err("join() expects array of strings".to_string()); } }
                        return Ok(Value::String(parts.join(&sepv)));
                    }
                    return Err("join() expects array and string".to_string());
                }
                if name == "keys" {
                    if let Value::Map(m) = self.evaluate(args[0].clone())? {
                        let b = m.borrow(); let mut keys = Vec::new();
                        for k in b.keys() {
                            let kv = match k { MapKey::String(s) => Value::String(s.clone()), MapKey::Number(n) => Value::Number(f64::from_bits(*n as u64)), MapKey::Bool(b) => Value::Bool(*b) };
                            keys.push(kv);
                        }
                        return Ok(Value::Array(Rc::new(RefCell::new(keys))));
                    }
                    return Err("keys() expects map".to_string());
                }
                if name == "read_file" {
                    if let Value::String(p) = self.evaluate(args[0].clone())? {
                        return Ok(Value::String(fs::read_to_string(&p).map_err(|e| format!("read_file failed: {}", e))?));
                    }
                    return Err("read_file() expects a string path".to_string());
                }
                if name == "write_file" {
                    let p = self.evaluate(args[0].clone())?; let c = self.evaluate(args[1].clone())?;
                    if let (Value::String(pv), Value::String(cv)) = (p, c) {
                        fs::write(&pv, cv).map_err(|e| format!("write_file failed: {}", e))?;
                        return Ok(Value::Null);
                    }
                    return Err("write_file() expects two strings".to_string());
                }
                if name == "file_exists" {
                    if let Value::String(p) = self.evaluate(args[0].clone())? { return Ok(Value::Bool(Path::new(&p).exists())); }
                    return Err("file_exists() expects a string".to_string());
                }
                if name == "byte_at" {
                    let s = self.evaluate(args[0].clone())?; let i = self.evaluate(args[1].clone())?;
                    if let (Value::String(sv), Value::Number(n)) = (s, i) {
                        let idx = n as isize; let bytes = sv.as_bytes();
                        if idx < 0 || idx as usize >= bytes.len() { return Ok(Value::Number(-1.0)); }
                        return Ok(Value::Number(bytes[idx as usize] as f64));
                    }
                    return Err("byte_at() expects (string, number)".to_string());
                }
                if name == "byte_substr" {
                    let s = self.evaluate(args[0].clone())?; let a = self.evaluate(args[1].clone())?; let b = self.evaluate(args[2].clone())?;
                    if let (Value::String(sv), Value::Number(a_n), Value::Number(b_n)) = (s, a, b) {
                        let bytes = sv.as_bytes();
                        let mut start = if a_n < 0.0 { 0 } else { a_n as usize };
                        let mut end = if b_n < 0.0 { 0 } else { b_n as usize };
                        if start > bytes.len() { start = bytes.len(); }
                        if end > bytes.len() { end = bytes.len(); }
                        if start > end { start = end; }
                        return Ok(Value::String(String::from_utf8_lossy(&bytes[start..end]).to_string()));
                    }
                    return Err("byte_substr() expects (string, number, number)".to_string());
                }
                if name == "bytes_to_str" {
                    let a = self.evaluate(args[0].clone())?;
                    if let Value::Array(arr) = a {
                        let borrowed = arr.borrow(); let mut buf = Vec::with_capacity(borrowed.len());
                        for v in borrowed.iter() {
                            if let Value::Number(n) = v {
                                let b = *n as i64;
                                if !(0..=255).contains(&b) { return Err(format!("bytes_to_str: byte value out of range: {}", b)); }
                                buf.push(b as u8);
                            } else { return Err("bytes_to_str() expects array of numbers".to_string()); }
                        }
                        return Ok(Value::String(String::from_utf8_lossy(&buf).to_string()));
                    }
                    return Err("bytes_to_str() expects an array".to_string());
                }

                let callee = self.env.get(&name)?;
                match callee {
                    Value::Function { params, body } => {
                        if args.len() != params.len() { return Err(format!("{}() expects {} args, got {}", name, params.len(), args.len())); }
                        let mut arg_vals = Vec::new();
                        for a in args { arg_vals.push(self.evaluate(a)?); }
                        self.env.push_scope();
                        for (p, v) in params.iter().zip(arg_vals) { self.env.define(p.clone(), v); }
                        let result = self.execute(*body)?;
                        self.env.pop_scope();
                        if let ControlFlow::Return(val) = result { Ok(val) }
                        else if let ControlFlow::Throw(_) = result { Ok(Value::Null) }
                        else { Ok(Value::Null) }
                    }
                    _ => Err(format!("'{}' is not a function", name)),
                }
            }
            Expr::Unary(op, right) => {
                let rv = self.evaluate(*right)?;
                match op {
                    TokenType::Minus => match rv { Value::Number(n) => Ok(Value::Number(-n)), _ => Err("Operand must be number".to_string()) },
                    TokenType::Bang => match rv { Value::Bool(b) => Ok(Value::Bool(!b)), _ => Err("Operand must be bool".to_string()) },
                    _ => Err("Unknown unary".to_string()),
                }
            }
            Expr::Binary(left, op, right) => {
                if op == TokenType::And {
                    let lv = self.evaluate(*left)?;
                    if let Value::Bool(l) = lv {
                        if !l { return Ok(Value::Bool(false)); }
                        let rv = self.evaluate(*right)?;
                        if let Value::Bool(r) = rv { return Ok(Value::Bool(r)); }
                        return Err("Operands must be bools".to_string());
                    }
                    return Err("Operands must be bools".to_string());
                }
                if op == TokenType::Or {
                    let lv = self.evaluate(*left)?;
                    if let Value::Bool(l) = lv {
                        if l { return Ok(Value::Bool(true)); }
                        let rv = self.evaluate(*right)?;
                        if let Value::Bool(r) = rv { return Ok(Value::Bool(r)); }
                        return Err("Operands must be bools".to_string());
                    }
                    return Err("Operands must be bools".to_string());
                }
                
                let lv = self.evaluate(*left)?;
                let rv = self.evaluate(*right)?;
                match op {
                    TokenType::Plus => match (&lv, &rv) {
                        (Value::Number(l), Value::Number(r)) => Ok(Value::Number(l + r)),
                        (Value::String(l), Value::String(r)) => Ok(Value::String(format!("{}{}", l, r))),
                        _ => Err("Operands must be two numbers or two strings".to_string()),
                    },
                    TokenType::Minus | TokenType::Star | TokenType::Slash | TokenType::Div => {
                        match (&lv, &rv) {
                            (Value::Number(l), Value::Number(r)) => {
                                let res = match op {
                                    TokenType::Minus => l - r,
                                    TokenType::Star => l * r,
                                    TokenType::Slash => {
                                        if *r == 0.0 { return Err("Division by zero".to_string()); }
                                        l / r
                                    },
                                    TokenType::Div => {
                                        if *r == 0.0 { return Err("Integer division by zero".to_string()); }
                                        (l / r).trunc()
                                    },
                                    _ => unreachable!(),
                                };
                                Ok(Value::Number(res))
                            }
                            _ => Err("Operands must be numbers".to_string()),
                        }
                    }
                    TokenType::Gt | TokenType::GtEq | TokenType::Lt | TokenType::LtEq => {
                        match (&lv, &rv) {
                            (Value::Number(l), Value::Number(r)) => {
                                let res = match op {
                                    TokenType::Gt => l > r,
                                    TokenType::GtEq => l >= r,
                                    TokenType::Lt => l < r,
                                    TokenType::LtEq => l <= r,
                                    _ => unreachable!(),
                                };
                                Ok(Value::Bool(res))
                            }
                            (Value::String(l), Value::String(r)) => {
                                let res = match op {
                                    TokenType::Gt => l > r,
                                    TokenType::GtEq => l >= r,
                                    TokenType::Lt => l < r,
                                    TokenType::LtEq => l <= r,
                                    _ => unreachable!(),
                                };
                                Ok(Value::Bool(res))
                            }
                            _ => Err("Operands must be two numbers or two strings".to_string()),
                        }
                    }
                    TokenType::EqEq => Ok(Value::Bool(match (&lv, &rv) {
                        (Value::Number(l), Value::Number(r)) => l == r,
                        (Value::String(l), Value::String(r)) => l == r,
                        (Value::Bool(l), Value::Bool(r)) => l == r,
                        _ => false,
                    })),
                    TokenType::NotEq => Ok(Value::Bool(match (&lv, &rv) {
                        (Value::Number(l), Value::Number(r)) => l != r,
                        (Value::String(l), Value::String(r)) => l != r,
                        (Value::Bool(l), Value::Bool(r)) => l != r,
                        _ => true,
                    })),
                    _ => Err("Unknown binary operator".to_string()),
                }
            }
        }
    }
}