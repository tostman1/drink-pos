"""Parse application Python/JavaScript without executing it."""

from __future__ import annotations

import argparse
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_TYPES = {"", "module", "text/javascript", "application/javascript", "text/ecmascript", "application/ecmascript"}
JSON_TYPES = {"application/json", "application/ld+json", "importmap", "speculationrules"}


class HTMLSources(HTMLParser):
    """Collect executable scripts/handlers and separate JSON data."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[tuple[int, str, str]] = []
        self.handlers: list[tuple[int, str]] = []
        self.current: tuple[int, str, bool] | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        line = self.getpos()[0]
        for name, value in attrs:
            if name.startswith("on") and value:
                self.handlers.append((line, f"function handler(event) {{\n{value}\n}}"))
        if tag == "script":
            self.current = (line, (attributes.get("type") or "").lower().strip(), "src" in attributes)
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.current:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.current:
            line, kind, external = self.current
            if not external:
                self.scripts.append((line, kind, "".join(self.parts)))
            self.current = None
            self.parts = []


def check_python(paths: list[Path]) -> None:
    for path in paths:
        compile(path.read_bytes(), str(path), "exec")


def check_js(node: str, source: str, module: bool, label: str) -> None:
    command = [node, "--check", f"--input-type={'module' if module else 'commonjs'}"]
    result = subprocess.run(command, input=source, text=True, encoding="utf-8", capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f"JavaScript syntax failed: {label}\n{result.stderr}")


def check_app(root: Path, node: str) -> None:
    python_paths = sorted(
        path for directory in ("app", "tests", "scripts") for path in (root / directory).rglob("*.py")
    )
    check_python(python_paths)
    count = 0
    for path in sorted((root / "app").rglob("*.js")):
        module = "static" in path.relative_to(root / "app").parts
        check_js(node, path.read_text(encoding="utf-8"), module, str(path))
        count += 1
    for path in sorted((root / "app").rglob("*.html")):
        parser = HTMLSources()
        parser.feed(path.read_text(encoding="utf-8"))
        for line, kind, source in parser.scripts:
            label = f"{path}:{line}"
            if kind in JS_TYPES:
                check_js(node, source, kind == "module", label)
                count += 1
            elif kind in JSON_TYPES:
                json.loads(source)
            else:
                raise ValueError(f"Unclassified script type {kind!r} at {label}; review instead of silently skipping")
        for line, source in parser.handlers:
            check_js(node, source, False, f"{path}:{line} inline handler")
            count += 1
    for path in sorted((root / "app").rglob("*")):
        if path.suffix in {".json", ".webmanifest"}:
            json.loads(path.read_text(encoding="utf-8"))
    print(f"Syntax/data passed: {len(python_paths)} Python files; {count} JavaScript sources/handlers", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--node", default="node")
    args = parser.parse_args()
    check_app(args.root.resolve(), args.node)


if __name__ == "__main__":
    main()
