from donky import ast_nodes as ast
from donky.errors import DonkyRuntimeError
from donky.values import (
    Environment, Function, format_value, is_number, type_name,
)


class ReturnSignal(Exception):
    def __init__(self, value: object):
        super().__init__()
        self.value = value


class Interpreter:
    def __init__(self) -> None:
        self.globals = Environment()
        self.env = self.globals

    # ---------- entry ----------

    def run(self, program: ast.Program) -> None:
        try:
            for stmt in program.stmts:
                self.exec_stmt(stmt)
        except ReturnSignal:
            raise DonkyRuntimeError("'return' outside of a function")

    # ---------- statements ----------

    def exec_stmt(self, stmt: ast.Stmt) -> None:
        match stmt:
            case ast.LetStmt(name, value):
                self.env.define(name, self.eval_expr(value))
            case ast.PrintStmt(value):
                print(format_value(self.eval_expr(value)))
            case ast.ExprStmt(expr):
                self.eval_expr(expr)
            case ast.IfStmt(cond, then, else_):
                if self._require_bool(self.eval_expr(cond)):
                    self.exec_block(then)
                elif else_ is not None:
                    self.exec_block(else_)
            case ast.WhileStmt(cond, body):
                while self._require_bool(self.eval_expr(cond)):
                    self.exec_block(body)
            case ast.FnStmt(name, params, ret, body):
                self.env.define(name, Function(name, params, body, self.env, ret))
            case ast.ReturnStmt(value):
                v = None if value is None else self.eval_expr(value)
                raise ReturnSignal(v)
            case ast.Block(stmts):
                self.exec_block(stmt)
            case _:
                raise DonkyRuntimeError(f"cannot execute {type(stmt).__name__}")

    def exec_block(self, block: ast.Block) -> None:
        saved = self.env
        self.env = Environment(parent=saved)
        try:
            for s in block.stmts:
                self.exec_stmt(s)
        finally:
            self.env = saved

    # ---------- expressions ----------

    def eval_expr(self, expr: ast.Expr) -> object:
        match expr:
            case ast.NumberLit(v):
                return v
            case ast.StringLit(v):
                return v
            case ast.BoolLit(v):
                return v
            case ast.Ident(n):
                return self.env.get(n)
            case ast.Unary(op, operand):
                return self._eval_unary(op, self.eval_expr(operand))
            case ast.Binary(l, op, r):
                return self._eval_binary(op, self.eval_expr(l), self.eval_expr(r))
            case ast.Assign(n, v):
                val = self.eval_expr(v)
                self.env.assign(n, val)
                return val
            case ast.Call(callee, args):
                fn = self.env.get(callee)
                if not isinstance(fn, Function):
                    raise DonkyRuntimeError(
                        f"'{callee}' is not a function (got {type_name(fn)})"
                    )
                argvals = [self.eval_expr(a) for a in args]
                return self.call_function(fn, argvals)
            case _:
                raise DonkyRuntimeError(f"cannot evaluate {type(expr).__name__}")

    def _eval_unary(self, op: str, operand: object) -> object:
        if op == "-":
            if not is_number(operand):
                raise DonkyRuntimeError(
                    f"unary '-' expects number, got {type_name(operand)}"
                )
            return -operand
        raise DonkyRuntimeError(f"unknown unary operator '{op}'")

    def _eval_binary(self, op: str, left: object, right: object) -> object:
        if op == "+":
            if is_number(left) and is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise DonkyRuntimeError(
                f"'+' needs two numbers or two strings, got "
                f"{type_name(left)} and {type_name(right)}"
            )
        if op in ("-", "*", "/"):
            if not (is_number(left) and is_number(right)):
                raise DonkyRuntimeError(
                    f"'{op}' needs two numbers, got "
                    f"{type_name(left)} and {type_name(right)}"
                )
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if right == 0:
                raise DonkyRuntimeError("division by zero")
            return left / right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op in ("<", "<=", ">", ">="):
            both_num = is_number(left) and is_number(right)
            both_str = isinstance(left, str) and isinstance(right, str)
            if not (both_num or both_str):
                raise DonkyRuntimeError(
                    f"'{op}' needs two numbers or two strings, got "
                    f"{type_name(left)} and {type_name(right)}"
                )
            if op == "<":  return left < right
            if op == "<=": return left <= right
            if op == ">":  return left > right
            return left >= right
        raise DonkyRuntimeError(f"unknown operator '{op}'")

    # ---------- calls ----------

    def call_function(self, fn: Function, args: list[object]) -> object:
        if len(args) != len(fn.params):
            raise DonkyRuntimeError(
                f"{fn.name}() expects {len(fn.params)} argument(s), got {len(args)}"
            )
        call_env = Environment(parent=fn.closure)
        for p, a in zip(fn.params, args):
            call_env.define(p, a)

        saved = self.env
        self.env = call_env
        try:
            for s in fn.body.stmts:
                self.exec_stmt(s)
        except ReturnSignal as ret:
            return ret.value
        finally:
            self.env = saved
        return None

    # ---------- helpers ----------

    def _require_bool(self, v: object) -> bool:
        if not isinstance(v, bool):
            raise DonkyRuntimeError(f"condition must be bool, got {type_name(v)}")
        return v