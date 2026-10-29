use cranelift::prelude::*;
use cranelift_jit::{JITBuilder, JITModule};
use cranelift_module::{Module, Linkage, FuncId};
use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;
use std::collections::HashMap;

// The Rust function the compiled machine code will call
extern "C" fn native_print(x: f64) {
    println!("{}", x);
}

struct FunctionContext {
    variables: HashMap<String, Variable>,
}

pub struct NativeCompiler {
    builder_context: FunctionBuilderContext,
    ctx: codegen::Context,
    module: JITModule,
    print_func_id: FuncId,
}

impl NativeCompiler {
    pub fn new() -> Self {
        let mut flag_builder = settings::builder();
        flag_builder.set("opt_level", "speed").unwrap();
        
        let isa_builder = cranelift_native::builder().unwrap();
        let isa = isa_builder.finish(settings::Flags::new(flag_builder)).unwrap();
        
        let mut builder = JITBuilder::with_isa(isa, cranelift_module::default_libcall_names());
        builder.symbol("donky_print", native_print as *const u8);
        
        let mut module = JITModule::new(builder);

        // Declare the signature for print: fn(f64) -> void
        let mut sig = module.make_signature();
        sig.params.push(AbiParam::new(types::F64));
        let print_func_id = module.declare_function("donky_print", Linkage::Import, &sig).unwrap();
        
        NativeCompiler {
            builder_context: FunctionBuilderContext::new(),
            ctx: codegen::Context::new(),
            module,
            print_func_id,
        }
    }

    pub fn compile_and_run(&mut self, stmts: &[Stmt]) {
        let sig = self.module.make_signature();
        
        // 1. Declare the function FIRST (borrows sig)
        let func_id = self.module.declare_function("main", Linkage::Export, &sig).unwrap();
        // 2. Then move it into the context
        self.ctx.func.signature = sig;

        {
            let mut builder = FunctionBuilder::new(&mut self.ctx.func, &mut self.builder_context);
            let entry_block = builder.create_block();
            builder.append_block_params_for_function_params(entry_block);
            builder.switch_to_block(entry_block);
            builder.seal_block(entry_block);

            let mut fctx = FunctionContext { variables: HashMap::new() };

            for stmt in stmts {
                Self::compile_stmt(&mut builder, &mut self.module, self.print_func_id, &mut fctx, stmt);
            }

            builder.ins().return_(&[]);
            builder.finalize();
        }

        self.module.define_function(func_id, &mut self.ctx).unwrap();
        self.module.clear_context(&mut self.ctx);
        self.module.finalize_definitions().unwrap();

        let code_ptr = self.module.get_finalized_function(func_id);
        let func: fn() = unsafe { std::mem::transmute(code_ptr) };
        func();
    }

    fn compile_stmt(builder: &mut FunctionBuilder, module: &mut JITModule, print_id: FuncId, fctx: &mut FunctionContext, stmt: &Stmt) {
        match stmt {
            Stmt::Let(name, expr) => {
                let val = Self::compile_expr(builder, fctx, expr);
                let var = Variable::new(fctx.variables.len());
                builder.declare_var(var, types::F64);
                builder.def_var(var, val);
                fctx.variables.insert(name.clone(), var);
            }
            Stmt::Print(expr) => {
                let val = Self::compile_expr(builder, fctx, expr);
                let local_callee = module.declare_func_in_func(print_id, builder.func);
                builder.ins().call(local_callee, &[val]);
            }
            Stmt::ExprStmt(expr) => {
                Self::compile_expr(builder, fctx, expr);
            }
            _ => panic!("Unsupported statement in native codegen"),
        }
    }

    fn compile_expr(builder: &mut FunctionBuilder, fctx: &mut FunctionContext, expr: &Expr) -> Value {
        match expr {
            Expr::Number(n) => builder.ins().f64const(*n),
            Expr::Ident(name) => {
                let var = fctx.variables.get(name).expect(&format!("Undefined variable: {}", name));
                builder.use_var(*var)
            }
            Expr::Binary(left, op, right) => {
                let lhs = Self::compile_expr(builder, fctx, left);
                let rhs = Self::compile_expr(builder, fctx, right);
                
                match op {
                    TokenType::Plus => builder.ins().fadd(lhs, rhs),
                    TokenType::Minus => builder.ins().fsub(lhs, rhs),
                    TokenType::Star => builder.ins().fmul(lhs, rhs),
                    TokenType::Slash => builder.ins().fdiv(lhs, rhs),
                    _ => panic!("Unsupported binary op in native codegen"),
                }
            }
            _ => panic!("Unsupported expression in native codegen"),
        }
    }
}