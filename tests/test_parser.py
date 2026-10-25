import pytest
from donky.lexer import Lexer
from donky.parser import Parser, ParseError
from donky import ast_nodes as ast


def parse_expr(src):
    return Parser(Lexer(src).tokenize()).parse_expr()


def parse_program(src):
    return Parser(Lexer(src).tokenize()).parse()


# ---------- expression tests ----------

def test_precedence():
    e = parse_expr("1 + 2 * 3")
    assert isinstance(e, ast.Binary) and e.op == "+"
    assert isinstance(e.right, ast.Binary) and e.right.op == "*"


def test_parens():
    e = parse_expr("(1 + 2) * 3")
    assert isinstance(e, ast.Binary) and e.op == "*"
    assert isinstance(e.left, ast.Binary) and e.left.op == "+"


def test_left_assoc():
    e = parse_expr("1 - 2 - 3")
    assert isinstance(e, ast.Binary) and e.op == "-"
    assert isinstance(e.left, ast.Binary)


def test_unary():
    e = parse_expr("-x")
    assert isinstance(e, ast.Unary) and e.op == "-"


def test_call_no_args():
    e = parse_expr("f()")
    assert isinstance(e, ast.Call) and e.callee == "f" and e.args == []


def test_call_args():
    e = parse_expr("f(1, 2 + 3)")
    assert isinstance(e, ast.Call) and len(e.args) == 2


def test_bad_paren():
    with pytest.raises(ParseError):
        parse_expr("(1 + 2")


# ---------- statement tests ----------

def test_let_stmt():
    p = parse_program("let x = 1;")
    assert len(p.stmts) == 1
    assert isinstance(p.stmts[0], ast.LetStmt)
    assert p.stmts[0].name == "x"


def test_assignment():
    p = parse_program("x = 1 + 2;")
    s = p.stmts[0]
    assert isinstance(s, ast.ExprStmt)
    assert isinstance(s.expr, ast.Assign) and s.expr.name == "x"


def test_if_else():
    p = parse_program("if true { print(1); } else { print(2); }")
    s = p.stmts[0]
    assert isinstance(s, ast.IfStmt)
    assert len(s.then.stmts) == 1
    assert s.else_ is not None


def test_fn_with_return_type():
    p = parse_program("fn add(a, b) -> num { return a + b; }")
    s = p.stmts[0]
    assert isinstance(s, ast.FnStmt)
    assert s.name == "add" and s.params == ["a", "b"]
    assert s.return_type == "num"


def test_missing_semi_errors():
    with pytest.raises(ParseError):
        parse_program("let x = 1")


def test_missing_brace_errors():
    with pytest.raises(ParseError):
        parse_program("if true { let x = 1;")


def test_empty_block_ok():
    parse_program("if true {}")


# ---------- Session 2 additions ----------

def test_and_binds_tighter_than_or():
    e = parse_expr("a && b || c")
    assert isinstance(e, ast.Binary) and e.op == "||"
    assert isinstance(e.left, ast.Binary) and e.left.op == "&&"


def test_or_left_assoc():
    e = parse_expr("a || b || c")
    assert isinstance(e, ast.Binary) and e.op == "||"
    assert isinstance(e.left, ast.Binary) and e.left.op == "||"


def test_unary_bang():
    e = parse_expr("!true")
    assert isinstance(e, ast.Unary) and e.op == "!"


def test_bang_binds_tighter_than_eq():
    e = parse_expr("!a == b")
    assert isinstance(e, ast.Binary) and e.op == "=="
    assert isinstance(e.left, ast.Unary) and e.left.op == "!"


def test_modulo_same_precedence_as_mul():
    e = parse_expr("1 + 2 % 3")
    assert isinstance(e, ast.Binary) and e.op == "+"
    assert isinstance(e.right, ast.Binary) and e.right.op == "%"