use cranelift::prelude::*;
use cranelift_object::{ObjectBuilder, ObjectModule};
use cranelift_module::{Module, Linkage, FuncId, DataDescription};
use crate::ast::{Expr, Stmt};
use crate::lexer::TokenType;
use std::collections::HashMap;

#[derive(Clone, Copy)]
pub struct RuntimeFuncs {
    pub print_id: FuncId,
    pub alloc_array_id: FuncId,
    pub array_push_id: FuncId,
    pub alloc_map_id: FuncId,
    pub map_set_id: FuncId,
    pub index_get_id: FuncId,
    pub index_set_id: FuncId,
    pub alloc_string_id: FuncId,
}

pub struct AotCompiler {
    builder_context: FunctionBuilderContext,
    ctx: codegen::Context,
    module: ObjectModule,
    user_functions: HashMap<String, FuncId>,
    runtime: RuntimeFuncs,
}

struct FunctionContext {
    variables: HashMap<String, Variable>,
}

impl AotCompiler {
    pub fn new() -> Self {
        let mut flag_builder = settings::builder();
        flag_builder.set("opt_level", "speed").unwrap();
        let isa_builder = cranelift_native::builder().unwrap();
        let isa = isa_builder.finish(settings::Flags::new(flag_builder)).unwrap();
        
        let object_builder = ObjectBuilder::new(isa, "donky_app", cranelift_module::default_libcall_names()).unwrap();
        let mut module = ObjectModule::new(object_builder);

        let mut declare = |name: &str, params: &[Type], ret: Option<Type>| {
            let mut sig = module.make_signature();
            for p in params { sig.params.push(AbiParam::new(*p)); }
            if let Some(r) = ret { sig.returns.push(AbiParam::new(r)); }
            module.declare_function(name, Linkage::Import, &sig).unwrap()
        };

        let runtime = RuntimeFuncs {
            print_id: declare("donky_print", &[types::I64], None),
            alloc_array_id: declare("donky_alloc_array", &[], Some(types::I64)),
            array_push_id: declare("donky_array_push", &[types::I64, types::I64], None),
            alloc_map_id: declare("donky_alloc_map", &[], Some(types::I64)),
            map_set_id: declare("donky_map_set", &[types::I64, types::I64, types::I64], None),
            index_get_id: declare("donky_index_get", &[types::I64, types::I64], Some(types::I64)),
            index_set_id: declare("donky_index_set", &[types::I64, types::I64, types::I64], None),
            alloc_string_id: declare("donky_alloc_string", &[types::I64], Some(types::I64)),
        };
        
        AotCompiler {
            builder_context: FunctionBuilderContext::new(),
            ctx: codegen::Context::new(),
            module,
            user_functions: HashMap::new(),
            runtime,
        }
    }

