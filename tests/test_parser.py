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
    
def test_div_same_precedence_as_mul():
    e = parse_expr("1 + 2 div 3")
    assert isinstance(e, ast.Binary) and e.op == "+"
    assert isinstance(e.right, ast.Binary) and e.right.op == "div"


def test_array_literal_empty():
    e = parse_expr("[]")
    assert isinstance(e, ast.ArrayLit) and e.elems == []


def test_array_literal_elems():
    e = parse_expr("[1, 2, 3]")
    assert isinstance(e, ast.ArrayLit) and len(e.elems) == 3


def test_index_read():
    e = parse_expr("a[0]")
    assert isinstance(e, ast.Index)
    assert isinstance(e.array, ast.Ident) and e.array.name == "a"
    assert isinstance(e.index, ast.NumberLit) and e.index.value == 0


def test_index_chain():
    e = parse_expr("a[0][1]")
    assert isinstance(e, ast.Index)
    assert isinstance(e.array, ast.Index)


def test_index_assignment():
    p = parse_program("a[0] = 5;")
    s = p.stmts[0]
    assert isinstance(s, ast.IndexSet)
    assert s.array_name == "a"


def test_array_trailing_comma_errors():
    with pytest.raises(ParseError):
        parse_expr("[1, 2,]")


def test_index_missing_bracket():
    with pytest.raises(ParseError):
        parse_expr("a[0")

def test_for_parses():
    p = parse_program("for x in arr { print(x); }")
    s = p.stmts[0]
    assert isinstance(s, ast.ForStmt) and s.var_name == "x"


def test_try_parses():
    p = parse_program("try { } catch e { }")
    s = p.stmts[0]
    assert isinstance(s, ast.TryStmt) and s.err_name == "e"


def test_throw_parses():
    p = parse_program('throw "oops";')
    assert isinstance(p.stmts[0], ast.ThrowStmt)


def test_map_literal_parses():
    e = parse_expr('{"a": 1, "b": 2}')
    assert isinstance(e, ast.MapLit) and len(e.entries) == 2


def test_empty_map_parses():
    e = parse_expr("{}")
    assert isinstance(e, ast.MapLit) and e.entries == []

def test_else_if_parses():
    p = parse_program("if false { } else if true { }")
    s = p.stmts[0]
    assert isinstance(s, ast.IfStmt)
    assert isinstance(s.else_, ast.Block)
    assert len(s.else_.stmts) == 1
    assert isinstance(s.else_.stmts[0], ast.IfStmt)


def test_else_if_chain_parses():
    p = parse_program("if a { } else if b { } else if c { } else { }")
    s = p.stmts[0]
    assert isinstance(s.else_, ast.Block)
    nested = s.else_.stmts[0]
    assert isinstance(nested, ast.IfStmt)
    assert isinstance(nested.else_, ast.Block)
    assert isinstance(nested.else_.stmts[0], ast.IfStmt)
    assert nested.else_.stmts[0].else_ is not None