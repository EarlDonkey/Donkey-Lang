from donky.repl import _brace_delta


def test_brace_delta_balanced():
    assert _brace_delta("if x { }") == 0


def test_brace_delta_open():
    assert _brace_delta("if x {") == 1


def test_brace_delta_close():
    assert _brace_delta("}") == -1


def test_brace_delta_nested():
    assert _brace_delta("fn f() { if x { } }") == 0


def test_brace_delta_ignores_strings():
    assert _brace_delta('print("{ }")') == 0


def test_brace_delta_ignores_comments():
    assert _brace_delta("{ // } ") == 1


def test_brace_delta_escaped_quote():
    assert _brace_delta(r'print("\"{")') == 0