mod lexer;
mod parser;
mod ast;
mod codegen;

use std::env;
use std::fs;
use lexer::Lexer;
use parser::Parser;
use codegen::CodeGen;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        println!("Usage: donky-asm <file.donk>");
        return;
    }

    let path = &args[1];
    let source = fs::read_to_string(path).expect("Could not read file");
    
    let mut lex = Lexer::new(&source);
    let tokens = lex.tokenize().expect("Lex error");
    
    let mut parser = Parser::new(tokens);
    let ast = parser.parse().expect("Parse error");
    
    let mut generator = CodeGen::new();
    let asm = generator.compile(ast);
    
    fs::write("output.asm", asm).expect("Failed to write assembly");
    println!("Successfully generated output.asm!");
}