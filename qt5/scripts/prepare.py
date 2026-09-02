"""下载并展开固定版本的 Qt 5 qtbase 源码。"""

from __future__ import annotations

import hashlib
import shutil
import tarfile
import urllib.request
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
ARCHIVE = ROOT / "upstream" / Path(MANIFEST["source"]).name
SOURCE_DIR = ROOT / "upstream" / f"qtbase-everywhere-src-{MANIFEST['revision']}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.exists():
        with urllib.request.urlopen(MANIFEST["source"]) as response:
            with ARCHIVE.open("wb") as output:
                shutil.copyfileobj(response, output)

    actual = sha256(ARCHIVE)
    if actual != MANIFEST["sha256"]:
        raise SystemExit(f"Qt source checksum mismatch: {actual}")

    if not SOURCE_DIR.exists():
        with tarfile.open(ARCHIVE, "r:xz") as archive:
            archive.extractall(ROOT / "upstream", filter="data")

    print(f"Qt {MANIFEST['revision']} qtbase source ready: {SOURCE_DIR}")


if __name__ == "__main__":
    main()
