mod lexer;
mod parser;
mod ast;
mod interpreter;
mod vm;
mod heap;
mod package;
mod repl;

use std::env;
use std::fs;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        print_usage();
        return;
    }

    match args[1].as_str() {
        "install" => {
            if let Err(e) = package::install_from_manifest() { eprintln!("Package Error: {}", e); }
        }
        "add" => {
            if args.len() < 4 {
                eprintln!("Usage: donky-native add <name> <url-or-path>");
                return;
            }
            if let Err(e) = package::add_dependency(&args[2], &args[3]) {
                eprintln!("Package Error: {}", e);
            }
        }
        "repl" => {
            let script_args: Vec<String> = args[2..].to_vec();
            let mut interp = interpreter::Interpreter::new(script_args);
            repl::run(&mut interp);
        }
        "test" => {
            let path = args.get(2).map(|s| s.as_str());
            if let Err(e) = cmd_test(path) {
                eprintln!("Test runner: {}", e);
                std::process::exit(1);
            }
        }
        "build" => {
            if args.len() < 3 {
                eprintln!("Usage: donky-native build <file.donk>");
                return;
            }
            if let Err(e) = cmd_build(&args[2]) {
                eprintln!("Build Error: {}", e);
            }
        }
        "run" | "vm" => {
            if args.len() < 3 {
                eprintln!("Usage: donky-native run <file.donk|file.donk.bc> [args...]");
                return;
            }
            let script_args: Vec<String> = args[3..].to_vec();
            if let Err(e) = cmd_run(&args[2], script_args) {
                eprintln!("Runtime Error: {}", e);
            }
        }
        _ => {
            let path = &args[1];
            let script_args: Vec<String> = args[2..].to_vec();
            if let Err(e) = cmd_tree(path, script_args) {
                eprintln!("Runtime Error: {}", e);
            }
        }
    }
}

fn print_usage() {
    println!("Usage:");
    println!("  donky-native <file.donk>                 tree-walker (legacy)");
    println!("  donky-native run <file.donk|file.bc>     VM (default)");
    println!("  donky-native build <file.donk>           compile to <file.donk.bc>");
    println!("  donky-native test [dir|file]             run tests (default: ./tests)");
    println!("  donky-native repl                        interactive REPL");
    println!("  donky-native install                     install from donky.json");
    println!("  donky-native add <name> <url|path>       add dependency");
}

fn cmd_tree(path: &str, script_args: Vec<String>) -> Result<(), String> {
    let source = fs::read_to_string(path).map_err(|e| format!("{}: {}", path, e))?;
    let tokens = lexer::Lexer::new(&source).tokenize()?;
    let ast = parser::Parser::new(tokens).parse()?;
    let mut interp = interpreter::Interpreter::new(script_args);
    interp.interpret(ast)
}

fn cmd_run(path: &str, script_args: Vec<String>) -> Result<(), String> {
    if path.ends_with(".bc") {
        let bundle = vm::load_bytecode(path)?;
        let mut machine = vm::VM::new();
        machine.run(bundle.code, bundle.funcs, bundle.string_pool, script_args)?;
        return Ok(());
    }
    let source = fs::read_to_string(path).map_err(|e| format!("{}: {}", path, e))?;
    let tokens = lexer::Lexer::new(&source).tokenize()?;
    let ast = parser::Parser::new(tokens).parse()?;
    let compiler = vm::Compiler::new();
    let (code, funcs, pool) = compiler.compile(ast);
    let mut machine = vm::VM::new();
    machine.run(code, funcs, pool, script_args)?;
    Ok(())
}

fn cmd_build(path: &str) -> Result<(), String> {
    let source = fs::read_to_string(path).map_err(|e| format!("{}: {}", path, e))?;
    let tokens = lexer::Lexer::new(&source).tokenize()?;
    let ast = parser::Parser::new(tokens).parse()?;
    let compiler = vm::Compiler::new();
    let (code, funcs, pool) = compiler.compile(ast);
    let n_main = code.len();
    let n_funcs = funcs.len();
    let n_pool = pool.len();
    let out_path = format!("{}.bc", path);
    vm::save_bytecode(&out_path, code, funcs, pool)?;
    println!("Built {} ({} main ops, {} functions, {} string constants)",
        out_path, n_main, n_funcs, n_pool);
    Ok(())
}

fn cmd_test(arg: Option<&str>) -> Result<(), String> {
    let targets: Vec<std::path::PathBuf> = match arg {
        Some(p) if std::path::Path::new(p).is_file() => {
            vec![std::path::PathBuf::from(p)]
        }
        Some(p) if std::path::Path::new(p).is_dir() => collect_donk_files(p)?,
        Some(p) => return Err(format!("path not found: {}", p)),
        None => collect_donk_files("tests")?,
    };

    if targets.is_empty() {
        return Err("no .donk test files found".to_string());
    }

    let mut passed = 0usize;
    let mut failed = 0usize;
    let mut failures: Vec<(String, String)> = Vec::new();

    println!("Running {} test file(s)...\n", targets.len());

    for path in &targets {
        let name = path.strip_prefix("tests").unwrap_or(path)
            .to_string_lossy().trim_start_matches(['/', '\\']).to_string();
        match run_file(path.to_str().unwrap_or("")) {
            Ok(_) => {
                println!("  \x1b[32mPASS\x1b[0m  {}", name);
                passed += 1;
            }
            Err(e) => {
                println!("  \x1b[31mFAIL\x1b[0m  {}", name);
                failures.push((name, e));
                failed += 1;
            }
        }
    }

    println!("\n{} passed, {} failed ({} total)", passed, failed, passed + failed);

    if !failures.is_empty() {
        println!("\nFailures:");
        for (name, err) in failures {
            println!("  {}:", name);
            for line in err.lines() {
                println!("    {}", line);
            }
        }
        return Err(format!("{} test(s) failed", failed));
    }
    Ok(())
}

fn collect_donk_files(dir: &str) -> Result<Vec<std::path::PathBuf>, String> {
    let mut files = Vec::new();
    let entries = fs::read_dir(dir).map_err(|e| format!("{}: {}", dir, e))?;
    for entry in entries.flatten() {
        let p = entry.path();
        if p.is_file() && p.extension().and_then(|s| s.to_str()) == Some("donk") {
            files.push(p);
        }
    }
    files.sort();
    Ok(files)
}

fn run_file(path: &str) -> Result<(), String> {
    let source = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let tokens = lexer::Lexer::new(&source).tokenize()?;
    let ast = parser::Parser::new(tokens).parse()?;
    let compiler = vm::Compiler::new();
    let (code, funcs, pool) = compiler.compile(ast);
    let mut machine = vm::VM::new();
    machine.run(code, funcs, pool, vec![])
}