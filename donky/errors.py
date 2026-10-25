class DonkyRuntimeError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        if line > 0:
            super().__init__(f"[{line}:{col}] runtime error: {message}")
        else:
            super().__init__(f"runtime error: {message}")
        self.line = line
        self.col = col