from donky import ast_nodes as ast


TYPE_ANY = "any"
TYPE_NUMBER = "number"
TYPE_STRING = "string"
TYPE_BOOL = "bool"
TYPE_ARRAY = "array"
TYPE_MAP = "map"
TYPE_FUNCTION = "function"


BUILTIN_RETURNS = {
    "len":         TYPE_NUMBER,
    "str":         TYPE_STRING,
    "num":         TYPE_NUMBER,
    "type":        TYPE_STRING,
    "push":        TYPE_ANY,
    "pop":         TYPE_ANY,
    "read_file":   TYPE_STRING,
    "write_file":  TYPE_ANY,
    "file_exists": TYPE_BOOL,
    "split":       TYPE_ARRAY,
    "join":        TYPE_STRING,
    "contains":    TYPE_BOOL,
    "keys":        TYPE_ARRAY,
    "upper":       TYPE_STRING,
    "lower":       TYPE_STRING,
    "trim":        TYPE_STRING,
    "replace":     TYPE_STRING,
    "input":       TYPE_STRING,
    "sort":        TYPE_ANY,
    "tcp_listen":  TYPE_NUMBER,
    "tcp_accept":  TYPE_NUMBER,
    "tcp_read":    TYPE_STRING,
    "tcp_write":   TYPE_ANY,
    "tcp_close":   TYPE_ANY,
}


ANNOTATION_TO_TYPE = {
    "num":   TYPE_NUMBER,
    "str":   TYPE_STRING,
    "bool":  TYPE_BOOL,
    "array": TYPE_ARRAY,
    "map":   TYPE_MAP,
    "any":   TYPE_ANY,
    "void":  TYPE_ANY,
}


class TypeCheckError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"[{line}:{col}] type error: {message}")
        self.line = line
        self.col = col


