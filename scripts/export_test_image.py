"""Save the already tested local AMD64 image; no build, pull or publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout.strip()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def archived_configuration(archive: Path) -> tuple[bytes, dict]:
    with tarfile.open(archive, "r") as bundle:
        manifest = json.load(bundle.extractfile("manifest.json"))
        if len(manifest) != 1:
            raise ValueError("Exactly one runnable image required")
        entry = bundle.getmember(manifest[0]["Config"])
        if not entry.isfile() or entry.size > 1_000_000:
            raise ValueError("Invalid bounded image configuration")
        data = bundle.extractfile(entry).read()
        return data, json.loads(data)


def bind_tested_configuration(archive: Path, tested: dict) -> str:
    """Bind saved config bytes to actual tested runtime config and rootfs diff IDs.

    .Id is deliberately NOT called config digest: containerd stores expose an
    index/manifest there, classic stores the config hash. Never conflate them.
    """
    data, config = archived_configuration(archive)
    if (
        config["config"] != tested["Config"]
        or config.get("rootfs", {}).get("diff_ids", []) != tested["RootFS"]["Layers"]
        or config["os"] != tested["Os"]
        or config["architecture"] != tested["Architecture"]
    ):
        raise ValueError("Saved configuration/rootfs differs from tested image")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def verify_archive(archive: Path, receipt: dict) -> None:
    """No extraction; archive bytes, config identity, platform and exact tag agree."""
    if digest(archive) != receipt["archive_sha256"]:
        raise ValueError("Archive checksum mismatch")
    with tarfile.open(archive, "r") as bundle:
        manifest = json.load(bundle.extractfile("manifest.json"))
        if len(manifest) != 1 or manifest[0]["RepoTags"] != [receipt["image_tag"]]:
            raise ValueError("Unexpected archive images/tags")
        config_file = bundle.getmember(manifest[0]["Config"])
        if not config_file.isfile() or config_file.size > 1_000_000:
            raise ValueError("Invalid image configuration")
        data = bundle.extractfile(config_file).read()
        if "sha256:" + hashlib.sha256(data).hexdigest() != receipt["image_config_id"]:
            raise ValueError("Image config ID mismatch")
        config = json.loads(data)
        if config["architecture"] != "amd64" or config["os"] != "linux":
            raise ValueError("Unsupported platform")
        env = dict(value.split("=", 1) for value in config["config"]["Env"])
        if env["APP_BUILD_COMMIT"] != receipt["source_sha"]:
            raise ValueError("Archive build source mismatch")


def export(image: str, commit: str, destination: Path, *, run_url: str, run_attempt: str) -> dict:
    if (
        not re.fullmatch(r"[0-9a-f]{40}", commit)
        or not re.fullmatch(r"https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+", run_url)
        or not run_attempt.isdigit()
    ):
        raise ValueError("Exact source and CI execution required")
    if docker("inspect", "--type=image", "--format", "{{.Os}}/{{.Architecture}}", image) != "linux/amd64":
        raise ValueError("AMD64 image required")
    identity = json.loads(
        docker(
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--entrypoint",
            "python",
            image,
            "-B",
            "/app/synology_test.py",
            "identity",
        )
    )
    if identity["git_commit"] != commit:
        raise ValueError("Executing image source does not match tested checkout")
    runtime = json.loads(
        docker(
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--entrypoint",
            "python",
            image,
            "-B",
            "-c",
            "import os,sys,sqlite3,json; print(json.dumps({'python':sys.version,'sqlite':sqlite3.sqlite_version,"
            "'build':{k:v for k,v in os.environ.items() if k.startswith('APP_BUILD_')}}))",
        )
    )
    destination.mkdir(mode=0o700)  # Never overwrite an earlier receipt/artifact.
    tag = "drink-pos-test:" + commit
    docker("tag", image, tag)
    archive = destination / "drink-pos-test-amd64.tar"
    docker("save", "--output", str(archive), tag)
    tested = json.loads(docker("image", "inspect", tag))[0]
    config_id = bind_tested_configuration(archive, tested)
    receipt = {
        "format": "drink-pos-test-image",
        "format_version": 1,
        "source_sha": commit,
        "image_tag": tag,
        "image_config_id": config_id,
        "ci_docker_image_id": tested["Id"],
        "ci_docker_descriptor": tested.get("Descriptor"),
        "archive": archive.name,
        "archive_sha256": digest(archive),
        "platform": "linux/amd64",
        "oci_registry_digest": None,
        "reproducible_build": "not-proven",
        "release": identity,
        "runtime": runtime,
        "ci": {
            "run_url": run_url,
            "run_attempt": int(run_attempt),
            "checkout_sha": commit,
            "publication": "none",
            "gates": [
                "python-3.12-3.13-standard-checks",
                "container-smoke",
                "upgrade",
                "migration",
                "financial-round-recovery",
                "encrypted-source-loss",
                "actual-test-compose",
                "image-dependency-audit",
            ],
        },
    }
    verify_archive(archive, receipt)
    docker("load", "--input", str(archive))
    loaded = json.loads(docker("image", "inspect", tag))[0]
    if loaded["Id"] != receipt["ci_docker_image_id"] or bind_tested_configuration(archive, loaded) != config_id:
        raise ValueError("Imported archive image differs from tested image")
    (destination / "artifact.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (destination / "release.json").write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name in ("compose.synology.test.yaml", ".env.test.example"):
        shutil.copyfile(ROOT / name, destination / name)
    for name in (
        "synology-test-deployment.md",
        "release-safety.md",
        "migration-safety.md",
        "application-recovery.md",
        "disaster-recovery.md",
        "recovery.md",
        "round-cancellation-contract.md",
        "rl-06-contract.md",
    ):
        shutil.copyfile(ROOT / "docs" / name, destination / name)
    (destination / "SHA256SUMS").write_text(
        "".join(digest(file) + "  " + file.name + "\n" for file in sorted(destination.iterdir()) if file.is_file()),
        encoding="ascii",
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--run-attempt", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            export(args.image, args.commit, args.destination, run_url=args.run_url, run_attempt=args.run_attempt)
        )
    )


if __name__ == "__main__":
    main()
