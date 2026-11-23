"""Run the cross-platform, non-production Drink-POS quality gate."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_environment(directory: Path) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(
            ("DRINK_POS_", "SUMUP_", "SMTP_", "APP_BUILD_", "PAYMENT_PROVIDER", "UVICORN_", "WEB_CONCURRENCY")
        )
    }
    environment.update(
        {
            "DRINK_POS_ENV": "development",
            "DRINK_POS_DB": str(directory / "checks.db"),
            "DRINK_POS_MESSAGES": str(directory / "messages.json"),
            "DRINK_POS_BACKUP_DIR": str(directory / "backups"),
            "DRINK_POS_PIN": "1234",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
        }
    )
    return environment


def run(command: list[str], environment: dict[str, str]) -> None:
    print(f"Running: {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node")
    parser.add_argument("--handoff-root", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="drink-pos-checks-") as temporary:
        environment = test_environment(Path(temporary))
        run([sys.executable, "-m", "ruff", "check", "."], environment)
        run([sys.executable, "-m", "ruff", "format", "--check", "."], environment)
        run([sys.executable, "-m", "compileall", "-q", "app", "tests"], environment)
        run([sys.executable, "scripts/check_syntax.py", "--node", args.node], environment)
        traceability = [sys.executable, "scripts/check_traceability.py"]
        if args.handoff_root:
            traceability.extend(["--handoff-root", str(args.handoff_root.resolve())])
        run(traceability, environment)
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], environment)
        run([sys.executable, "-m", "pip_audit", "--strict", "--progress-spinner", "off"], environment)
        run([sys.executable, "scripts/browser_smoke.py"], environment)
        run(["git", "diff", "--check"], environment)
    print("Standard Checks passed. Container/manual evidence remain separate gates.", flush=True)


if __name__ == "__main__":
    main()
