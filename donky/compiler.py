from donky import ast_nodes as ast
from donky.bytecode import CodeObject, Op
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
    "==": Op.EQ, "!=": Op.NE,
    "<": Op.LT, "<=": Op.LE, ">": Op.GT, ">=": Op.GE,
}


class Compiler:
    """Compiles a Donky Program into a CodeObject for the stack VM.

    v1 has no closures: functions see globals and their own frame only.
    Any block (function body, if/while body, standalone braces) creates
    a new local scope. Top-level let/fn are globals.
    """

    def __init__(self) -> None:
        self.code = CodeObject(name="<main>", arity=0)
        self.scopes: list[dict[str, int]] = []
        self.slot_counter = 0
        self.position: tuple[int, int] = (0, 0)

    def compile(self, program: ast.Program) -> CodeObject:
        for stmt in program.stmts:
            self.compile_stmt(stmt)
        self.code.slot_count = self.slot_counter
        return self.code

    # ---------- scopes ----------

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _at_global_scope(self) -> bool:
        return len(self.scopes) == 0

    def _resolve(self, name: str) -> tuple[str, int | None]:
        for scope in reversed(self.scopes):
            if name in scope:
                return ("local", scope[name])
        return ("global", None)

    def _declare_local(self, name: str) -> int:
        slot = self.slot_counter
        self.slot_counter += 1
        self.scopes[-1][name] = slot
        return slot

    # ---------- emit helpers ----------

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

    # ---------- name load/store ----------

    def _load_name(self, name: str) -> None:
        kind, slot = self._resolve(name)
        if kind == "local":
            self._emit(Op.LOAD_LOCAL, slot)
        else:
            self._emit(Op.LOAD_GLOBAL, name)

    def _declare_name(self, name: str) -> None:
        if self._at_global_scope():
            self._emit(Op.DEFINE_GLOBAL, name)
        else:
            slot = self._declare_local(name)
            self._emit(Op.STORE_LOCAL, slot)

    def _store_existing(self, name: str) -> None:
        kind, slot = self._resolve(name)
        if kind == "local":
            self._emit(Op.STORE_LOCAL, slot)
        else:
            self._emit(Op.STORE_GLOBAL, name)

    # ---------- statements ----------

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
            case ast.FnStmt(name, params, ret, body, line, col):
                fn_code = self._compile_function(name, params, body)
                idx = len(self.code.functions)
                self.code.functions.append(fn_code)
                self._emit(Op.MAKE_FN, idx)
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
            case ast.Block(stmts, line, col):
                self._compile_block_scoped(stmt)
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
        self._compile_block_scoped(body)
        self._emit(Op.JUMP, loop_start)
        self._patch_jump(jf_idx)

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

        fn_code = CodeObject(name=name, arity=len(params))
        self.code = fn_code
        self.scopes = []
        self.slot_counter = 0

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

        self.code = saved_code
        self.scopes = saved_scopes
        self.slot_counter = saved_slots
        self.position = saved_position

        return fn_code

    # ---------- expressions ----------

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
            case _:
                raise DonkyRuntimeError(
                    f"cannot compile {type(expr).__name__}"
                )