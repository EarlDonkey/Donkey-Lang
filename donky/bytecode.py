from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto


class Op(Enum):
    # --- push ---
    CONST = auto()            # CONST idx  → push constants[idx]
    TRUE = auto()             # TRUE       → push True
    FALSE = auto()            # FALSE      → push False
    # --- discard ---
    POP = auto()              # POP        → discard top of stack
    # --- locals ---
    LOAD_LOCAL = auto()       # LOAD_LOCAL slot
    STORE_LOCAL = auto()      # STORE_LOCAL slot
    # --- globals ---
    DEFINE_GLOBAL = auto()    # DEFINE_GLOBAL name
    LOAD_GLOBAL = auto()      # LOAD_GLOBAL name
    STORE_GLOBAL = auto()     # STORE_GLOBAL name
    # --- arithmetic ---
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    NEG = auto()
    # --- logic ---
    NOT = auto()
    # --- comparison ---
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    # --- control ---
    JUMP = auto()             # JUMP target
    JUMP_IF_FALSE = auto()    # pop; if falsy, jump
    JUMP_IF_FALSE_PEEK = auto()  # peek; if falsy, jump (don't pop)
    JUMP_IF_TRUE_PEEK = auto()   # peek; if truthy, jump (don't pop)
    # --- functions ---
    MAKE_FN = auto()          # MAKE_FN idx  → push functions[idx]
    CALL = auto()             # CALL argc name  → pop argc args + callee, push result
    RETURN = auto()           # RETURN       → return top of stack
    # --- I/O ---
    PRINT = auto()            # PRINT        → pop and print


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
        """Return the index of value in constants, adding if not present."""
        for i, existing in enumerate(self.constants):
            if type(existing) is type(value) and existing == value:
                return i
        self.constants.append(value)
        return len(self.constants) - 1


def disassemble(code: CodeObject, name: str | None = None) -> str:
    """Render a CodeObject as a human-readable listing."""
    out: list[str] = []
    label = name or code.name
    out.append(f"=== {label} (arity={code.arity}, slots={code.slot_count}) ===")

    # show constants
    if code.constants:
        out.append("-- constants --")
        for i, c in enumerate(code.constants):
            out.append(f"  [{i}] {c!r}")

    # show function headers so you can see the nesting
    if code.functions:
        out.append("-- nested functions --")
        for i, fn in enumerate(code.functions):
            out.append(f"  [{i}] {fn.name}/arity={fn.arity}")

    # instructions
    out.append("-- instructions --")
    targets = _jump_targets(code.instructions)
    for i, instr in enumerate(code.instructions):
        if i in targets:
            out.append(f"  L{i}:")
        out.append(f"  {i:>4}  {_format_instr(instr)}")

    # recurse
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
    op, arg = instr
    if op in (Op.LOAD_GLOBAL, Op.STORE_GLOBAL, Op.DEFINE_GLOBAL):
        return f"{op.name:<18} {arg!r}"
    if op in (Op.JUMP, Op.JUMP_IF_FALSE, Op.JUMP_IF_FALSE_PEEK, Op.JUMP_IF_TRUE_PEEK):
        return f"{op.name:<18} -> L{arg}"
    return f"{op.name:<18} {arg}"