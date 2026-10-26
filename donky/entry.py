import sys

from donky.repl import repl
from donky.run import main as run_main


def main() -> None:
    if len(sys.argv) == 1:
        repl()
    else:
        run_main()


if __name__ == "__main__":
    main()