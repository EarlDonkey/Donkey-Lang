mod lexer;
mod parser;
mod ast;
mod interpreter;

use lexer::Lexer;
use parser::Parser;
use interpreter::Interpreter;
use std::env;
use std::fs;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        println!("Usage: donky-native <file.donk> [args...]");
        return;
    }

    let path = &args[1];
    // Capture script args (skip the executable and the file path)
    let script_args: Vec<String> = args[2..].to_vec();

    let source = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error reading file {}: {}", path, e);
            return;
        }
    };
    
    let mut lex = Lexer::new(&source);
    let tokens = match lex.tokenize() {
        Ok(t) => t,
        Err(e) => {
            eprintln!("Lex Error: {}", e);
            return;
        }
    };

    let mut parser = Parser::new(tokens);
    let ast = match parser.parse() {
        Ok(a) => a,
        Err(e) => {
            eprintln!("Parse Error: {}", e);
            return;
        }
    };

    let mut interp = Interpreter::new(script_args);
    if let Err(e) = interp.interpret(ast) {
        eprintln!("Runtime Error: {}", e);
    }
}