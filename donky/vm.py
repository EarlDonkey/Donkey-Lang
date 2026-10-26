from donky.bytecode import CodeObject, Op
from donky.builtins import install_builtins
from donky.errors import DonkyRuntimeError
from donky.values import (
    Builtin, Cell, Closure, Environment, format_value, is_int, is_number,
    type_name,
)


class Frame:
    __slots__ = ("code", "ip", "slots", "closure", "handlers")

    def __init__(self, code: CodeObject, closure: Closure | None = None):
        self.code = code
        self.ip = 0
        self.slots: list[Cell] = [Cell() for _ in range(code.slot_count)]
        self.closure = closure
        self.handlers: list[tuple[int, int]] = []


class VM:
    def __init__(self, args: list[str] | None = None):
        self.globals = Environment()
        install_builtins(self.globals, args)
        self.stack: list[object] = []
        self.frames: list[Frame] = []
        self.position: tuple[int, int] = (0, 0)

    def run(self, code: CodeObject) -> None:
        self.frames = [Frame(code, None)]
        self.stack = []
        self.position = (0, 0)
        self._execute()

    def _execute(self) -> None:
        while self.frames:
            frame = self.frames[-1]
            instrs = frame.code.instructions

            if frame.ip >= len(instrs):
                if len(self.frames) == 1:
                    self.frames.pop()
                    return
                raise DonkyRuntimeError(
                    f"function '{frame.code.name}' reached end without RETURN"
                )

            idx = frame.ip
            instr = instrs[idx]
            if idx < len(frame.code.positions):
                self.position = frame.code.positions[idx]
            frame.ip += 1

            try:
                self._dispatch(instr, frame)
            except DonkyRuntimeError as e:
                if e.line == 0:
                    line, col = self.position
                    e = DonkyRuntimeError(e.message, line, col)
                self._handle_error(e)

    def _handle_error(self, err: DonkyRuntimeError) -> None:
        while self.frames:
            frame = self.frames[-1]
            if frame.handlers:
                target, depth = frame.handlers.pop()
                del self.stack[depth:]
                self.stack.append(err.message)
                frame.ip = target
                return
            self.frames.pop()
        raise err

    def _dispatch(self, instr: tuple, frame: Frame) -> None:
        op = instr[0]

        match op:
            case Op.CONST:
                self.stack.append(frame.code.constants[instr[1]])
            case Op.TRUE:
                self.stack.append(True)
            case Op.FALSE:
                self.stack.append(False)
            case Op.POP:
                self.stack.pop()
            case Op.LOAD_LOCAL:
                self.stack.append(frame.slots[instr[1]].value)
            case Op.STORE_LOCAL:
                frame.slots[instr[1]].value = self.stack.pop()
            case Op.LOAD_UPVALUE:
                self.stack.append(frame.closure.upvalues[instr[1]].value)
            case Op.STORE_UPVALUE:
                frame.closure.upvalues[instr[1]].value = self.stack.pop()
            case Op.CAPTURE_LOCAL:
                self.stack.append(frame.slots[instr[1]])
            case Op.CAPTURE_UPVALUE:
                self.stack.append(frame.closure.upvalues[instr[1]])
            case Op.DEFINE_GLOBAL:
                self.globals.define(instr[1], self.stack.pop())
            case Op.LOAD_GLOBAL:
                try:
                    self.stack.append(self.globals.get(instr[1]))
                except DonkyRuntimeError:
                    raise self._err(f"undefined variable '{instr[1]}'")
            case Op.STORE_GLOBAL:
                try:
                    self.globals.assign(instr[1], self.stack.pop())
                except DonkyRuntimeError:
                    raise self._err(
                        f"assignment to undefined variable '{instr[1]}'"
                    )
            case Op.ADD:
                r = self.stack.pop()
                l = self.stack.pop()
                self.stack.append(self._add(l, r))
            case Op.SUB:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_num("-", l, r)
                self.stack.append(l - r)
            case Op.MUL:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_num("*", l, r)
                self.stack.append(l * r)
            case Op.DIV:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_num("/", l, r)
                if r == 0:
                    raise self._err("division by zero")
                self.stack.append(l / r)
            case Op.MOD:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_num("%", l, r)
                if r == 0:
                    raise self._err("modulo by zero")
                self.stack.append(l % r)
            case Op.FLOOR_DIV:
                r = self.stack.pop()
                l = self.stack.pop()
                self.stack.append(self._floor_div(l, r))
            case Op.NEG:
                v = self.stack.pop()
                if not is_number(v):
                    raise self._err(
                        f"unary '-' expects number, got {type_name(v)}"
                    )
                self.stack.append(-v)
            case Op.NOT:
                v = self.stack.pop()
                if not isinstance(v, bool):
                    raise self._err(
                        f"unary '!' expects bool, got {type_name(v)}"
                    )
                self.stack.append(not v)
            case Op.EQ:
                r = self.stack.pop()
                l = self.stack.pop()
                self.stack.append(l == r)
            case Op.NE:
                r = self.stack.pop()
                l = self.stack.pop()
                self.stack.append(l != r)
            case Op.LT:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_cmp("<", l, r)
                self.stack.append(l < r)
            case Op.LE:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_cmp("<=", l, r)
                self.stack.append(l <= r)
            case Op.GT:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_cmp(">", l, r)
                self.stack.append(l > r)
            case Op.GE:
                r = self.stack.pop()
                l = self.stack.pop()
                self._check_cmp(">=", l, r)
                self.stack.append(l >= r)
            case Op.JUMP:
                frame.ip = instr[1]
            case Op.JUMP_IF_FALSE:
                v = self.stack.pop()
                if not isinstance(v, bool):
                    raise self._err(
                        f"condition must be bool, got {type_name(v)}"
                    )
                if not v:
                    frame.ip = instr[1]
            case Op.JUMP_IF_FALSE_PEEK:
                v = self.stack[-1]
                if not isinstance(v, bool):
                    raise self._err(f"'&&' expects bool, got {type_name(v)}")
                if not v:
                    frame.ip = instr[1]
            case Op.JUMP_IF_TRUE_PEEK:
                v = self.stack[-1]
                if not isinstance(v, bool):
                    raise self._err(f"'||' expects bool, got {type_name(v)}")
                if v:
                    frame.ip = instr[1]
            case Op.CLOSURE:
                fn_idx = instr[1]
                n_upvals = instr[2]
                cells = [self.stack.pop() for _ in range(n_upvals)]
                cells.reverse()
                self.stack.append(Closure(frame.code.functions[fn_idx], cells))
            case Op.CALL:
                self._call(instr[1], instr[2])
            case Op.RETURN:
                v = self.stack.pop()
                self._return(v)
            case Op.PRINT:
                print(format_value(self.stack.pop()))
            case Op.NEW_ARRAY:
                n = instr[1]
                elems = [self.stack.pop() for _ in range(n)]
                elems.reverse()
                self.stack.append(elems)
            case Op.NEW_MAP:
                n = instr[1]
                entries = [self.stack.pop() for _ in range(2 * n)]
                entries.reverse()
                result = {}
                for i in range(n):
                    k = entries[2 * i]
                    v = entries[2 * i + 1]
                    if isinstance(k, (list, dict)):
                        raise self._err(
                            f"map key cannot be {type_name(k)}"
                        )
                    result[k] = v
                self.stack.append(result)
            case Op.NEW_ITER:
                container = self.stack.pop()
                if isinstance(container, dict):
                    self.stack.append(iter(list(container.keys())))
                elif isinstance(container, (list, str)):
                    self.stack.append(iter(list(container)))
                else:
                    raise self._err(
                        f"cannot iterate {type_name(container)}"
                    )
            case Op.ITER_NEXT:
                it = self.stack[-1]
                try:
                    val = next(it)
                except StopIteration:
                    frame.ip = instr[1]
                else:
                    self.stack.append(val)
            case Op.INDEX_GET:
                index = self.stack.pop()
                container = self.stack.pop()
                if isinstance(container, dict):
                    if index not in container:
                        raise self._err(
                            f"key {format_value(index)!r} not in map"
                        )
                    self.stack.append(container[index])
                else:
                    self._check_index(container, index)
                    self.stack.append(container[index])
            case Op.INDEX_SET:
                value = self.stack.pop()
                index = self.stack.pop()
                container = self.stack.pop()
                if isinstance(container, str):
                    raise self._err(
                        "cannot assign to string index (strings are immutable)"
                    )
                if isinstance(container, dict):
                    if isinstance(index, (list, dict)):
                        raise self._err(
                            f"map key cannot be {type_name(index)}"
                        )
                    container[index] = value
                else:
                    self._check_index(container, index)
                    container[index] = value
            case Op.PUSH_TRY:
                frame.handlers.append((instr[1], len(self.stack)))
            case Op.POP_TRY:
                frame.handlers.pop()
            case Op.THROW:
                msg = self.stack.pop()
                if not isinstance(msg, str):
                    raise self._err(
                        f"throw expects string, got {type_name(msg)}"
                    )
                raise self._err(msg)
            case _:
                raise self._err(f"unknown opcode {op}")

    def _add(self, l: object, r: object) -> object:
        if is_number(l) and is_number(r):
            return l + r
        if isinstance(l, str) and isinstance(r, str):
            return l + r
        raise self._err(
            f"'+' needs two numbers or two strings, got "
            f"{type_name(l)} and {type_name(r)}"
        )

    def _check_num(self, op: str, l: object, r: object) -> None:
        if not (is_number(l) and is_number(r)):
            raise self._err(
                f"'{op}' needs two numbers, got "
                f"{type_name(l)} and {type_name(r)}"
            )

    def _check_cmp(self, op: str, l: object, r: object) -> None:
        both_num = is_number(l) and is_number(r)
        both_str = isinstance(l, str) and isinstance(r, str)
        if not (both_num or both_str):
            raise self._err(
                f"'{op}' needs two numbers or two strings, got "
                f"{type_name(l)} and {type_name(r)}"
            )

    def _floor_div(self, l: object, r: object) -> object:
        if not (is_number(l) and is_number(r)):
            raise self._err(
                f"'div' needs two numbers, got {type_name(l)} and {type_name(r)}"
            )
        if not (is_int(l) and is_int(r)):
            raise self._err("'div' expects integers, not floats")
        if r == 0:
            raise self._err("integer division by zero")
        q = abs(l) // abs(r)
        if (l < 0) != (r < 0):
            return -q
        return q

    def _check_index(self, array: object, index: object) -> None:
        if not isinstance(array, (list, str)):
            raise self._err(
                f"cannot index {type_name(array)}, expected array or string"
            )
        if not is_int(index):
            raise self._err(
                f"index must be integer, got {type_name(index)}"
            )
        if index < 0 or index >= len(array):
            raise self._err(
                f"index {index} out of range for length {len(array)}"
            )

    def _call(self, argc: int, name: str) -> None:
        args = [self.stack.pop() for _ in range(argc)]
        args.reverse()
        callee = self.stack.pop()

        if isinstance(callee, Builtin):
            max_a = callee.max_arity if callee.max_arity is not None else callee.arity
            if not (callee.arity <= len(args) <= max_a):
                if callee.arity == max_a:
                    msg = (f"{callee.name}() expects {callee.arity} "
                           f"argument(s), got {len(args)}")
                else:
                    msg = (f"{callee.name}() expects {callee.arity} or "
                           f"{max_a} argument(s), got {len(args)}")
                raise self._err(msg)
            try:
                result = callee.impl(args)
            except DonkyRuntimeError as e:
                if e.line == 0:
                    raise self._err(e.message) from None
                raise
            self.stack.append(result)

        elif isinstance(callee, Closure):
            if len(args) != callee.code.arity:
                raise self._err(
                    f"{callee.code.name}() expects {callee.code.arity} "
                    f"argument(s), got {len(args)}"
                )
            new_frame = Frame(callee.code, callee)
            for i, a in enumerate(args):
                new_frame.slots[i].value = a
            self.frames.append(new_frame)

        elif isinstance(callee, CodeObject):
            if len(args) != callee.arity:
                raise self._err(
                    f"{callee.name}() expects {callee.arity} "
                    f"argument(s), got {len(args)}"
                )
            new_frame = Frame(callee, Closure(callee, []))
            for i, a in enumerate(args):
                new_frame.slots[i].value = a
            self.frames.append(new_frame)

        else:
            raise self._err(
                f"'{name}' is not a function (got {type_name(callee)})"
            )

    def _return(self, value: object) -> None:
        self.frames.pop()
        if self.frames:
            self.stack.append(value)

    def _err(self, msg: str) -> DonkyRuntimeError:
        line, col = self.position
        return DonkyRuntimeError(msg, line, col)