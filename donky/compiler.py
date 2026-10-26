from dataclasses import dataclass

from donky import ast_nodes as ast
from donky.bytecode import CodeObject, Op, UpvalueDesc
from donky.errors import DonkyRuntimeError


class CompileError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        if line > 0:
            super().__init__(f"[{line}:{col}] compile error: {message}")
        else:
            super().__init__(f"compile error: {message}")
        self.line = line
        self.col = col


BIN_OP_MAP = {
    "+": Op.ADD, "-": Op.SUB, "*": Op.MUL,
    "/": Op.DIV, "%": Op.MOD,
    "div": Op.FLOOR_DIV,
    "==": Op.EQ, "!=": Op.NE,
    "<": Op.LT, "<=": Op.LE, ">": Op.GT, ">=": Op.GE,
}


@dataclass
class CompileContext:
    code: CodeObject
    scopes: list[dict[str, int]]
    slot_counter: int


@dataclass
class LoopContext:
    start_offset: int
    break_patches: list[int]
    try_depth: int


class Compiler:
    def __init__(self) -> None:
        self.code = CodeObject(name="<main>", arity=0)
        self.scopes: list[dict[str, int]] = []
        self.slot_counter = 0
        self.position: tuple[int, int] = (0, 0)
        self.enclosing: list[CompileContext] = []
        self.loop_stack: list[LoopContext] = []
        self.try_depth = 0

    def compile(self, program: ast.Program) -> CodeObject:
        for stmt in program.stmts:
            self.compile_stmt(stmt)
        self.code.slot_count = self.slot_counter
        return self.code

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _at_global_scope(self) -> bool:
        return len(self.scopes) == 0

    def _resolve_local_in(self, scopes: list[dict[str, int]],
                          name: str) -> int | None:
        for scope in reversed(scopes):
            if name in scope:
                return scope[name]
        return None

    def _declare_local(self, name: str) -> int:
        slot = self.slot_counter
        self.slot_counter += 1
        self.scopes[-1][name] = slot
        return slot

    def _add_upvalue(self, code: CodeObject,
                     from_parent_local: bool, index: int) -> int:
        for i, uv in enumerate(code.upvalues):
            if uv.from_parent_local == from_parent_local and uv.index == index:
                return i
        code.upvalues.append(UpvalueDesc(from_parent_local, index))
        return len(code.upvalues) - 1

    def _resolve_upvalue_at(self, name: str, code: CodeObject,
                            enclosing: list[CompileContext]) -> int | None:
        if not enclosing:
            return None
        parent = enclosing[-1]
        slot = self._resolve_local_in(parent.scopes, name)
        if slot is not None:
            return self._add_upvalue(code, True, slot)
        parent_idx = self._resolve_upvalue_at(name, parent.code, enclosing[:-1])
        if parent_idx is not None:
            return self._add_upvalue(code, False, parent_idx)
        return None

    def _resolve(self, name: str) -> tuple[str, int | None]:
        slot = self._resolve_local_in(self.scopes, name)
        if slot is not None:
            return ("local", slot)
        idx = self._resolve_upvalue_at(name, self.code, self.enclosing)
        if idx is not None:
            return ("upvalue", idx)
        return ("global", None)

    def _emit(self, op: Op, *args) -> int:
        idx = len(self.code.instructions)
        self.code.instructions.append((op,) + args)
        self.code.positions.append(self.position)
        return idx

    def _emit_jump(self, op: Op) -> int:
        idx = len(self.code.instructions)
        self.code.instructions.append((op, -1))
        self.code.positions.append(self.position)
        return idx

    def _patch_jump(self, idx: int) -> None:
        op = self.code.instructions[idx][0]
        self.code.instructions[idx] = (op, len(self.code.instructions))

    def _current_offset(self) -> int:
        return len(self.code.instructions)

    def _load_name(self, name: str) -> None:
        kind, idx = self._resolve(name)
        if kind == "local":
            self._emit(Op.LOAD_LOCAL, idx)
        elif kind == "upvalue":
            self._emit(Op.LOAD_UPVALUE, idx)
        else:
            self._emit(Op.LOAD_GLOBAL, name)

    def _declare_name(self, name: str) -> None:
        if self._at_global_scope():
            self._emit(Op.DEFINE_GLOBAL, name)
        else:
            slot = self._declare_local(name)
            self._emit(Op.STORE_LOCAL, slot)

    def _store_existing(self, name: str) -> None:
        kind, idx = self._resolve(name)
        if kind == "local":
            self._emit(Op.STORE_LOCAL, idx)
        elif kind == "upvalue":
            self._emit(Op.STORE_UPVALUE, idx)
        else:
            self._emit(Op.STORE_GLOBAL, name)

    def _compile_closure_expr(self, name: str, params: list[str],
                               body: ast.Block) -> None:
        """Compile a function body into a CLOSURE and leave it on the stack."""
        fn_code = self._compile_function(name, params, body)
        fn_idx = len(self.code.functions)
        self.code.functions.append(fn_code)
        for uv in fn_code.upvalues:
            if uv.from_parent_local:
                self._emit(Op.CAPTURE_LOCAL, uv.index)
            else:
                self._emit(Op.CAPTURE_UPVALUE, uv.index)
        self._emit(Op.CLOSURE, fn_idx, len(fn_code.upvalues))

    def compile_stmt(self, stmt: ast.Stmt) -> None:
        line = getattr(stmt, "line", 0)
        col = getattr(stmt, "col", 0)
        if line > 0:
            self.position = (line, col)

        match stmt:
            case ast.LetStmt(name, value, line, col):
                self.compile_expr(value)
                self._declare_name(name)
            case ast.PrintStmt(value, line, col):
                self.compile_expr(value)
                self._emit(Op.PRINT)
            case ast.ExprStmt(expr, line, col):
                self.compile_expr(expr)
                if not isinstance(expr, ast.Assign):
                    self._emit(Op.POP)
            case ast.IfStmt(cond, then, else_, line, col):
                self._compile_if(cond, then, else_)
            case ast.WhileStmt(cond, body, line, col):
                self._compile_while(cond, body)
            case ast.ForStmt(var_name, iter_expr, body, line, col):
                self._compile_for(var_name, iter_expr, body)
            case ast.TryStmt(body, err_name, handler, line, col):
                self._compile_try(body, err_name, handler)
            case ast.ThrowStmt(value, line, col):
                self.compile_expr(value)
                self._emit(Op.THROW)
            case ast.FnStmt(name, params, ret, body, line, col):
                self._compile_closure_expr(name, params, body)
                self._declare_name(name)
            case ast.ReturnStmt(value, line, col):
                if self.code.name == "<main>":
                    raise CompileError(
                        "'return' outside of a function", line, col
                    )
                if value is not None:
                    self.compile_expr(value)
                else:
                    self._emit(Op.CONST, self.code.constant_index(None))
                self._emit(Op.RETURN)
            case ast.BreakStmt(line, col):
                if not self.loop_stack:
                    raise CompileError("'break' outside of a loop", line, col)
                loop = self.loop_stack[-1]
                for _ in range(self.try_depth - loop.try_depth):
                    self._emit(Op.POP_TRY)
                idx = self._emit_jump(Op.JUMP)
                loop.break_patches.append(idx)
            case ast.ContinueStmt(line, col):
                if not self.loop_stack:
                    raise CompileError("'continue' outside of a loop", line, col)
                loop = self.loop_stack[-1]
                for _ in range(self.try_depth - loop.try_depth):
                    self._emit(Op.POP_TRY)
                self._emit(Op.JUMP, loop.start_offset)
            case ast.Block(stmts, line, col):
                self._compile_block_scoped(stmt)
            case ast.IndexSet(name, index, value, line, col):
                self._load_name(name)
                self.compile_expr(index)
                self.compile_expr(value)
                self._emit(Op.INDEX_SET)
            case _:
                raise DonkyRuntimeError(
                    f"cannot compile {type(stmt).__name__}"
                )

    def _compile_if(self, cond, then, else_):
        saved = self.position
        self.compile_expr(cond)
        self.position = saved
        jf_idx = self._emit_jump(Op.JUMP_IF_FALSE)
        self._compile_block_scoped(then)
        if else_ is not None:
            end_idx = self._emit_jump(Op.JUMP)
            self._patch_jump(jf_idx)
            self._compile_block_scoped(else_)
            self._patch_jump(end_idx)
        else:
            self._patch_jump(jf_idx)

    def _compile_while(self, cond, body):
        saved = self.position
        loop_start = self._current_offset()
        self.compile_expr(cond)
        self.position = saved
        jf_idx = self._emit_jump(Op.JUMP_IF_FALSE)

        ctx = LoopContext(start_offset=loop_start, break_patches=[],
                          try_depth=self.try_depth)
        self.loop_stack.append(ctx)
        try:
            self._compile_block_scoped(body)
        finally:
            self.loop_stack.pop()

        self._emit(Op.JUMP, loop_start)
        self._patch_jump(jf_idx)
        for bp in ctx.break_patches:
            self._patch_jump(bp)

    def _compile_for(self, var_name, iter_expr, body):
        self.compile_expr(iter_expr)
        self._emit(Op.NEW_ITER)

        loop_start = self._current_offset()
        jf_idx = self._emit_jump(Op.ITER_NEXT)

        ctx = LoopContext(start_offset=loop_start, break_patches=[],
                          try_depth=self.try_depth)
        self.loop_stack.append(ctx)
        try:
            self._push_scope()
            try:
                slot = self._declare_local(var_name)
                self._emit(Op.STORE_LOCAL, slot)
                for s in body.stmts:
                    self.compile_stmt(s)
            finally:
                self._pop_scope()
        finally:
            self.loop_stack.pop()

        self._emit(Op.JUMP, loop_start)
        self._patch_jump(jf_idx)
        for bp in ctx.break_patches:
            self._patch_jump(bp)
        self._emit(Op.POP)

    def _compile_try(self, body, err_name, handler):
        push_try_idx = self._emit_jump(Op.PUSH_TRY)
        self.try_depth += 1
        try:
            self._compile_block_scoped(body)
        finally:
            self.try_depth -= 1
        self._emit(Op.POP_TRY)
        end_idx = self._emit_jump(Op.JUMP)
        self._patch_jump(push_try_idx)

        self._push_scope()
        try:
            slot = self._declare_local(err_name)
            self._emit(Op.STORE_LOCAL, slot)
            self._compile_block_scoped(handler)
        finally:
            self._pop_scope()
        self._patch_jump(end_idx)

    def _compile_block_scoped(self, block: ast.Block) -> None:
        self._push_scope()
        try:
            for s in block.stmts:
                self.compile_stmt(s)
        finally:
            self._pop_scope()

    def _compile_function(
        self, name: str, params: list[str], body: ast.Block
    ) -> CodeObject:
        saved_code = self.code
        saved_scopes = self.scopes
        saved_slots = self.slot_counter
        saved_position = self.position
        saved_loop_stack = self.loop_stack
        saved_try_depth = self.try_depth

        self.enclosing.append(
            CompileContext(saved_code, saved_scopes, saved_slots)
        )
        fn_code = CodeObject(name=name, arity=len(params))
        self.code = fn_code
        self.scopes = []
        self.slot_counter = 0
        self.loop_stack = []
        self.try_depth = 0

        try:
            self._push_scope()
            try:
                for p in params:
                    self._declare_local(p)
                for s in body.stmts:
                    self.compile_stmt(s)
                if (
                    not self.code.instructions
                    or self.code.instructions[-1][0] != Op.RETURN
                ):
                    self._emit(Op.CONST, fn_code.constant_index(None))
                    self._emit(Op.RETURN)
            finally:
                self._pop_scope()
            fn_code.slot_count = self.slot_counter
        finally:
            self.enclosing.pop()
            self.code = saved_code
            self.scopes = saved_scopes
            self.slot_counter = saved_slots
            self.position = saved_position
            self.loop_stack = saved_loop_stack
            self.try_depth = saved_try_depth

        return fn_code

    def compile_expr(self, expr: ast.Expr) -> None:
        line = getattr(expr, "line", 0)
        col = getattr(expr, "col", 0)
        if line > 0:
            self.position = (line, col)

        match expr:
            case ast.NumberLit(v, line, col):
                self._emit(Op.CONST, self.code.constant_index(v))
            case ast.StringLit(v, line, col):
                self._emit(Op.CONST, self.code.constant_index(v))
            case ast.BoolLit(v, line, col):
                self._emit(Op.TRUE if v else Op.FALSE)
            case ast.Ident(n, line, col):
                self._load_name(n)
            case ast.FnExpr(params, ret, body, line, col):
                self._compile_closure_expr("<anonymous>", params, body)
            case ast.Unary("-", operand, line, col):
                self.compile_expr(operand)
                self._emit(Op.NEG)
            case ast.Unary("!", operand, line, col):
                self.compile_expr(operand)
                self._emit(Op.NOT)
            case ast.Binary(l, "&&", r, line, col):
                self.compile_expr(l)
                end_idx = self._emit_jump(Op.JUMP_IF_FALSE_PEEK)
                self._emit(Op.POP)
                self.compile_expr(r)
                self._patch_jump(end_idx)
            case ast.Binary(l, "||", r, line, col):
                self.compile_expr(l)
                end_idx = self._emit_jump(Op.JUMP_IF_TRUE_PEEK)
                self._emit(Op.POP)
                self.compile_expr(r)
                self._patch_jump(end_idx)
            case ast.Binary(l, op, r, line, col):
                if op not in BIN_OP_MAP:
                    raise DonkyRuntimeError(f"unknown operator '{op}'")
                self.compile_expr(l)
                self.compile_expr(r)
                self._emit(BIN_OP_MAP[op])
            case ast.Assign(n, v, line, col):
                self.compile_expr(v)
                self._store_existing(n)
            case ast.Call(callee, args, line, col):
                self._load_name(callee)
                for a in args:
                    self.compile_expr(a)
                self._emit(Op.CALL, len(args), callee)
            case ast.ArrayLit(elems, line, col):
                for e in elems:
                    self.compile_expr(e)
                self._emit(Op.NEW_ARRAY, len(elems))
            case ast.MapLit(entries, line, col):
                for k, v in entries:
                    self.compile_expr(k)
                    self.compile_expr(v)
                self._emit(Op.NEW_MAP, len(entries))
            case ast.Index(container, index, line, col):
                self.compile_expr(container)
                self.compile_expr(index)
                self._emit(Op.INDEX_GET)
            case _:
                raise DonkyRuntimeError(
                    f"cannot compile {type(expr).__name__}"
                )