"""Offline release identity. No application, configuration or startup imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

FORMAT = "drink-pos-release"
PYTHON_BASELINE = ["3.12", "3.13"]
MIGRATION_INPUTS = (
    "db/schema.py",
    "db/migrations.py",
    "db/connection.py",
    "config.py",
    "utils/helpers.py",
    "utils/parsing.py",
    "utils/formatting.py",
    "services/messages.py",
)


def release_identity(commit: str, channel: str, version: str | None, *, image_ref: str | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Exact Git commit required")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", channel):
        raise ValueError("Explicit release channel required")
    if version is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,79}", version):
        raise ValueError("Invalid release version")
    if image_ref is not None and not re.fullmatch(r"[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}", image_ref):
        raise ValueError("Only actually verified digest-pinned image references are supported")
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in MIGRATION_INPUTS:
        # Normalize checkout line endings, not code semantics; includes filenames.
        digest.update(name.encode() + b"\0" + (root / name).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return {
        "format": FORMAT,
        "format_version": 1,
        "git_commit": commit,
        "version": version,
        "channel": channel,
        "image_ref": image_ref,
        "migration_code_sha256": digest.hexdigest(),
        "python": list(PYTHON_BASELINE),
        "application_bundle_version": 1,
        "schema_version": None,  # Dual legacy/versioned runtime: DB evidence is separate.
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--version")
    parser.add_argument("--image-ref")
    args = parser.parse_args(argv)
    try:
        print(
            json.dumps(
                release_identity(args.commit, args.channel, args.version, image_ref=args.image_ref), sort_keys=True
            )
        )
        return 0
    except (OSError, ValueError):
        print(json.dumps({"status": "identity-unavailable"}))
        return 4


if __name__ == "__main__":
    sys.exit(main())
