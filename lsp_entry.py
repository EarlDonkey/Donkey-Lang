import sys
import os
from donky.repl import repl
from editor.lsp.donky_lsp import server

if __name__ == "__main__":
    # Start the language server on stdio
    server.start_io()