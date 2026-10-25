import pytest

from donky.bytecode import CodeObject, Op
from donky.compiler import CompileError, Compiler
from donky.lexer import Lexer
from donky.parser import Parser


def compile_src(src: str) -> CodeObject:
    prog = Parser(Lexer(src).tokenize()).parse()
    return Compiler().compile(prog)


def test_const_and_add():
    code = compile_src("1 + 2;")
    assert code.constants == [1, 2]
    assert code.instructions == [
        (Op.CONST, 0),
        (Op.CONST, 1),
        (Op.ADD,),
        (Op.POP,),
    ]


def test_let_global():
    code = compile_src("let x = 5;")
    assert code.instructions == [
        (Op.CONST, 0),
        (Op.DEFINE_GLOBAL, "x"),
    ]
    assert code.constants == [5]


def test_print():
    code = compile_src("print(1);")
    assert code.instructions == [
        (Op.CONST, 0),
        (Op.PRINT,),
    ]


def test_assign_global():
    code = compile_src("x = 5;")
    assert code.instructions == [
        (Op.CONST, 0),
        (Op.STORE_GLOBAL, "x"),
    ]


def test_let_local_in_block():
    code = compile_src("if true { let x = 5; }")
    assert code.instructions[0] == (Op.TRUE,)
    assert code.instructions[1][0] == Op.JUMP_IF_FALSE
    assert code.instructions[2] == (Op.CONST, 0)
    assert code.instructions[3] == (Op.STORE_LOCAL, 0)
    assert code.slot_count == 1


def test_while_loop_jumps_back():
    code = compile_src("while false { print(1); }")
    jumps = [
        (i, ins) for i, ins in enumerate(code.instructions)
        if ins[0] == Op.JUMP
    ]
    assert len(jumps) == 1
    idx, ins = jumps[0]
    assert ins[1] == 0   # jumps back to start of loop


def test_if_else_patching():
    code = compile_src("if true { print(1); } else { print(2); }")
    assert code.instructions[0] == (Op.TRUE,)
    assert code.instructions[1] == (Op.JUMP_IF_FALSE, 5)
    assert code.instructions[4][0] == Op.JUMP
    assert code.instructions[4][1] == 7


def test_and_short_circuit():
    code = compile_src("true && false;")
    assert code.instructions[0] == (Op.TRUE,)
    assert code.instructions[1][0] == Op.JUMP_IF_FALSE_PEEK
    assert code.instructions[1][1] == 4
    assert code.instructions[2] == (Op.POP,)
    assert code.instructions[3] == (Op.FALSE,)
    assert code.instructions[4] == (Op.POP,)


def test_or_short_circuit():
    code = compile_src("true || false;")
    assert code.instructions[1][0] == Op.JUMP_IF_TRUE_PEEK


def test_fn_compiles_to_nested():
    code = compile_src("fn f() -> num { return 1; }")
    assert code.instructions[0][0] == Op.MAKE_FN
    assert code.instructions[1] == (Op.DEFINE_GLOBAL, "f")
    assert len(code.functions) == 1
    inner = code.functions[0]
    assert inner.name == "f"
    assert inner.arity == 0
    assert inner.instructions == [
        (Op.CONST, 0),
        (Op.RETURN,),
    ]
    assert inner.constants == [1]


def test_fn_params_get_slots():
    code = compile_src("fn add(a, b) -> num { return a + b; }")
    inner = code.functions[0]
    assert inner.arity == 2
    assert inner.slot_count == 2
    assert inner.instructions[0] == (Op.LOAD_LOCAL, 0)
    assert inner.instructions[1] == (Op.LOAD_LOCAL, 1)
    assert inner.instructions[2] == (Op.ADD,)
    assert inner.instructions[3] == (Op.RETURN,)


def test_call_compilation():
    code = compile_src('print(len("hi"));')
    assert code.instructions[0] == (Op.LOAD_GLOBAL, "len")
    assert code.instructions[1] == (Op.CONST, 0)
    assert code.instructions[2] == (Op.CALL, 1, "len")
    assert code.instructions[3] == (Op.PRINT,)


def test_return_at_top_level_errors():
    with pytest.raises(CompileError):
        compile_src("return 1;")


def test_constant_dedup():
    code = compile_src("let x = 1; let y = 1;")
    assert code.constants == [1]


def test_unary():
    code = compile_src("-5;")
    assert code.instructions == [
        (Op.CONST, 0),
        (Op.NEG,),
        (Op.POP,),
    ]