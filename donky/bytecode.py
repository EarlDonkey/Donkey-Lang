from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto


class Op(Enum):
    # push
    CONST = auto()            # CONST idx  → push constants[idx]
    TRUE = auto()
    FALSE = auto()
    # discard
    POP = auto()
    # locals
    LOAD_LOCAL = auto()
    STORE_LOCAL = auto()
    # globals
    DEFINE_GLOBAL = auto()
    LOAD_GLOBAL = auto()
    STORE_GLOBAL = auto()
    # arithmetic
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    FLOOR_DIV = auto()
    NEG = auto()
    # logic
    NOT = auto()
    # comparison
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    # control
    JUMP = auto()
    JUMP_IF_FALSE = auto()
    JUMP_IF_FALSE_PEEK = auto()
    JUMP_IF_TRUE_PEEK = auto()
    # functions
    MAKE_FN = auto()
    CALL = auto()             # CALL argc name
    RETURN = auto()
    # I/O
    PRINT = auto()
    # arrays
    NEW_ARRAY = auto()        # NEW_ARRAY n  → pop n values, push list
    INDEX_GET = auto()        # pop idx, pop arr, push arr[idx]
    INDEX_SET = auto()        # pop val, pop idx, pop arr, mutate


@dataclass
class CodeObject:
    name: str
    arity: int
    instructions: list[tuple] = field(default_factory=list)
    positions: list[tuple[int, int]] = field(default_factory=list)
    constants: list[object] = field(default_factory=list)
    functions: list["CodeObject"] = field(default_factory=list)
    slot_count: int = 0

    def constant_index(self, value: object) -> int:
        for i, existing in enumerate(self.constants):
            if type(existing) is type(value) and existing == value:
                return i
        self.constants.append(value)
        return len(self.constants) - 1


def disassemble(code: CodeObject, name: str | None = None) -> str:
    out: list[str] = []
    label = name or code.name
    out.append(f"=== {label} (arity={code.arity}, slots={code.slot_count}) ===")

    if code.constants:
        out.append("-- constants --")
        for i, c in enumerate(code.constants):
            out.append(f"  [{i}] {c!r}")

    if code.functions:
        out.append("-- nested functions --")
        for i, fn in enumerate(code.functions):
            out.append(f"  [{i}] {fn.name}/arity={fn.arity}")

    out.append("-- instructions --")
    targets = _jump_targets(code.instructions)
    for i, instr in enumerate(code.instructions):
        if i in targets:
            out.append(f"  L{i}:")
        out.append(f"  {i:>4}  {_format_instr(instr)}")

    for i, fn in enumerate(code.functions):
        out.append("")
        out.append(disassemble(fn, name=f"{label}/fn[{i}] {fn.name}"))

    return "\n".join(out)


def _jump_targets(instructions: list[tuple]) -> set[int]:
    jump_ops = {
        Op.JUMP, Op.JUMP_IF_FALSE,
        Op.JUMP_IF_FALSE_PEEK, Op.JUMP_IF_TRUE_PEEK,
    }
    targets: set[int] = set()
    for instr in instructions:
        if instr[0] in jump_ops and len(instr) == 2:
            targets.add(instr[1])
    return targets


def _format_instr(instr: tuple) -> str:
    if len(instr) == 1:
        return instr[0].name

    op = instr[0]
    if op is Op.CALL:
        return f"{op.name:<18} argc={instr[1]} {instr[2]!r}"

    if len(instr) > 2:
        # shouldn't happen, but don't crash the disassembler if it does
        return f"{op.name:<18} {instr[1:]!r}"

    arg = instr[1]
    if op in (Op.LOAD_GLOBAL, Op.STORE_GLOBAL, Op.DEFINE_GLOBAL):
        return f"{op.name:<18} {arg!r}"
    if op in (Op.JUMP, Op.JUMP_IF_FALSE,
              Op.JUMP_IF_FALSE_PEEK, Op.JUMP_IF_TRUE_PEEK):
        return f"{op.name:<18} -> L{arg}"
    return f"{op.name:<18} {arg}"