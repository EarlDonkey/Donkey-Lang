from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    NUMBER = auto()
    STRING = auto()
    STRING_INTERP = auto()
    IDENT = auto()
    LET = auto()
    FN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    RETURN = auto()
    PRINT = auto()
    TRUE = auto()
    FALSE = auto()
    DIV = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRY = auto()
    CATCH = auto()
    THROW = auto()
    IMPORT = auto()
    STRUCT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    BANG = auto()
    AND = auto()
    OR = auto()
    EQ = auto()
    EQEQ = auto()
    NOTEQ = auto()
    LT = auto()
    LTEQ = auto()
    GT = auto()
    GTEQ = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    SEMI = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    lexeme: str
    literal: object
    line: int
    col: int

    def __repr__(self) -> str:
        return (f"Token({self.type.name}, {self.lexeme!r}, "
                f"{self.literal!r}, {self.line}:{self.col})")


class LexError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"[{line}:{col}] lex error: {message}")
        self.line = line
        self.col = col


KEYWORDS = {
    "let":      TokenType.LET,
    "fn":       TokenType.FN,
    "if":       TokenType.IF,
    "else":     TokenType.ELSE,
    "while":    TokenType.WHILE,
    "for":      TokenType.FOR,
    "in":       TokenType.IN,
    "return":   TokenType.RETURN,
    "print":    TokenType.PRINT,
    "true":     TokenType.TRUE,
    "false":    TokenType.FALSE,
    "div":      TokenType.DIV,
    "break":    TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "try":      TokenType.TRY,
    "catch":    TokenType.CATCH,
    "throw":    TokenType.THROW,
    "import":   TokenType.IMPORT,
    "struct":   TokenType.STRUCT,
}


class Lexer:
    def __init__(self, source: str):
        if source.startswith("\ufeff"):
            source = source[1:]
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return "\0" if i >= len(self.source) else self.source[i]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._at_end() or self.source[self.pos] != expected:
            return False
        self._advance()
        return True

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            self._skip_whitespace_and_comments()
            if self._at_end():
                tokens.append(Token(TokenType.EOF, "", None, self.line, self.col))
                return tokens
            tokens.append(self._next_token())

    def _skip_whitespace_and_comments(self) -> None:
        while not self._at_end():
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
            else:
                return

    def _next_token(self) -> Token:
        line, col = self.line, self.col
        ch = self._advance()

        simple = {
            "+": TokenType.PLUS,   "-": TokenType.MINUS,
            "*": TokenType.STAR,   "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "(": TokenType.LPAREN, ")": TokenType.RPAREN,
            "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
            ";": TokenType.SEMI,   ",": TokenType.COMMA,
            ":": TokenType.COLON,  ".": TokenType.DOT,
        }
        if ch in simple:
            return Token(simple[ch], ch, None, line, col)

        if ch == "=":
            if self._match("="):
                return Token(TokenType.EQEQ, "==", None, line, col)
            return Token(TokenType.EQ, "=", None, line, col)
        if ch == "!":
            if self._match("="):
                return Token(TokenType.NOTEQ, "!=", None, line, col)
            return Token(TokenType.BANG, "!", None, line, col)
        if ch == "<":
            if self._match("="):
                return Token(TokenType.LTEQ, "<=", None, line, col)
            return Token(TokenType.LT, "<", None, line, col)
        if ch == ">":
            if self._match("="):
                return Token(TokenType.GTEQ, ">=", None, line, col)
            return Token(TokenType.GT, ">", None, line, col)
        if ch == "&":
            if self._match("&"):
                return Token(TokenType.AND, "&&", None, line, col)
            raise LexError("unexpected '&' (did you mean '&&'?)", line, col)
        if ch == "|":
            if self._match("|"):
                return Token(TokenType.OR, "||", None, line, col)
            raise LexError("unexpected '|' (did you mean '||'?)", line, col)

        if ch == '"':
            return self._read_string(line, col)
        if ch.isdigit():
            return self._read_number(ch, line, col)
        if ch.isalpha() or ch == "_":
            return self._read_identifier(ch, line, col)

        raise LexError(f"unexpected character {ch!r}", line, col)

    def _read_string(self, line: int, col: int) -> Token:
        chars: list[str] = []
        has_interp = False
        while not self._at_end() and self._peek() != '"':
            ch = self._advance()
            if ch == "\\":
                if self._at_end():
                    break
                esc = self._advance()
                if esc == "$":
                    chars.append("\0")
                else:
                    mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
                    if esc not in mapping:
                        raise LexError(f"unknown escape '\\{esc}'", self.line, self.col)
                    chars.append(mapping[esc])
            elif ch == "$" and self._peek() == "{":
                has_interp = True
                chars.append("${")
                self._advance()
            else:
                chars.append(ch)
        if self._at_end():
            raise LexError("unterminated string", line, col)
        self._advance()
        value = "".join(chars)
        
        if not has_interp:
            value = value.replace("\0", "$")
            return Token(TokenType.STRING, f'"{value}"', value, line, col)
            
        return Token(TokenType.STRING_INTERP, f'"{value}"', value, line, col)

    def _read_number(self, first: str, line: int, col: int) -> Token:
        chars = [first]
        seen_dot = False
        while not self._at_end():
            ch = self._peek()
            if ch.isdigit():
                chars.append(self._advance())
            elif ch == "." and not seen_dot:
                seen_dot = True
                chars.append(self._advance())
            else:
                break
        text = "".join(chars)
        try:
            literal = float(text) if seen_dot else int(text)
        except ValueError:
            raise LexError(f"invalid number {text!r}", line, col)
        return Token(TokenType.NUMBER, text, literal, line, col)

    def _read_identifier(self, first: str, line: int, col: int) -> Token:
        chars = [first]
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            chars.append(self._advance())
        text = "".join(chars)
        return Token(KEYWORDS.get(text, TokenType.IDENT), text, None, line, col)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/hello.donk"
    with open(path, "r", encoding="utf-8-sig") as f:
        src = f.read()
    for tok in Lexer(src).tokenize():
        print(tok)