    pub fn compile_to_object(mut self, stmts: &[Stmt], output_path: &str) -> Result<(), String> {
        for stmt in stmts {
            if let Stmt::Function(name, params, _) = stmt {
                let mut sig = self.module.make_signature();
                for _ in 0..params.len() { sig.params.push(AbiParam::new(types::I64)); }
                sig.returns.push(AbiParam::new(types::I64));
                let func_id = self.module.declare_function(name, Linkage::Export, &sig).unwrap();
                self.user_functions.insert(name.clone(), func_id);
            }
        }

        for stmt in stmts {
            if let Stmt::Function(name, params, body) = stmt {
                let func_id = self.user_functions[name];
                self.compile_function(func_id, params, body);
            }
        }

        let sig = self.module.make_signature();
        // RENAME TO donky_main to avoid clashing with C's main()
        let main_id = self.module.declare_function("donky_main", Linkage::Export, &sig).unwrap();
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
                    terminated = Self::compile_stmt(&mut builder, &mut self.module, &self.runtime, &self.user_functions, &mut fctx, stmt);
                    if terminated { break; }
                }
            }

            if !terminated { builder.ins().return_(&[]); }
            builder.finalize();
        }

        self.module.define_function(main_id, &mut self.ctx).unwrap();
        self.module.clear_context(&mut self.ctx);
        
        // ObjectModule doesn't have finalize_definitions
        let product = self.module.finish();
        let bytes = product.emit().unwrap();
        std::fs::write(output_path, bytes).map_err(|e| e.to_string())?;
        Ok(())
    }

    fn compile_function(&mut self, func_id: FuncId, params: &[String], body: &Stmt) {
        let mut sig = self.module.make_signature();
        for _ in 0..params.len() { sig.params.push(AbiParam::new(types::I64)); }
        sig.returns.push(AbiParam::new(types::I64));
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
                builder.declare_var(var, types::I64);
                builder.def_var(var, block_params[i]);
                fctx.variables.insert(param_name.clone(), var);
            }

            let terminated = Self::compile_stmt(&mut builder, &mut self.module, &self.runtime, &self.user_functions, &mut fctx, body);

            if !terminated {
                let zero = builder.ins().iconst(types::I64, 0.0_f64.to_bits() as i64);
                builder.ins().return_(&[zero]);
            }
            builder.finalize();
        }

        self.module.define_function(func_id, &mut self.ctx).unwrap();
        self.module.clear_context(&mut self.ctx);
    }

    fn compile_stmt(
        builder: &mut FunctionBuilder, 
        module: &mut ObjectModule, 
        runtime: &RuntimeFuncs,
        user_funcs: &HashMap<String, FuncId>,
        fctx: &mut FunctionContext, 
        stmt: &Stmt,
    ) -> bool {
        match stmt {
            Stmt::Let(name, expr) => {
                let val = Self::compile_expr(builder, module, runtime, user_funcs, fctx, expr);
                let var = Variable::new(fctx.variables.len());
                builder.declare_var(var, types::I64);
                builder.def_var(var, val);
                fctx.variables.insert(name.clone(), var);
                false
            }
            Stmt::Assign(name, expr) => {
                let val = Self::compile_expr(builder, module, runtime, user_funcs, fctx, expr);
                let var = fctx.variables.get(name).expect(&format!("Undefined variable: {}", name));
                builder.def_var(*var, val);
                false
            }
            Stmt::IndexSet(target, index, val) => {
                let t = Self::compile_expr(builder, module, runtime, user_funcs, fctx, target);
                let i = Self::compile_expr(builder, module, runtime, user_funcs, fctx, index);
                let v = Self::compile_expr(builder, module, runtime, user_funcs, fctx, val);
                let local_callee = module.declare_func_in_func(runtime.index_set_id, builder.func);
                builder.ins().call(local_callee, &[t, i, v]);
                false
            }
            Stmt::Print(expr) => {
                let val = Self::compile_expr(builder, module, runtime, user_funcs, fctx, expr);
                let local_callee = module.declare_func_in_func(runtime.print_id, builder.func);
                builder.ins().call(local_callee, &[val]);
                false
            }
            Stmt::ExprStmt(expr) => {
                Self::compile_expr(builder, module, runtime, user_funcs, fctx, expr);
                false
            }
            Stmt::Return(expr) => {
                let val = if let Some(e) = expr {
                    Self::compile_expr(builder, module, runtime, user_funcs, fctx, e)
                } else {
                    builder.ins().iconst(types::I64, 0.0_f64.to_bits() as i64)
                };
                builder.ins().return_(&[val]);
                true
            }
            Stmt::If(cond, then_b, else_b) => {
                let cond_val = Self::compile_expr(builder, module, runtime, user_funcs, fctx, cond);
                let cond_f64 = builder.ins().bitcast(types::F64, MemFlags::new(), cond_val);
                let zero = builder.ins().f64const(0.0);
                let is_true = builder.ins().fcmp(FloatCC::NotEqual, cond_f64, zero);

                let then_block = builder.create_block();
                let else_block = builder.create_block();

                builder.ins().brif(is_true, then_block, &[], else_block, &[]);

                builder.switch_to_block(then_block);
                builder.seal_block(then_block);
                let then_term = Self::compile_stmt(builder, module, runtime, user_funcs, fctx, then_b);

                builder.switch_to_block(else_block);
                builder.seal_block(else_block);
                let else_term = if let Some(eb) = else_b {
                    Self::compile_stmt(builder, module, runtime, user_funcs, fctx, eb)
                } else { false };

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
                } else { true }
            }
            Stmt::While(cond, body) => {
                let header_block = builder.create_block();
                let body_block = builder.create_block();
                let exit_block = builder.create_block();

                builder.ins().jump(header_block, &[]);

                builder.switch_to_block(header_block);
                let cond_val = Self::compile_expr(builder, module, runtime, user_funcs, fctx, cond);
                let cond_f64 = builder.ins().bitcast(types::F64, MemFlags::new(), cond_val);
                let zero = builder.ins().f64const(0.0);
                let is_true = builder.ins().fcmp(FloatCC::NotEqual, cond_f64, zero);
                builder.ins().brif(is_true, body_block, &[], exit_block, &[]);

                builder.switch_to_block(body_block);
                builder.seal_block(body_block);
                let body_term = Self::compile_stmt(builder, module, runtime, user_funcs, fctx, body);
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
                    if Self::compile_stmt(builder, module, runtime, user_funcs, fctx, s) { return true; }
                }
                false
            }
            Stmt::Function(_, _, _) => false,
            _ => panic!("Unsupported statement in native codegen"),
        }
    }

    fn compile_expr(
        builder: &mut FunctionBuilder, 
        module: &mut ObjectModule, 
        runtime: &RuntimeFuncs,
        user_funcs: &HashMap<String, FuncId>,
        fctx: &mut FunctionContext, 
        expr: &Expr,
    ) -> Value {
        match expr {
            Expr::Number(n) => builder.ins().iconst(types::I64, n.to_bits() as i64),
            Expr::Bool(b) => builder.ins().iconst(types::I64, (if *b { 1.0_f64 } else { 0.0_f64 }).to_bits() as i64),
            Expr::String(s) => {
                // Allocate the string data in the object file
                let data_id = module.declare_data(&format!("str_{}_{}", s.len(), s.as_ptr() as usize), Linkage::Export, true, false).unwrap();
                let mut data_ctx = DataDescription::new();
                let mut bytes = s.as_bytes().to_vec();
                bytes.push(0); // null terminator for C
                data_ctx.define(bytes.into_boxed_slice());
                module.define_data(data_id, &data_ctx).unwrap();
                
                let local_data = module.declare_data_in_func(data_id, builder.func);
                let ptr = builder.ins().global_value(types::I64, local_data);
                
                let local_callee = module.declare_func_in_func(runtime.alloc_string_id, builder.func);
                let call = builder.ins().call(local_callee, &[ptr]);
                builder.inst_results(call)[0]
            }
            Expr::Ident(name) => {
                let var = fctx.variables.get(name).expect(&format!("Undefined variable: {}", name));
                builder.use_var(*var)
            }
            Expr::Call(name, args) => {
                let func_id = user_funcs.get(name).expect(&format!("Undefined function: {}", name));
                let local_callee = module.declare_func_in_func(*func_id, builder.func);
                let mut arg_vals = Vec::new();
                for arg in args {
                    arg_vals.push(Self::compile_expr(builder, module, runtime, user_funcs, fctx, arg));
                }
                let call = builder.ins().call(local_callee, &arg_vals);
                builder.inst_results(call)[0]
            }
            Expr::Array(elements) => {
                let arr_func = module.declare_func_in_func(runtime.alloc_array_id, builder.func);
                let call = builder.ins().call(arr_func, &[]);
                let arr_handle = builder.inst_results(call)[0];

                for el in elements {
                    let val = Self::compile_expr(builder, module, runtime, user_funcs, fctx, el);
                    let push_func = module.declare_func_in_func(runtime.array_push_id, builder.func);
                    builder.ins().call(push_func, &[arr_handle, val]);
                }
                arr_handle
            }
            Expr::Map(pairs) => {
                let map_func = module.declare_func_in_func(runtime.alloc_map_id, builder.func);
                let call = builder.ins().call(map_func, &[]);
                let map_handle = builder.inst_results(call)[0];

                for (k, v) in pairs {
                    let key = Self::compile_expr(builder, module, runtime, user_funcs, fctx, k);
                    let val = Self::compile_expr(builder, module, runtime, user_funcs, fctx, v);
                    let set_func = module.declare_func_in_func(runtime.map_set_id, builder.func);
                    builder.ins().call(set_func, &[map_handle, key, val]);
                }
                map_handle
            }
            Expr::Index(target, index) => {
                let t = Self::compile_expr(builder, module, runtime, user_funcs, fctx, target);
                let i = Self::compile_expr(builder, module, runtime, user_funcs, fctx, index);
                let get_func = module.declare_func_in_func(runtime.index_get_id, builder.func);
                let call = builder.ins().call(get_func, &[t, i]);
                builder.inst_results(call)[0]
            }
            Expr::Binary(left, op, right) => {
                let lhs = Self::compile_expr(builder, module, runtime, user_funcs, fctx, left);
                let rhs = Self::compile_expr(builder, module, runtime, user_funcs, fctx, right);
                
                let a_f64 = builder.ins().bitcast(types::F64, MemFlags::new(), lhs);
                let b_f64 = builder.ins().bitcast(types::F64, MemFlags::new(), rhs);
                
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
                    let bool_val = builder.ins().fcmp(cc, a_f64, b_f64);
                    let int_val = builder.ins().uextend(types::I64, bool_val);
                    let f64_val = builder.ins().fcvt_from_uint(types::F64, int_val);
                    builder.ins().bitcast(types::I64, MemFlags::new(), f64_val)
                } else {
                    let res = match op {
                        TokenType::Plus => builder.ins().fadd(a_f64, b_f64),
                        TokenType::Minus => builder.ins().fsub(a_f64, b_f64),
                        TokenType::Star => builder.ins().fmul(a_f64, b_f64),
                        TokenType::Slash => builder.ins().fdiv(a_f64, b_f64),
                        _ => panic!("Unsupported binary op"),
                    };
                    builder.ins().bitcast(types::I64, MemFlags::new(), res)
                }
            }
            _ => panic!("Unsupported expression in native codegen"),
        }
    }
}