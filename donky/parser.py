from donky.lexer import Token, TokenType
from donky import ast_nodes as ast


class ParseError(Exception):
    def __init__(self, message: str, tok: Token):
        super().__init__(f"[{tok.line}:{tok.col}] parse error: {message}")
        self.tok = tok


INFX_BP = {
    TokenType.OR:   1, TokenType.AND:  2,
    TokenType.EQEQ: 3, TokenType.NOTEQ: 3,
    TokenType.LT:   4, TokenType.LTEQ: 4, TokenType.GT: 4, TokenType.GTEQ: 4,
    TokenType.PLUS: 6, TokenType.MINUS: 6,
    TokenType.STAR: 7, TokenType.SLASH: 7, TokenType.PERCENT: 7,
    TokenType.DIV: 7,
}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.loop_depth = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _peek_ahead(self, n: int = 1) -> Token:
        i = self.pos + n
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type is not TokenType.EOF:
            self.pos += 1
        return tok

    def _check(self, t: TokenType) -> bool:
        return self._peek().type is t

    def _match(self, *types: TokenType) -> Token | None:
        if self._peek().type in types:
            return self._advance()
        return None

    def _expect(self, t: TokenType, what: str) -> Token:
        if self._check(t):
            return self._advance()
        tok = self._peek()
        raise ParseError(f"expected {what}, got {tok.type.name} ({tok.lexeme!r})", tok)

    # ---------- expressions ----------

    def parse_expr(self, min_bp: int = 0) -> ast.Expr:
        left = self.parse_prefix()
        while True:
            op = self._peek()
            bp = INFX_BP.get(op.type)
            if bp is None or bp < min_bp:
                break
            self._advance()
            right = self.parse_expr(bp + 1)
            left = ast.Binary(left, op.lexeme, right, op.line, op.col)
        return left

    def parse_prefix(self) -> ast.Expr:
        tok = self._advance()

        match tok.type:
            case TokenType.NUMBER:
                expr = ast.NumberLit(tok.literal, tok.line, tok.col)
            case TokenType.STRING:
                expr = ast.StringLit(tok.literal, tok.line, tok.col)
            case TokenType.TRUE:
                expr = ast.BoolLit(True, tok.line, tok.col)
            case TokenType.FALSE:
                expr = ast.BoolLit(False, tok.line, tok.col)
            case TokenType.MINUS:
                return ast.Unary("-", self.parse_expr(8), tok.line, tok.col)
            case TokenType.BANG:
                return ast.Unary("!", self.parse_expr(8), tok.line, tok.col)
            case TokenType.LPAREN:
                inner = self.parse_expr(0)
                self._expect(TokenType.RPAREN, "')'")
                expr = inner
            case TokenType.LBRACKET:
                elems: list[ast.Expr] = []
                if not self._check(TokenType.RBRACKET):
                    elems.append(self.parse_expr(0))
                    while self._match(TokenType.COMMA):
                        elems.append(self.parse_expr(0))
                self._expect(TokenType.RBRACKET, "']'")
                expr = ast.ArrayLit(elems, tok.line, tok.col)
            case TokenType.LBRACE:
                entries: list[tuple[ast.Expr, ast.Expr]] = []
                if not self._check(TokenType.RBRACE):
                    while True:
                        k = self.parse_expr(0)
                        self._expect(TokenType.COLON, "':' in map literal")
                        v = self.parse_expr(0)
                        entries.append((k, v))
                        if not self._match(TokenType.COMMA):
                            break
                self._expect(TokenType.RBRACE, "'}'")
                expr = ast.MapLit(entries, tok.line, tok.col)
            case TokenType.IDENT:
                if self._check(TokenType.LPAREN):
                    self._advance()
                    args: list[ast.Expr] = []
                    if not self._check(TokenType.RPAREN):
                        args.append(self.parse_expr(0))
                        while self._match(TokenType.COMMA):
                            args.append(self.parse_expr(0))
                    self._expect(TokenType.RPAREN, "')' after call arguments")
                    expr = ast.Call(tok.lexeme, args, tok.line, tok.col)
                else:
                    expr = ast.Ident(tok.lexeme, tok.line, tok.col)
            case _:
                raise ParseError(
                    f"expected expression, got {tok.type.name}", tok
                )

        while self._check(TokenType.LBRACKET):
            self._advance()
            idx = self.parse_expr(0)
            self._expect(TokenType.RBRACKET, "']'")
            expr = ast.Index(expr, idx, expr.line, expr.col)

        return expr

    # ---------- statements ----------

    def parse(self) -> ast.Program:
        stmts: list[ast.Stmt] = []
        while not self._check(TokenType.EOF):
            stmts.append(self.parse_statement())
        line, col = (stmts[0].line, stmts[0].col) if stmts else (1, 1)
        return ast.Program(stmts, line, col)

    def parse_statement(self) -> ast.Stmt:
        if self._check(TokenType.LET):      return self.parse_let()
        if self._check(TokenType.PRINT):    return self.parse_print()
        if self._check(TokenType.IF):       return self.parse_if()
        if self._check(TokenType.WHILE):    return self.parse_while()
        if self._check(TokenType.FOR):      return self.parse_for()
        if self._check(TokenType.FN):       return self.parse_fn()
        if self._check(TokenType.RETURN):   return self.parse_return()
        if self._check(TokenType.BREAK):    return self.parse_break()
        if self._check(TokenType.CONTINUE): return self.parse_continue()
        if self._check(TokenType.TRY):      return self.parse_try()
        if self._check(TokenType.THROW):    return self.parse_throw()
        if self._check(TokenType.LBRACE):   return self.parse_block()
        return self.parse_expr_stmt()

    def parse_block(self) -> ast.Block:
        tok = self._expect(TokenType.LBRACE, "'{'")
        stmts: list[ast.Stmt] = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            stmts.append(self.parse_statement())
        self._expect(TokenType.RBRACE, "'}'")
        return ast.Block(stmts, tok.line, tok.col)

    def parse_let(self) -> ast.LetStmt:
        tok = self._advance()
        name = self._expect(TokenType.IDENT, "identifier after 'let'")
        self._expect(TokenType.EQ, "'=' in let binding")
        value = self.parse_expr()
        self._expect(TokenType.SEMI, "';' after let binding")
        return ast.LetStmt(name.lexeme, value, tok.line, tok.col)

    def parse_print(self) -> ast.PrintStmt:
        tok = self._advance()
        self._expect(TokenType.LPAREN, "'(' after 'print'")
        value = self.parse_expr()
        self._expect(TokenType.RPAREN, "')' after print argument")
        self._expect(TokenType.SEMI, "';' after print")
        return ast.PrintStmt(value, tok.line, tok.col)

    def parse_return(self) -> ast.ReturnStmt:
        tok = self._advance()
        if self._match(TokenType.SEMI):
            return ast.ReturnStmt(None, tok.line, tok.col)
        value = self.parse_expr()
        self._expect(TokenType.SEMI, "';' after return")
        return ast.ReturnStmt(value, tok.line, tok.col)

    def parse_break(self) -> ast.BreakStmt:
        tok = self._advance()
        if self.loop_depth == 0:
            raise ParseError("'break' outside of a loop", tok)
        self._expect(TokenType.SEMI, "';' after break")
        return ast.BreakStmt(tok.line, tok.col)

    def parse_continue(self) -> ast.ContinueStmt:
        tok = self._advance()
        if self.loop_depth == 0:
            raise ParseError("'continue' outside of a loop", tok)
        self._expect(TokenType.SEMI, "';' after continue")
        return ast.ContinueStmt(tok.line, tok.col)

    def parse_throw(self) -> ast.ThrowStmt:
        tok = self._advance()
        value = self.parse_expr()
        self._expect(TokenType.SEMI, "';' after throw")
        return ast.ThrowStmt(value, tok.line, tok.col)

    def parse_try(self) -> ast.TryStmt:
        tok = self._advance()
        self._push_loop_saved = self.loop_depth
        try:
            body = self.parse_block()
        finally:
            self.loop_depth = self._push_loop_saved
        self._expect(TokenType.CATCH, "'catch' after try block")
        err_name = self._expect(TokenType.IDENT, "error variable name")
        handler = self.parse_block()
        return ast.TryStmt(body, err_name.lexeme, handler, tok.line, tok.col)

    def parse_if(self) -> ast.IfStmt:
        tok = self._advance()
        cond = self.parse_expr()
        then = self.parse_block()
        else_ = None
        if self._match(TokenType.ELSE):
            if self._check(TokenType.IF):
                nested = self.parse_if()
                else_ = ast.Block([nested], nested.line, nested.col)
            else:
                else_ = self.parse_block()
        return ast.IfStmt(cond, then, else_, tok.line, tok.col)

    def parse_while(self) -> ast.WhileStmt:
        tok = self._advance()
        cond = self.parse_expr()
        self.loop_depth += 1
        try:
            body = self.parse_block()
        finally:
            self.loop_depth -= 1
        return ast.WhileStmt(cond, body, tok.line, tok.col)

    def parse_for(self) -> ast.ForStmt:
        tok = self._advance()
        var = self._expect(TokenType.IDENT, "loop variable after 'for'")
        self._expect(TokenType.IN, "'in' after for variable")
        iter_expr = self.parse_expr()
        self.loop_depth += 1
        try:
            body = self.parse_block()
        finally:
            self.loop_depth -= 1
        return ast.ForStmt(var.lexeme, iter_expr, body, tok.line, tok.col)

    def parse_fn(self) -> ast.FnStmt:
        tok = self._advance()
        name = self._expect(TokenType.IDENT, "function name")
        self._expect(TokenType.LPAREN, "'(' after function name")
        params: list[str] = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENT, "parameter name").lexeme)
            while self._match(TokenType.COMMA):
                params.append(self._expect(TokenType.IDENT, "parameter name").lexeme)
        self._expect(TokenType.RPAREN, "')' after parameters")
        self._expect(TokenType.MINUS, "'->' in return type")
        self._expect(TokenType.GT, "'>' in return type")
        ret = self._expect(TokenType.IDENT, "return type name")

        saved_depth = self.loop_depth
        self.loop_depth = 0
        try:
            body = self.parse_block()
        finally:
            self.loop_depth = saved_depth

        return ast.FnStmt(name.lexeme, params, ret.lexeme, body, tok.line, tok.col)

    def parse_expr_stmt(self) -> ast.Stmt:
        if self._check(TokenType.IDENT) and self._peek_ahead(1).type is TokenType.EQ:
            name_tok = self._advance()
            self._advance()
            value = self.parse_expr()
            self._expect(TokenType.SEMI, "';' after assignment")
            assign = ast.Assign(name_tok.lexeme, value, name_tok.line, name_tok.col)
            return ast.ExprStmt(assign, name_tok.line, name_tok.col)

        expr = self.parse_expr()

        if isinstance(expr, ast.Index) and self._check(TokenType.EQ):
            if not isinstance(expr.array, ast.Ident):
                raise ParseError(
                    "cannot assign to non-variable array expression",
                    self._peek(),
                )
            self._advance()
            value = self.parse_expr()
            self._expect(TokenType.SEMI, "';' after index assignment")
            return ast.IndexSet(
                expr.array.name, expr.index, value, expr.line, expr.col
            )

        self._expect(TokenType.SEMI, "';' after expression")
        return ast.ExprStmt(expr, expr.line, expr.col)