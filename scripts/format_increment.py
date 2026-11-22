"""Apply Ruff formatting to explicit files, refusing any Python AST change."""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    before = {path: ast.dump(ast.parse(path.read_bytes()), include_attributes=False) for path in args.files}
    subprocess.run([sys.executable, "-m", "ruff", "format", *map(str, args.files)], check=True)
    for path, syntax in before.items():
        if ast.dump(ast.parse(path.read_bytes()), include_attributes=False) != syntax:
            raise RuntimeError(f"Formatting changed Python AST: {path}")
    print(f"AST-equivalent formatting verified for {len(before)} explicitly selected files.")


if __name__ == "__main__":
    main()
