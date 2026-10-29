use cranelift::prelude::*;
use cranelift_jit::{JITBuilder, JITModule};
use cranelift_module::{Module, Linkage, FuncId};
use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;
use std::collections::HashMap;

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
    user_functions: HashMap<String, FuncId>,
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

        let mut sig = module.make_signature();
        sig.params.push(AbiParam::new(types::F64));
        let print_func_id = module.declare_function("donky_print", Linkage::Import, &sig).unwrap();
        
        NativeCompiler {
            builder_context: FunctionBuilderContext::new(),
            ctx: codegen::Context::new(),
            module,
            print_func_id,
            user_functions: HashMap::new(),
        }
    }

    pub fn compile_and_run(&mut self, stmts: &[Stmt]) {
        // 1. PREPASS: Declare all functions
        for stmt in stmts {
            if let Stmt::Function(name, params, _) = stmt {
                let mut sig = self.module.make_signature();
                for _ in 0..params.len() { sig.params.push(AbiParam::new(types::F64)); }
                sig.returns.push(AbiParam::new(types::F64));
                let func_id = self.module.declare_function(name, Linkage::Export, &sig).unwrap();
                self.user_functions.insert(name.clone(), func_id);
            }
        }

        // 2. DEFINE USER FUNCTIONS
        for stmt in stmts {
            if let Stmt::Function(name, params, body) = stmt {
                let func_id = self.user_functions[name];
                self.compile_function(func_id, params, body);
            }
        }

        // 3. DEFINE MAIN
        let sig = self.module.make_signature();
        let main_id = self.module.declare_function("main", Linkage::Export, &sig).unwrap();
        self.ctx.func.signature = sig;

        {
            let mut builder = FunctionBuilder::new(&mut self.ctx.func, &mut self.builder_context);
            let entry_block = builder.create_block();
            builder.append_block_params_for_function_params(entry_block);
            builder.switch_to_block(entry_block);
            builder.seal_block(entry_block);

            let mut fctx = FunctionContext { variables: HashMap::new() };
            let mut terminated = false;

            for stmt in stmts {
                if !matches!(stmt, Stmt::Function(_, _, _)) {
                    terminated = Self::compile_stmt(&mut builder, &mut self.module, self.print_func_id, &self.user_functions, &mut fctx, stmt);
                    if terminated { break; }
                }
            }

            if !terminated {
                builder.ins().return_(&[]);
            }
            builder.finalize();
        }

        self.module.define_function(main_id, &mut self.ctx).unwrap();
        self.module.clear_context(&mut self.ctx);
        self.module.finalize_definitions().unwrap();

        let code_ptr = self.module.get_finalized_function(main_id);
        let func: fn() = unsafe { std::mem::transmute(code_ptr) };
        func();
    }

    fn compile_function(&mut self, func_id: FuncId, params: &[String], body: &Stmt) {
        let mut sig = self.module.make_signature();
        for _ in 0..params.len() { sig.params.push(AbiParam::new(types::F64)); }
        sig.returns.push(AbiParam::new(types::F64));
        self.ctx.func.signature = sig;

        {
            let mut builder = FunctionBuilder::new(&mut self.ctx.func, &mut self.builder_context);
            let entry_block = builder.create_block();
            builder.append_block_params_for_function_params(entry_block);
            builder.switch_to_block(entry_block);
            builder.seal_block(entry_block);

            let mut fctx = FunctionContext { variables: HashMap::new() };
            let block_params: Vec<Value> = builder.block_params(entry_block).to_vec();

            for (i, param_name) in params.iter().enumerate() {
                let var = Variable::new(fctx.variables.len());
                builder.declare_var(var, types::F64);
                builder.def_var(var, block_params[i]);
                fctx.variables.insert(param_name.clone(), var);
            }

            let terminated = Self::compile_stmt(&mut builder, &mut self.module, self.print_func_id, &self.user_functions, &mut fctx, body);

            if !terminated {
                let zero = builder.ins().f64const(0.0);
                builder.ins().return_(&[zero]);
            }
            builder.finalize();
        }

        self.module.define_function(func_id, &mut self.ctx).unwrap();
        self.module.clear_context(&mut self.ctx);
    }

    fn compile_stmt(
        builder: &mut FunctionBuilder,
        module: &mut JITModule,
        print_id: FuncId,
        user_funcs: &HashMap<String, FuncId>,
        fctx: &mut FunctionContext,
        stmt: &Stmt,
    ) -> bool { // Returns true if this statement guarantees termination (like return)
        match stmt {
            Stmt::Let(name, expr) => {
                let val = Self::compile_expr(builder, module, user_funcs, fctx, expr);
                let var = Variable::new(fctx.variables.len());
                builder.declare_var(var, types::F64);
                builder.def_var(var, val);
                fctx.variables.insert(name.clone(), var);
                false
            }
            Stmt::Assign(name, expr) => {
                let val = Self::compile_expr(builder, module, user_funcs, fctx, expr);
                let var = fctx.variables.get(name).expect(&format!("Undefined variable: {}", name));
                builder.def_var(*var, val);
                false
            }
            Stmt::Print(expr) => {
                let val = Self::compile_expr(builder, module, user_funcs, fctx, expr);
                let local_callee = module.declare_func_in_func(print_id, builder.func);
                builder.ins().call(local_callee, &[val]);
                false
            }
            Stmt::ExprStmt(expr) => {
                Self::compile_expr(builder, module, user_funcs, fctx, expr);
                false
            }
            Stmt::Return(expr) => {
                let val = if let Some(e) = expr {
                    Self::compile_expr(builder, module, user_funcs, fctx, e)
                } else {
                    builder.ins().f64const(0.0)
                };
                builder.ins().return_(&[val]);
                true
            }
            Stmt::If(cond, then_b, else_b) => {
                let cond_val = Self::compile_expr(builder, module, user_funcs, fctx, cond);
                let zero = builder.ins().f64const(0.0);
                let is_true = builder.ins().fcmp(FloatCC::NotEqual, cond_val, zero);

                let then_block = builder.create_block();
                let else_block = builder.create_block();

                builder.ins().brif(is_true, then_block, &[], else_block, &[]);

                builder.switch_to_block(then_block);
                builder.seal_block(then_block);
                let then_term = Self::compile_stmt(builder, module, print_id, user_funcs, fctx, then_b);

                builder.switch_to_block(else_block);
                builder.seal_block(else_block);
                let else_term = if let Some(eb) = else_b {
                    Self::compile_stmt(builder, module, print_id, user_funcs, fctx, eb)
                } else {
                    false
                };

                if !then_term || !else_term {
                    let merge_block = builder.create_block();
                    if !then_term {
                        builder.switch_to_block(then_block);
                        builder.ins().jump(merge_block, &[]);
                    }
                    if !else_term {
                        builder.switch_to_block(else_block);
                        builder.ins().jump(merge_block, &[]);
                    }
                    builder.switch_to_block(merge_block);
                    builder.seal_block(merge_block);
                    false
                } else {
                    true
                }
            }
            Stmt::While(cond, body) => {
                let header_block = builder.create_block();
                let body_block = builder.create_block();
                let exit_block = builder.create_block();

                builder.ins().jump(header_block, &[]);

                builder.switch_to_block(header_block);
                let cond_val = Self::compile_expr(builder, module, user_funcs, fctx, cond);
                let zero = builder.ins().f64const(0.0);
                let is_true = builder.ins().fcmp(FloatCC::NotEqual, cond_val, zero);
                builder.ins().brif(is_true, body_block, &[], exit_block, &[]);

                builder.switch_to_block(body_block);
                builder.seal_block(body_block);
                let body_term = Self::compile_stmt(builder, module, print_id, user_funcs, fctx, body);
                if !body_term {
                    builder.ins().jump(header_block, &[]);
                }

                builder.switch_to_block(exit_block);
                builder.seal_block(exit_block);
                builder.seal_block(header_block);
                false
            }
            Stmt::Block(stmts) => {
                for s in stmts {
                    let term = Self::compile_stmt(builder, module, print_id, user_funcs, fctx, s);
                    if term {
                        return true;
                    }
                }
                false
            }
            Stmt::Function(_, _, _) => false,
            _ => panic!("Unsupported statement in native codegen"),
        }
    }

    fn compile_expr(
        builder: &mut FunctionBuilder,
        module: &mut JITModule,
        user_funcs: &HashMap<String, FuncId>,
        fctx: &mut FunctionContext,
        expr: &Expr,
    ) -> Value {
        match expr {
            Expr::Number(n) => builder.ins().f64const(*n),
            Expr::Bool(b) => builder.ins().f64const(if *b { 1.0 } else { 0.0 }),
            Expr::Ident(name) => {
                let var = fctx.variables.get(name).expect(&format!("Undefined variable: {}", name));
                builder.use_var(*var)
            }
            Expr::Call(name, args) => {
                let func_id = user_funcs.get(name).expect(&format!("Undefined function: {}", name));
                let local_callee = module.declare_func_in_func(*func_id, builder.func);
                let mut arg_vals = Vec::new();
                for arg in args {
                    arg_vals.push(Self::compile_expr(builder, module, user_funcs, fctx, arg));
                }
                let call = builder.ins().call(local_callee, &arg_vals);
                builder.inst_results(call)[0]
            }
            Expr::Binary(left, op, right) => {
                let lhs = Self::compile_expr(builder, module, user_funcs, fctx, left);
                let rhs = Self::compile_expr(builder, module, user_funcs, fctx, right);
                
                let cmp = match op {
                    TokenType::EqEq => Some(FloatCC::Equal),
                    TokenType::NotEq => Some(FloatCC::NotEqual),
                    TokenType::Lt => Some(FloatCC::LessThan),
                    TokenType::LtEq => Some(FloatCC::LessThanOrEqual),
                    TokenType::Gt => Some(FloatCC::GreaterThan),
                    TokenType::GtEq => Some(FloatCC::GreaterThanOrEqual),
                    _ => None,
                };

                if let Some(cc) = cmp {
                    let bool_val = builder.ins().fcmp(cc, lhs, rhs);
                    let int_val = builder.ins().uextend(types::I64, bool_val);
                    builder.ins().fcvt_from_uint(types::F64, int_val)
                } else {
                    match op {
                        TokenType::Plus => builder.ins().fadd(lhs, rhs),
                        TokenType::Minus => builder.ins().fsub(lhs, rhs),
                        TokenType::Star => builder.ins().fmul(lhs, rhs),
                        TokenType::Slash => builder.ins().fdiv(lhs, rhs),
                        _ => panic!("Unsupported binary op in native codegen"),
                    }
                }
            }
            _ => panic!("Unsupported expression in native codegen"),
        }
    }
}