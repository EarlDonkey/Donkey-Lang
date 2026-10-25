from donky import ast_nodes as ast


def show(node, indent: int = 0) -> str:
    pad = "  " * indent
    match node:
        # ---------- expressions ----------
        case ast.NumberLit(v):
            return f"{pad}Number({v})"
        case ast.StringLit(v):
            return f"{pad}String({v!r})"
        case ast.BoolLit(v):
            return f"{pad}Bool({v})"
        case ast.Ident(n):
            return f"{pad}Ident({n})"
        case ast.Unary(o, e):
            return f"{pad}Unary({o})\n" + show(e, indent + 1)
        case ast.Binary(l, o, r):
            return (f"{pad}Binary({o})\n"
                    + show(l, indent + 1) + "\n"
                    + show(r, indent + 1))
        case ast.Assign(n, v):
            return f"{pad}Assign({n})\n" + show(v, indent + 1)
        case ast.Call(c, args):
            out = f"{pad}Call({c})"
            if args:
                out += "\n" + "\n".join(show(a, indent + 1) for a in args)
            return out

        # ---------- statements ----------
        case ast.Program(stmts):
            return "\n".join(show(s, indent) for s in stmts)
        case ast.Block(stmts):
            if not stmts:
                return f"{pad}Block()"
            return f"{pad}Block\n" + "\n".join(show(s, indent + 1) for s in stmts)
        case ast.LetStmt(n, v):
            return f"{pad}Let({n})\n" + show(v, indent + 1)
        case ast.PrintStmt(v):
            return f"{pad}Print\n" + show(v, indent + 1)
        case ast.ExprStmt(e):
            return f"{pad}ExprStmt\n" + show(e, indent + 1)
        case ast.IfStmt(c, t, e):
            out = f"{pad}If\n" + show(c, indent + 1) + "\n" + show(t, indent + 1)
            if e is not None:
                out += "\n" + show(e, indent + 1)
            return out
        case ast.WhileStmt(c, b):
            return f"{pad}While\n" + show(c, indent + 1) + "\n" + show(b, indent + 1)
        case ast.FnStmt(n, ps, rt, b):
            return (f"{pad}Fn({n}) -> {rt} params={ps}\n"
                    + show(b, indent + 1))
        case ast.ReturnStmt(v):
            if v is None:
                return f"{pad}Return"
            return f"{pad}Return\n" + show(v, indent + 1)
        case ast.ArrayLit(elems, _, _):
            if not elems:
                return f"{pad}ArrayLit([])"
            return (f"{pad}ArrayLit\n"
                    + "\n".join(show(e, indent + 1) for e in elems))
        case ast.Index(arr, idx, _, _):
            return (f"{pad}Index\n"
                    + show(arr, indent + 1) + "\n"
                    + show(idx, indent + 1))
        case ast.IndexSet(name, idx, val, _, _):
            return (f"{pad}IndexSet({name})\n"
                    + show(idx, indent + 1) + "\n"
                    + show(val, indent + 1))

        case _:
            return f"{pad}?? {node!r}"