use crate::lexer::TokenType;

#[derive(Debug, Clone)]
pub enum Expr {
    Number(f64),
    String(String),
    Bool(bool),
    Ident(String),
    Unary(TokenType, Box<Expr>),
    Binary(Box<Expr>, TokenType, Box<Expr>),
    Call(String, Vec<Expr>),
    Array(Vec<Expr>),
    Map(Vec<(Expr, Expr)>),
    Index(Box<Expr>, Box<Expr>),
    InterpolatedString(Vec<Expr>),
    StructInit(String, Vec<(String, Expr)>),
    FieldAccess(Box<Expr>, String),
    Function(Vec<String>, Box<Stmt>),   // <--- NEW: anonymous function / lambda
}

#[derive(Debug, Clone)]
pub enum Stmt {
    Let(String, Expr),
    Assign(String, Expr),
    IndexSet(String, Expr, Expr), 
    FieldSet(Expr, String, Expr),
    Print(Expr),
    ExprStmt(Expr),
    Block(Vec<Stmt>),
    If(Expr, Box<Stmt>, Option<Box<Stmt>>),
    While(Expr, Box<Stmt>),
    For(String, Expr, Box<Stmt>),
    Function(String, Vec<String>, Box<Stmt>),
    Return(Option<Expr>),
    Break,
    Continue,
    StructDef(String, Vec<(String, String)>),
    Try(Box<Stmt>, String, Box<Stmt>),
    Throw(Expr),
    Import(String),
}