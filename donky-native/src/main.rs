mod lexer;
mod parser;
mod ast;
mod interpreter;
mod vm;
mod heap;
mod package;
mod repl;
mod profiler;

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
        "bench" => {
            let path = args.get(2).map(|s| s.as_str());
            if let Err(e) = cmd_bench(path) {
                eprintln!("Bench: {}", e);
                std::process::exit(1);
            }
        }
        "profile" => {
            if args.len() < 3 {
                eprintln!("Usage: donky-native profile <file.donk>");
                return;
            }
            if let Err(e) = cmd_profile(&args[2]) {
                eprintln!("Profile: {}", e);
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
                eprintln!("Usage: donky-native run <file.donk|file.bc> [args...]");
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
    println!("  donky-native bench [dir]                 benchmark (default: ./bench)");
    println!("  donky-native profile <file.donk>         opcode profile + folded stacks");
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
        let bundle = vm::load_bytecode_auto(path)?;
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
    vm::save_bytecode_bin(&out_path, code, funcs, pool)?;
    let file_size = fs::metadata(&out_path).map(|m| m.len()).unwrap_or(0);
    println!("Built {} ({} main ops, {} functions, {} strings, {} bytes)",
        out_path, n_main, n_funcs, n_pool, file_size);
    Ok(())
}

fn cmd_profile(path: &str) -> Result<(), String> {
    let source = fs::read_to_string(path).map_err(|e| format!("{}: {}", path, e))?;
    let tokens = lexer::Lexer::new(&source).tokenize()?;
    let ast = parser::Parser::new(tokens).parse()?;
    let compiler = vm::Compiler::new();
    let (code, funcs, pool) = compiler.compile(ast);
    let mut machine = vm::VM::new();
    machine.silent = true;
    let report = machine.run_profiled(code, funcs, pool, vec![])?;
    println!("{}", report.ascii_report());

    let folded_path = "profile.folded";
    fs::write(folded_path, report.folded_stacks()).map_err(|e| e.to_string())?;
    println!("Folded stacks written to {}\n", folded_path);
    println!("To generate an SVG flame graph:");
    println!("  cargo install inferno");
    println!("  inferno-flamegraph {} > profile.svg", folded_path);
    Ok(())
}

fn cmd_test(arg: Option<&str>) -> Result<(), String> {
    let targets: Vec<std::path::PathBuf> = match arg {
        Some(p) if std::path::Path::new(p).is_file() => vec![std::path::PathBuf::from(p)],
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
            Ok(_) => { println!("  \x1b[32mPASS\x1b[0m  {}", name); passed += 1; }
            Err(e) => { println!("  \x1b[31mFAIL\x1b[0m  {}", name); failures.push((name, e)); failed += 1; }
        }
    }
    println!("\n{} passed, {} failed ({} total)", passed, failed, passed + failed);
    if !failures.is_empty() {
        println!("\nFailures:");
        for (name, err) in failures {
            println!("  {}:", name);
            for line in err.lines() { println!("    {}", line); }
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

fn cmd_bench(arg: Option<&str>) -> Result<(), String> {
    use std::time::Instant;
    let dir = arg.unwrap_or("bench");
    let files = collect_donk_files(dir)?;
    if files.is_empty() {
        return Err(format!("no .donk files in {}", dir));
    }

    const ITERS: usize = 10;
    println!("Benchmarking {} file(s), {} iterations each\n", files.len(), ITERS);
    println!("{:<20} {:>9} {:>11} {:>13} {:>10} {:>12}", "file", "compile", "run(src)", "load+run(.bc)", "ns/op", "ns/call");
    println!("{}", "-".repeat(82));
    println!("  (ns/op = nanoseconds per VM instruction, ns/call = nanoseconds per function call)\n");

    let mut total_compile = 0.0f64;
    let mut total_run = 0.0f64;
    let mut total_bc = 0.0f64;

    for path in &files {
        let p = path.to_str().unwrap_or("");
        let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
        let source = fs::read_to_string(p).map_err(|e| e.to_string())?;

        // ---- Warmup + Profile (get exact op/call counts) ----
        let mut total_ops = 0u64;
        let mut total_calls = 0u64;
        {
            let toks = lexer::Lexer::new(&source).tokenize()?;
            let ast = parser::Parser::new(toks).parse()?;
            let (code, funcs, pool) = vm::Compiler::new().compile(ast);
            let mut m = vm::VM::new();
            m.silent = true;
            let report = m.run_profiled(code, funcs, pool, vec![])?;
            total_ops = report.total_instructions;
            total_calls = report.call_counts.values().sum();
        }

        // ---- Compile-only ----
        let t = Instant::now();
        for _ in 0..ITERS {
            let toks = lexer::Lexer::new(&source).tokenize()?;
            let ast = parser::Parser::new(toks).parse()?;
            let _ = vm::Compiler::new().compile(ast);
        }
        let compile_ms = t.elapsed().as_secs_f64() * 1000.0 / ITERS as f64;

        // ---- Run from source ----
        let t = Instant::now();
        for _ in 0..ITERS {
            let toks = lexer::Lexer::new(&source).tokenize()?;
            let ast = parser::Parser::new(toks).parse()?;
            let (code, funcs, pool) = vm::Compiler::new().compile(ast);
            let mut m = vm::VM::new();
            m.silent = true;
            let _ = m.run(code, funcs, pool, vec![]);
        }
        let run_ms = t.elapsed().as_secs_f64() * 1000.0 / ITERS as f64;

        // Calculate pure execution time by subtracting compile time
        let exec_only_ms = (run_ms - compile_ms).max(0.0);
        
        let ns_per_op = if total_ops > 0 { (exec_only_ms * 1_000_000.0) / (total_ops as f64) } else { 0.0 };
        let ns_per_call = if total_calls > 0 { (exec_only_ms * 1_000_000.0) / (total_calls as f64) } else { 0.0 };

        // ---- Build once, run .bc ----
        let toks = lexer::Lexer::new(&source).tokenize()?;
        let ast = parser::Parser::new(toks).parse()?;
        let (code, funcs, pool) = vm::Compiler::new().compile(ast);
        let tmp = format!("{}/.tmp_{}.bc", dir, name);
        vm::save_bytecode_bin(&tmp, code, funcs, pool)?;

        {
            let b = vm::load_bytecode_auto(&tmp)?;
            let mut m = vm::VM::new();
            m.silent = true;
            let _ = m.run(b.code, b.funcs, b.string_pool, vec![]);
        }

        let bc_bytes = fs::read(&tmp).map_err(|e| e.to_string())?;
        let t = Instant::now();
        for _ in 0..ITERS {
            let bundle: vm::CompiledBundle = if !bc_bytes.is_empty() && bc_bytes[0] == 0xBC {
                bincode::deserialize(&bc_bytes[1..]).map_err(|e| e.to_string())?
            } else {
                serde_json::from_slice(&bc_bytes).map_err(|e| e.to_string())?
            };
            let mut m = vm::VM::new();
            m.silent = true;
            let _ = m.run(bundle.code, bundle.funcs, bundle.string_pool, vec![]);
        }
        let bc_ms = t.elapsed().as_secs_f64() * 1000.0 / ITERS as f64;

        let _ = fs::remove_file(&tmp);

        total_compile += compile_ms;
        total_run += run_ms;
        total_bc += bc_ms;

        println!("{:<20} {:>7.2}ms {:>9.2}ms {:>11.2}ms {:>8.1}ns {:>10.1}ns", name, compile_ms, run_ms, bc_ms, ns_per_op, ns_per_call);
    }

    let n = files.len() as f64;
    println!("{}", "-".repeat(82));
    println!("{:<20} {:>7.2}ms {:>9.2}ms {:>11.2}ms", "MEAN", total_compile/n, total_run/n, total_bc/n);
    Ok(())
}