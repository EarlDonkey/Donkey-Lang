import pytest
from donky.lexer import Lexer, TokenType, LexError


def types(src):
    return [t.type for t in Lexer(src).tokenize()]


def test_simple_let():
    assert types("let x = 10;") == [
        TokenType.LET, TokenType.IDENT, TokenType.EQ,
        TokenType.NUMBER, TokenType.SEMI, TokenType.EOF,
    ]


def test_double_equals_is_one_token():
    toks = list(Lexer("==").tokenize())
    assert toks[0].type == TokenType.EQEQ
    assert toks[1].type == TokenType.EOF


def test_eq_lexeme():
    toks = list(Lexer("= == ").tokenize())
    assert toks[0].type == TokenType.EQ   and toks[0].lexeme == "="
    assert toks[1].type == TokenType.EQEQ and toks[1].lexeme == "=="


def test_noteq():
    toks = list(Lexer("!=").tokenize())
    assert toks[0].type == TokenType.NOTEQ
    assert toks[0].lexeme == "!="


def test_lteq_gteq():
    toks = list(Lexer("<= >= < >").tokenize())
    assert [t.type for t in toks[:4]] == [
        TokenType.LTEQ, TokenType.GTEQ, TokenType.LT, TokenType.GT,
    ]
    assert [t.lexeme for t in toks[:4]] == ["<=", ">=", "<", ">"]


def test_float():
    t = list(Lexer("10.5").tokenize())[0]
    assert t.type == TokenType.NUMBER
    assert t.literal == 10.5
    assert isinstance(t.literal, float)


def test_int():
    t = list(Lexer("42").tokenize())[0]
    assert t.literal == 42
    assert isinstance(t.literal, int)


def test_keyword_boundary():
    toks = list(Lexer("letx let").tokenize())
    assert toks[0].type == TokenType.IDENT
    assert toks[1].type == TokenType.LET


def test_string_escape():
    t = list(Lexer(r'"hi\nthere"').tokenize())[0]
    assert t.type == TokenType.STRING
    assert t.literal == "hi\nthere"


def test_unterminated_string():
    with pytest.raises(LexError):
        Lexer('"oops').tokenize()


def test_bad_char():
    with pytest.raises(LexError):
        Lexer("@").tokenize()


def test_comment():
    assert types("// hi\nlet") == [TokenType.LET, TokenType.EOF]


def test_position_tracking():
    toks = list(Lexer("let\n  x").tokenize())
    assert toks[0].line == 1 and toks[0].col == 1
    assert toks[1].line == 2 and toks[1].col == 3


# ---------- Session 2 additions ----------

def test_percent_token():
    assert types("5 % 3")[1] == TokenType.PERCENT


def test_bang_token():
    toks = list(Lexer("!").tokenize())
    assert toks[0].type == TokenType.BANG
    assert toks[0].lexeme == "!"


def test_bang_not_bangeq():
    toks = list(Lexer("! !=").tokenize())
    assert toks[0].type == TokenType.BANG
    assert toks[1].type == TokenType.NOTEQ


def test_and_token():
    assert types("a && b")[1] == TokenType.AND


def test_or_token():
    assert types("a || b")[1] == TokenType.OR


def test_bare_amp_errors():
    with pytest.raises(LexError):
        Lexer("a & b").tokenize()


def test_bare_pipe_errors():
    with pytest.raises(LexError):
        Lexer("a | b").tokenize()

def test_lbracket_token():
    assert types("[1]")[0] == TokenType.LBRACKET


def test_rbracket_token():
    toks = list(Lexer("[]").tokenize())
    assert toks[0].type == TokenType.LBRACKET
    assert toks[1].type == TokenType.RBRACKET


def test_div_token():
    assert types("7 div 2")[1] == TokenType.DIV


def test_div_is_keyword_not_ident():
    toks = list(Lexer("div").tokenize())
    assert toks[0].type == TokenType.DIV