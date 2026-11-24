"""RL-03 source-only schema evidence, NOT an adoption or migration tool.

Read only allowlisted Python blobs from verified local Git ancestry. Never import
historical code or inspect database/release/runtime blobs. Execute extracted literal
DDL in memory only; fresh schemas are reconstructions, not historical installations.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "33c16979d2ae17a5d53c118c7f173f324e02e75b"
SOURCES = ("app/db/schema.py", "app/legacy_main.py", "app/main.py")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8-sig")


def schema_statements(source: str) -> list[tuple[str, ...]]:
    """Extract the existing literal schema idiom; no eval/exec or helper execution."""
    tree = ast.parse(source)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    initializer = functions.get("_init_legacy", functions.get("init_db"))
    if initializer is None or "ensure_indexes" not in functions:
        raise ValueError("Source does not contain the expected schema definitions")
    statements = []
    for node in sorted(ast.walk(initializer), key=lambda n: getattr(n, "lineno", 0)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "execute" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if re.match(r"\s*CREATE TABLE IF NOT EXISTS\s", arg.value, re.I):
                    statements.append(("create", arg.value))
        elif isinstance(node.func, ast.Name) and node.func.id == "add_column_if_missing":
            if len(node.args) != 3 or not all(isinstance(a, ast.Constant) for a in node.args[1:]):
                raise ValueError("Nonliteral column definition")
            table, definition = (a.value for a in node.args[1:])
            if not isinstance(table, str) or not re.fullmatch(r"[a-z_]+", table):
                raise ValueError("Unexpected table identifier")
            if not isinstance(definition, str) or not re.match(r"[a-z_]+\s", definition):
                raise ValueError("Unexpected column definition")
            statements.append(("column", table, definition))
    indexes = functions["ensure_indexes"]
    lists = [
        n.value
        for n in ast.walk(indexes)
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "indexes" for t in n.targets)
    ]
    if len(lists) != 1 or not isinstance(lists[0], ast.List):
        raise ValueError("Unexpected index definitions")
    for node in lists[0].elts:
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            raise ValueError("Nonliteral index definition")
        if not re.match(r"CREATE (UNIQUE )?INDEX IF NOT EXISTS\s", node.value, re.I):
            raise ValueError("Unexpected index SQL")
        statements.append(("create", node.value))
    if not statements:
        raise ValueError("No schema DDL extracted")
    return statements


def derive(*sources: str) -> dict:
    with closing(sqlite3.connect(":memory:")) as conn:
        for source in sources:
            for statement in schema_statements(source):
                if statement[0] == "create":
                    conn.execute(statement[1])
                else:
                    _, table, definition = statement
                    if definition.split()[0] not in {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
        rows = [list(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
        canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        tables = {}
        for typ, name, _, _ in rows:
            if typ == "table":
                tables[name] = {
                    "columns": [list(r) for r in conn.execute(f'PRAGMA table_info("{name}")')],
                    "foreign_keys": [list(r) for r in conn.execute(f'PRAGMA foreign_key_list("{name}")')],
                }
        return {"schema_sha256": hashlib.sha256(canonical).hexdigest(), "objects": rows, "tables": tables}


def inventory(base: str = BASE) -> dict:
    if base != BASE or git("rev-parse", base).strip() != BASE:
        raise ValueError("RL-03 evidence requires its exact reviewed baseline")
    if git("rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("Incomplete Git ancestry")
    states = {}
    blobs = {}
    for commit in git("rev-list", "--reverse", base).splitlines():
        paths = set(git("ls-tree", "-r", "--name-only", commit, "--", *SOURCES).splitlines())
        for path in SOURCES:
            if path not in paths:
                continue
            source = git("show", f"{commit}:{path}")
            tree = ast.parse(source)
            if any(isinstance(n, ast.FunctionDef) and n.name in {"init_db", "_init_legacy"} for n in tree.body):
                if path != "app/db/schema.py" and not any(
                    isinstance(n, ast.FunctionDef) and n.name == "ensure_indexes" for n in tree.body
                ):
                    continue
                break
        else:
            raise ValueError("No literal schema source at a reachable commit")
        blob = git("rev-parse", f"{commit}:{path}").strip()
        if blob not in blobs:
            blobs[blob] = derive(source)
        metadata = blobs[blob]
        fingerprint = metadata["schema_sha256"]
        if fingerprint not in states:
            states[fingerprint] = {
                "first_source_commit": commit,
                "source_path": path,
                "source_blob": blob,
                "source_text_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "derivation": "literal DDL only, fresh in-memory SQLite; no historical application execution",
                "historical_database_authenticated": False,
                "adoption_support_added": False,
                "reachable_commit_count": 0,
                **metadata,
            }
        states[fingerprint]["reachable_commit_count"] += 1
    sequence = [
        ("c5ce7367d8dba5a2162397b9cfb9cc5b81de7f27", "app/main.py"),
        ("c101aede7ca2bc77a094107b9d1ea205ae4bddfb", "app/main.py"),
        ("849228102574dc61c02748bee50b59cf3039cc32", "app/main.py"),
        ("c3a78cd334b47e9f45dec6c10fe26be2a26df8bb", "app/db/schema.py"),
    ]
    return {
        "format": "drink-pos-rl03-source-schema-inventory",
        "format_version": 1,
        "base_commit": base,
        "sqlite_version": sqlite3.sqlite_version,
        "scope": "all commits reachable from baseline; fresh source-defined schemas only, NOT upgrade-path schemas",
        "authenticated_historical_database_artifacts": [],
        "verified_historical_release_images": [],
        "schemas": list(states.values()),
        "illustrative_ddl_sequence": {
            "scope": "synthetic DDL-only sequence, NOT authenticated installation or full data migration",
            "sources": [{"commit": commit, "path": path} for commit, path in sequence],
            **derive(*(git("show", f"{commit}:{path}") for commit, path in sequence)),
        },
    }


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(inventory(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