class TypeChecker:
    def __init__(self) -> None:
        self.scopes: list[dict[str, str]] = [{}]
        self.fn_returns: list[str | None] = [None]
        self.fn_arities: dict[str, int] = {}
        self.structs: dict[str, dict[str, str]] = {}
        self.loop_depth = 0

    def check(self, program: ast.Program) -> None:
        for name, ret in BUILTIN_RETURNS.items():
            self.scopes[0][name] = TYPE_FUNCTION
        self.scopes[0]["args"] = TYPE_ARRAY
        for stmt in program.stmts:
            self.check_stmt(stmt)

    def _push(self) -> None:
        self.scopes.append({})

    def _pop(self) -> None:
        self.scopes.pop()

    def _lookup(self, name: str) -> str | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _define(self, name: str, t: str) -> None:
        self.scopes[-1][name] = t

    def _resolve_type(self, typ: str) -> str:
        if typ in ANNOTATION_TO_TYPE:
            return ANNOTATION_TO_TYPE[typ]
        if typ in self.structs:
            return typ
        return TYPE_ANY

    def check_stmt(self, stmt: ast.Stmt) -> None:
        match stmt:
            case ast.StructDefStmt(name, fields, line, col):
                if name in self.structs:
                    raise TypeCheckError(f"struct '{name}' already defined", line, col)
                field_dict = {}
                for f_name, f_type in fields:
                    field_dict[f_name] = self._resolve_type(f_type)
                self.structs[name] = field_dict

            case ast.LetStmt(name, value, line, col):
                t = self.infer(value)
                self._define(name, t)

            case ast.PrintStmt(value, line, col):
                self.infer(value)

            case ast.ExprStmt(expr, line, col):
                if isinstance(expr, ast.Assign):
                    self._check_assign(expr)
                else:
                    self.infer(expr)

            case ast.Assign(name, value, line, col):
                self._check_assign(stmt)

            case ast.FieldSet(obj, field, value, line, col):
                ot = self.infer(obj)
                if ot not in self.structs:
                    raise TypeCheckError(f"cannot set field on {ot}", line, col)
                if field not in self.structs[ot]:
                    raise TypeCheckError(f"struct '{ot}' has no field '{field}'", line, col)
                vt = self.infer(value)
                expected = self.structs[ot][field]
                if expected != TYPE_ANY and vt != TYPE_ANY and vt != expected:
                    raise TypeCheckError(f"field '{field}' expects {expected}, got {vt}", line, col)

            case ast.IfStmt(cond, then, else_, line, col):
                ct = self.infer(cond)
                self._check_bool(ct, cond, "if condition")
                self.check_block(then)
                if else_ is not None:
                    self.check_block(else_)

            case ast.WhileStmt(cond, body, line, col):
                ct = self.infer(cond)
                self._check_bool(ct, cond, "while condition")
                self.loop_depth += 1
                try:
                    self.check_block(body)
                finally:
                    self.loop_depth -= 1

            case ast.ForStmt(var_name, iter_expr, body, line, col):
                it = self.infer(iter_expr)
                var_type = TYPE_ANY
                if it == TYPE_STRING:
                    var_type = TYPE_STRING
                elif it not in (TYPE_ARRAY, TYPE_MAP, TYPE_ANY):
                    raise TypeCheckError(
                        f"cannot iterate {it}", iter_expr.line, iter_expr.col
                    )
                self.loop_depth += 1
                try:
                    self._push()
                    try:
                        self._define(var_name, var_type)
                        self.check_block(body)
                    finally:
                        self._pop()
                finally:
                    self.loop_depth -= 1

            case ast.FnStmt(name, params, ret, body, line, col):
                ret_t = self._resolve_type(ret)
                self.fn_arities[name] = len(params)
                self._define(name, TYPE_FUNCTION)
                self.fn_returns.append(ret_t)
                self._push()
                try:
                    for p in params:
                        self._define(p, TYPE_ANY)
                    saved_loop = self.loop_depth
                    self.loop_depth = 0
                    try:
                        for s in body.stmts:
                            self.check_stmt(s)
                    finally:
                        self.loop_depth = saved_loop
                finally:
                    self._pop()
                    self.fn_returns.pop()

            case ast.ReturnStmt(value, line, col):
                ret_t = self.fn_returns[-1]
                if ret_t is None:
                    raise TypeCheckError(
                        "'return' outside of a function", line, col
                    )
                if value is not None:
                    vt = self.infer(value)
                    if ret_t != TYPE_ANY and vt != TYPE_ANY and vt != ret_t:
                        raise TypeCheckError(
                            f"return type {vt} doesn't match declared {ret_t}",
                            value.line, value.col,
                        )

            case ast.BreakStmt(line, col):
                if self.loop_depth == 0:
                    raise TypeCheckError("'break' outside of a loop", line, col)

            case ast.ContinueStmt(line, col):
                if self.loop_depth == 0:
                    raise TypeCheckError("'continue' outside of a loop", line, col)

            case ast.TryStmt(body, err_name, handler, line, col):
                self.check_block(body)
                self._push()
                try:
                    self._define(err_name, TYPE_STRING)
                    self.check_block(handler)
                finally:
                    self._pop()

            case ast.ThrowStmt(value, line, col):
                vt = self.infer(value)
                if vt != TYPE_STRING and vt != TYPE_ANY:
                    raise TypeCheckError(
                        f"throw expects string, got {vt}", value.line, value.col
                    )

            case ast.ImportStmt(path, line, col):
                raise TypeCheckError(
                    "ImportStmt reached type checker — preprocessing not applied",
                    line, col,
                )

            case ast.Block(stmts, line, col):
                self.check_block(stmt)

            case ast.IndexSet(name, index, value, line, col):
                ct = self._lookup(name)
                if ct is None:
                    raise TypeCheckError(
                        f"undefined variable '{name}'", line, col
                    )
                self._check_index(ct, index)
                self.infer(value)

            case _:
                pass

    def check_block(self, block: ast.Block) -> None:
        self._push()
        try:
            for stmt in block.stmts:
                self.check_stmt(stmt)
        finally:
            self._pop()

    def _check_assign(self, assign: ast.Assign) -> None:
        existing = self._lookup(assign.name)
        if existing is None:
            raise TypeCheckError(
                f"assignment to undefined variable '{assign.name}'",
                assign.line, assign.col,
            )
        self.infer(assign.value)
        self._widen_to_any(assign.name)

    def _widen_to_any(self, name: str) -> None:
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = TYPE_ANY
                return

    def infer(self, expr: ast.Expr) -> str:
        match expr:
            case ast.NumberLit():
                return TYPE_NUMBER
            case ast.StringLit():
                return TYPE_STRING
            case ast.BoolLit():
                return TYPE_BOOL
            case ast.Ident(name, line, col):
                t = self._lookup(name)
                if t is None:
                    raise TypeCheckError(
                        f"undefined variable '{name}'", line, col
                    )
                return t
            case ast.InterpolatedString(parts, line, col):
                for p in parts:
                    if not isinstance(p, str):
                        self.infer(p)
                return TYPE_STRING
            case ast.StructInit(name, fields, line, col):
                if name not in self.structs:
                    raise TypeCheckError(f"undefined struct '{name}'", line, col)
                expected = self.structs[name]
                if len(fields) != len(expected):
                    raise TypeCheckError(f"expected {len(expected)} fields for '{name}', got {len(fields)}", line, col)
                for f_name, f_expr in fields:
                    if f_name not in expected:
                        raise TypeCheckError(f"struct '{name}' has no field '{f_name}'", line, col)
                    vt = self.infer(f_expr)
                    if expected[f_name] != TYPE_ANY and vt != TYPE_ANY and vt != expected[f_name]:
                        raise TypeCheckError(f"field '{f_name}' expects {expected[f_name]}, got {vt}", line, col)
                return name
            case ast.FieldAccess(obj, field, line, col):
                ot = self.infer(obj)
                if ot in self.structs:
                    if field not in self.structs[ot]:
                        raise TypeCheckError(f"struct '{ot}' has no field '{field}'", line, col)
                    return self.structs[ot][field]
                return TYPE_ANY
            case ast.ArrayLit():
                for e in expr.elems:
                    self.infer(e)
                return TYPE_ARRAY
            case ast.MapLit():
                for k, v in expr.entries:
                    self.infer(k)
                    self.infer(v)
                return TYPE_MAP
            case ast.Unary(op, operand, line, col):
                t = self.infer(operand)
                if op == "-":
                    if t not in (TYPE_NUMBER, TYPE_ANY):
                        raise TypeCheckError(
                            f"unary '-' expects number, got {t}", line, col
                        )
                    return TYPE_NUMBER
                if op == "!":
                    if t not in (TYPE_BOOL, TYPE_ANY):
                        raise TypeCheckError(
                            f"unary '!' expects bool, got {t}", line, col
                        )
                    return TYPE_BOOL
                return TYPE_ANY
            case ast.Binary(left, op, right, line, col):
                lt = self.infer(left)
                rt = self.infer(right)
                return self._check_binop(op, lt, rt, line, col)
            case ast.Assign(name, value, line, col):
                self._check_assign(expr)
                return TYPE_ANY
            case ast.Call(callee, args, line, col):
                t = self._lookup(callee)
                if t is None:
                    raise TypeCheckError(
                        f"undefined function '{callee}'", line, col
                    )
                for a in args:
                    self.infer(a)
                if callee in self.fn_arities:
                    expected = self.fn_arities[callee]
                    if len(args) != expected:
                        raise TypeCheckError(
                            f"{callee}() expects {expected} argument(s), "
                            f"got {len(args)}",
                            line, col,
                        )
                if callee in BUILTIN_RETURNS:
                    return BUILTIN_RETURNS[callee]
                return TYPE_ANY
            case ast.Index(container, index, line, col):
                ct = self.infer(container)
                self._check_index(ct, index)
                if ct == TYPE_STRING:
                    return TYPE_STRING
                return TYPE_ANY
            case _:
                return TYPE_ANY

    def _check_index(self, ct: str, index: ast.Expr) -> None:
        if ct not in (TYPE_ARRAY, TYPE_STRING, TYPE_MAP, TYPE_ANY) and ct not in self.structs:
            raise TypeCheckError(
                f"cannot index {ct}", index.line, index.col
            )
        self.infer(index)

    def _check_bool(self, t: str, node: ast.Expr, what: str) -> None:
        if t not in (TYPE_BOOL, TYPE_ANY):
            raise TypeCheckError(
                f"{what} must be bool, got {t}", node.line, node.col
            )

    def _check_binop(self, op: str, lt: str, rt: str,
                     line: int, col: int) -> str:
        if op in ("==", "!="):
            return TYPE_BOOL
        if op == "+":
            if lt == TYPE_ANY or rt == TYPE_ANY:
                return TYPE_ANY
            if lt == TYPE_NUMBER and rt == TYPE_NUMBER:
                return TYPE_NUMBER
            if lt == TYPE_STRING and rt == TYPE_STRING:
                return TYPE_STRING
            raise TypeCheckError(
                f"'+' needs number+number or string+string, got {lt}+{rt}",
                line, col,
            )
        if op in ("-", "*", "/", "%", "div"):
            if lt == TYPE_ANY or rt == TYPE_ANY:
                return TYPE_NUMBER
            if lt != TYPE_NUMBER or rt != TYPE_NUMBER:
                raise TypeCheckError(
                    f"'{op}' needs two numbers, got {lt} and {rt}", line, col
                )
            return TYPE_NUMBER
        if op in ("<", "<=", ">", ">="):
            if lt == TYPE_ANY or rt == TYPE_ANY:
                return TYPE_BOOL
            ok_num = lt == TYPE_NUMBER and rt == TYPE_NUMBER
            ok_str = lt == TYPE_STRING and rt == TYPE_STRING
            if not (ok_num or ok_str):
                raise TypeCheckError(
                    f"'{op}' needs two numbers or two strings, "
                    f"got {lt} and {rt}",
                    line, col,
                )
            return TYPE_BOOL
        if op in ("&&", "||"):
            if lt not in (TYPE_BOOL, TYPE_ANY):
                raise TypeCheckError(
                    f"'{op}' needs bool, got {lt}", line, col
                )
            if rt not in (TYPE_BOOL, TYPE_ANY):
                raise TypeCheckError(
                    f"'{op}' needs bool, got {rt}", line, col
                )
            return TYPE_BOOL
        return TYPE_ANY


def check(program: ast.Program) -> None:
    TypeChecker().check(program)