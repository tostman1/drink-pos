"""Resolve requirement evidence, distinguishing integrated and pending tests."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = {"observed-main", "pending-pr1", "handoff-integrated", "engineering"}


def local_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or non-local source path: {value}")
    return path


def validate_test(root: Path, reference: str) -> None:
    filename, separator, name = reference.partition("::")
    class_name, dot, method_name = name.partition(".")
    if not separator or not dot or not method_name.startswith("test_"):
        raise ValueError(f"Expected file::TestClass.test_method: {reference}")
    tree = ast.parse(local_path(root, filename).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            if any(isinstance(method, ast.FunctionDef) and method.name == method_name for method in node.body):
                return
    raise ValueError(f"Missing test method: {reference}")


def validate_catalog(root: Path = ROOT, handoff_root: Path | None = None) -> tuple[int, int]:
    catalog = json.loads((root / "docs/requirements.json").read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1:
        raise ValueError("Unsupported requirements schema")
    for key in ("baseline", "handoff"):
        if not re.fullmatch(r"[0-9a-f]{40}", catalog.get(key, "")):
            raise ValueError(f"Invalid {key} commit")
    manual_text = (root / "docs/standard-checks.md").read_text(encoding="utf-8")
    manual_ids = set(re.findall(r"^### (MV-\d{2}) —", manual_text, re.MULTILINE))
    ids: set[str] = set()
    external_count = 0
    for requirement in catalog["requirements"]:
        identity = requirement["id"]
        if not re.fullmatch(r"DP-\d{3}", identity) or identity in ids:
            raise ValueError(f"Invalid/duplicate requirement ID: {identity}")
        ids.add(identity)
        if requirement["scope"] not in SCOPES or len(requirement["statement"].strip()) < 20:
            raise ValueError(f"Missing scope/observable statement: {identity}")
        if not requirement["sources"]:
            raise ValueError(f"Missing sources: {identity}")
        for source in requirement["sources"]:
            local_path(root, source)
        for reference in requirement["tests"]:
            validate_test(root, reference)
        external = requirement.get("handoff_tests", [])
        if external and requirement["scope"] != "pending-pr1":
            raise ValueError(f"External tests must be explicitly pending-pr1: {identity}")
        for reference in external:
            if not re.fullmatch(r"tests/[\w/]+\.py::\w+\.test_\w+", reference):
                raise ValueError(f"Invalid external test reference: {reference}")
            if handoff_root:
                validate_test(handoff_root, reference)
            external_count += 1
        if set(requirement["manual"]) - manual_ids:
            raise ValueError(f"Unknown manual check: {identity}")
        if not (requirement["tests"] or requirement["manual"] or external):
            raise ValueError(f"No verification method: {identity}")
    return len(ids), external_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff-root", type=Path)
    args = parser.parse_args()
    count, external = validate_catalog(handoff_root=args.handoff_root)
    state = (
        "resolved" if args.handoff_root else "external only when explicitly pending; integrated tests resolve locally"
    )
    print(f"Traceability passed: {count} requirements; {external} external test references ({state})", flush=True)


if __name__ == "__main__":
    main()
