"""Install pinned official age tooling outside the repo/image, verifying SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "v1.3.2"
ASSETS = {
    ("Linux", "x86_64"): ("linux-amd64.tar.gz", "cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10"),
    ("Windows", "AMD64"): ("windows-amd64.zip", "f48d8f8f9ebe903ab5027ed067652f2cc1db94bc206976430133b905dcd8e8c7"),
}


def install(destination: Path) -> Path:
    if destination.exists():
        raise FileExistsError("Tooling destination must be new; never overwrite tools")
    suffix, expected = ASSETS[(platform.system(), platform.machine())]
    url = f"https://github.com/FiloSottile/age/releases/download/{VERSION}/age-{VERSION}-{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="age-download-", dir=destination.parent) as name:
        archive = Path(name) / "download"
        with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError("Pinned age download checksum mismatch")
        # Extract ONLY the two named binaries, never archive paths or links.
        extension = ".exe" if platform.system() == "Windows" else ""
        destination.mkdir(mode=0o700)
        for binary in ("age", "age-keygen"):
            entry = "age/" + binary + extension
            if suffix.endswith("zip"):
                with zipfile.ZipFile(archive) as source:
                    data = source.read(entry)
            else:
                with tarfile.open(archive, "r:gz") as source:
                    member = source.getmember(entry)
                    if not member.isfile():
                        raise ValueError("Unexpected tooling archive entry")
                    with source.extractfile(member) as handle:
                        data = handle.read()
            path = destination / (binary + extension)
            path.write_bytes(data)
            if os.name == "posix":
                path.chmod(0o700)
    return destination.absolute()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--github-path", type=Path)
    args = parser.parse_args()
    path = install(args.destination)
    if args.github_path:
        with args.github_path.open("a", encoding="utf-8") as output:
            output.write(str(path) + "\n")
    print(f"Pinned age {VERSION} tooling checksum verified; installed outside application image")


if __name__ == "__main__":
    main()
