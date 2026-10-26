from donky import ast_nodes as ast
from donky.builtins import install_builtins
from donky.errors import DonkyRuntimeError
from donky.values import (
    Builtin, Environment, Function, format_value, is_int, is_number, type_name,
)


class ReturnSignal(Exception):
    def __init__(self, value: object):
        super().__init__()
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class Interpreter:
    def __init__(self, args: list[str] | None = None) -> None:
        self.globals = Environment()
        self.env = self.globals
        install_builtins(self.globals, args)

    def run(self, program: ast.Program) -> None:
        for stmt in program.stmts:
            try:
                self.exec_stmt(stmt)
            except ReturnSignal:
                raise self._err(stmt, "'return' outside of a function")
            except (BreakSignal, ContinueSignal):
                raise self._err(stmt, "'break'/'continue' outside of a loop")

    def exec_stmt(self, stmt: ast.Stmt) -> None:
        match stmt:
            case ast.LetStmt(name, value, line, col):
                self.env.define(name, self.eval_expr(value))
            case ast.PrintStmt(value, line, col):
                print(format_value(self.eval_expr(value)))
            case ast.ExprStmt(expr, line, col):
                self.eval_expr(expr)
            case ast.IfStmt(cond, then, else_, line, col):
                if self._require_bool(self.eval_expr(cond), stmt):
                    self.exec_block(then)
                elif else_ is not None:
                    self.exec_block(else_)
            case ast.WhileStmt(cond, body, line, col):
                while self._require_bool(self.eval_expr(cond), stmt):
                    try:
                        self.exec_block(body)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        pass
            case ast.ForStmt(var_name, iter_expr, body, line, col):
                container = self.eval_expr(iter_expr)
                items = self._iterable(container, stmt)
                for item in items:
                    saved = self.env
                    self.env = Environment(parent=saved)
                    try:
                        self.env.define(var_name, item)
                        try:
                            for s in body.stmts:
                                self.exec_stmt(s)
                        except ContinueSignal:
                            pass
                        except BreakSignal:
                            break
                    finally:
                        self.env = saved
            case ast.TryStmt(body, err_name, handler, line, col):
                try:
                    self.exec_block(body)
                except DonkyRuntimeError as e:
                    saved = self.env
                    self.env = Environment(parent=saved)
                    try:
                        self.env.define(err_name, e.message)
                        self.exec_block(handler)
                    finally:
                        self.env = saved
            case ast.ThrowStmt(value, line, col):
                msg = self.eval_expr(value)
                if not isinstance(msg, str):
                    raise self._err(
                        stmt, f"throw expects string, got {type_name(msg)}"
                    )
                raise self._err(stmt, msg)
            case ast.FnStmt(name, params, ret, body, line, col):
                self.env.define(name, Function(name, params, body, self.env, ret))
            case ast.ReturnStmt(value, line, col):
                v = None if value is None else self.eval_expr(value)
                raise ReturnSignal(v)
            case ast.BreakStmt(line, col):
                raise BreakSignal()
            case ast.ContinueStmt(line, col):
                raise ContinueSignal()
            case ast.Block(stmts, line, col):
                self.exec_block(stmt)
            case ast.IndexSet(name, index_expr, value_expr, line, col):
                try:
                    container = self.env.get(name)
                except DonkyRuntimeError:
                    raise self._err(stmt, f"undefined variable '{name}'")
                if isinstance(container, str):
                    raise self._err(
                        stmt,
                        "cannot assign to string index (strings are immutable)",
                    )
                index = self.eval_expr(index_expr)
                value = self.eval_expr(value_expr)
                if isinstance(container, dict):
                    container[index] = value
                else:
                    self._check_index(container, index, stmt)
                    container[index] = value
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

    def _iterable(self, container: object, node: object) -> list:
        if isinstance(container, list):
            return list(container)
        if isinstance(container, str):
            return list(container)
        if isinstance(container, dict):
            return list(container.keys())
        raise self._err(
            node, f"cannot iterate {type_name(container)}"
        )

    def eval_expr(self, expr: ast.Expr) -> object:
        match expr:
            case ast.NumberLit(v, line, col):
                return v
            case ast.StringLit(v, line, col):
                return v
            case ast.BoolLit(v, line, col):
                return v
            case ast.Ident(n, line, col):
                try:
                    return self.env.get(n)
                except DonkyRuntimeError:
                    raise self._err(expr, f"undefined variable '{n}'")
            case ast.FnExpr(params, ret, body, line, col):
                return Function("<anonymous>", params, body, self.env, ret)
            case ast.InterpolatedString(parts, line, col):
                result = []
                for p in parts:
                    if isinstance(p, str):
                        result.append(p)
                    else:
                        result.append(format_value(self.eval_expr(p)))
                return "".join(result)
            case ast.Unary(op, operand, line, col):
                return self._eval_unary(op, self.eval_expr(operand), expr)
            case ast.Binary(l, "&&", r, line, col):
                left = self.eval_expr(l)
                if not isinstance(left, bool):
                    raise self._err(expr, f"'&&' expects bool, got {type_name(left)}")
                if not left:
                    return False
                right = self.eval_expr(r)
                if not isinstance(right, bool):
                    raise self._err(expr, f"'&&' expects bool, got {type_name(right)}")
                return right
            case ast.Binary(l, "||", r, line, col):
                left = self.eval_expr(l)
                if not isinstance(left, bool):
                    raise self._err(expr, f"'||' expects bool, got {type_name(left)}")
                if left:
                    return True
                right = self.eval_expr(r)
                if not isinstance(right, bool):
                    raise self._err(expr, f"'||' expects bool, got {type_name(right)}")
                return right
            case ast.Binary(l, op, r, line, col):
                return self._eval_binary(op, self.eval_expr(l), self.eval_expr(r), expr)
            case ast.Assign(n, v, line, col):
                val = self.eval_expr(v)
                try:
                    self.env.assign(n, val)
                except DonkyRuntimeError:
                    raise self._err(expr, f"assignment to undefined variable '{n}'")
                return val
            case ast.Call(callee, args, line, col):
                try:
                    fn = self.env.get(callee)
                except DonkyRuntimeError:
                    raise self._err(expr, f"undefined function '{callee}'")
                if not isinstance(fn, (Function, Builtin)):
                    raise self._err(
                        expr,
                        f"'{callee}' is not a function (got {type_name(fn)})",
                    )
                argvals = [self.eval_expr(a) for a in args]
                if isinstance(fn, Builtin):
                    return self._call_builtin(fn, argvals, expr)
                return self.call_function(fn, argvals, expr)
            case ast.ArrayLit(elems, line, col):
                return [self.eval_expr(e) for e in elems]
            case ast.MapLit(entries, line, col):
                result = {}
                for k_expr, v_expr in entries:
                    k = self.eval_expr(k_expr)
                    v = self.eval_expr(v_expr)
                    result[k] = v
                return result
            case ast.Index(container_expr, index_expr, line, col):
                container = self.eval_expr(container_expr)
                index = self.eval_expr(index_expr)
                if isinstance(container, dict):
                    if index not in container:
                        raise self._err(
                            expr, f"key {format_value(index)!r} not in map"
                        )
                    return container[index]
                self._check_index(container, index, expr)
                return container[index]
            case _:
                raise DonkyRuntimeError(f"cannot evaluate {type(expr).__name__}")

    def _check_index(self, array: object, index: object, node: object) -> None:
        if not isinstance(array, (list, str)):
            raise self._err(
                node,
                f"cannot index {type_name(array)}, expected array or string",
            )
        if not is_int(index):
            raise self._err(
                node, f"index must be integer, got {type_name(index)}"
            )
        if index < 0 or index >= len(array):
            raise self._err(
                node, f"index {index} out of range for length {len(array)}"
            )

    def _eval_unary(self, op: str, operand: object, node: ast.Expr) -> object:
        if op == "-":
            if not is_number(operand):
                raise self._err(
                    node, f"unary '-' expects number, got {type_name(operand)}"
                )
            return -operand
        if op == "!":
            if not isinstance(operand, bool):
                raise self._err(
                    node, f"unary '!' expects bool, got {type_name(operand)}"
                )
            return not operand
        raise DonkyRuntimeError(f"unknown unary operator '{op}'")

    def _eval_binary(self, op: str, left: object, right: object,
                     node: ast.Expr) -> object:
        if op == "+":
            if is_number(left) and is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise self._err(
                node,
                f"'+' needs two numbers or two strings, got "
                f"{type_name(left)} and {type_name(right)}",
            )
        if op == "div":
            if not (is_number(left) and is_number(right)):
                raise self._err(
                    node,
                    f"'div' needs two numbers, got "
                    f"{type_name(left)} and {type_name(right)}",
                )
            if not (is_int(left) and is_int(right)):
                raise self._err(node, "'div' expects integers, not floats")
            if right == 0:
                raise self._err(node, "integer division by zero")
            q = abs(left) // abs(right)
            if (left < 0) != (right < 0):
                return -q
            return q
        if op in ("-", "*", "/", "%"):
            if not (is_number(left) and is_number(right)):
                raise self._err(
                    node,
                    f"'{op}' needs two numbers, got "
                    f"{type_name(left)} and {type_name(right)}",
                )
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "%":
                if right == 0:
                    raise self._err(node, "modulo by zero")
                return left % right
            if right == 0:
                raise self._err(node, "division by zero")
            return left / right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op in ("<", "<=", ">", ">="):
            both_num = is_number(left) and is_number(right)
            both_str = isinstance(left, str) and isinstance(right, str)
            if not (both_num or both_str):
                raise self._err(
                    node,
                    f"'{op}' needs two numbers or two strings, got "
                    f"{type_name(left)} and {type_name(right)}",
                )
            if op == "<":  return left < right
            if op == "<=": return left <= right
            if op == ">":  return left > right
            return left >= right
        raise DonkyRuntimeError(f"unknown operator '{op}'")

    def call_function(self, fn: Function, args: list[object],
                      node: ast.Expr) -> object:
        if len(args) != len(fn.params):
            raise self._err(
                node,
                f"{fn.name}() expects {len(fn.params)} argument(s), got {len(args)}",
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

    def _call_builtin(self, fn: Builtin, args: list[object],
                      node: ast.Expr) -> object:
        max_a = fn.max_arity if fn.max_arity is not None else fn.arity
        if not (fn.arity <= len(args) <= max_a):
            if fn.arity == max_a:
                msg = f"{fn.name}() expects {fn.arity} argument(s), got {len(args)}"
            else:
                msg = (f"{fn.name}() expects {fn.arity} or {max_a} "
                       f"argument(s), got {len(args)}")
            raise self._err(node, msg)
        try:
            return fn.impl(args)
        except DonkyRuntimeError as e:
            if e.line == 0:
                raise self._err(node, e.message) from None
            raise

    def _require_bool(self, v: object, node: object) -> bool:
        if not isinstance(v, bool):
            raise self._err(node, f"condition must be bool, got {type_name(v)}")
        return v

    def _err(self, node: object, msg: str) -> DonkyRuntimeError:
        return DonkyRuntimeError(msg, node.line, node.col)