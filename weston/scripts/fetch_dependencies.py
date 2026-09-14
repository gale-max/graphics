"""下载并校验 Weston desktop-shell 的固定版本依赖源码。"""

from argparse import ArgumentParser
from pathlib import Path
import os
import shutil
import stat
import subprocess

import yaml


def run(*command: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def remove_tree(path: Path) -> None:
    def make_writable_and_retry(function, name, _error) -> None:
        os.chmod(name, stat.S_IWRITE)
        function(name)

    if path.exists():
        shutil.rmtree(path, onexc=make_writable_and_retry)


def fetch(name: str, spec: dict[str, str], output: Path) -> None:
    destination = output / name
    temporary = output / f".{name}.fetch"
    remove_tree(temporary)
    run(
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        spec["tag"],
        spec["remote"],
        str(temporary),
    )
    revision = run("git", "rev-parse", "HEAD", cwd=temporary)
    if revision != spec["revision"]:
        raise RuntimeError(
            f"{name}: expected {spec['revision']}, fetched {revision}"
        )
    remove_tree(temporary / ".git")
    remove_tree(destination)
    temporary.replace(destination)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dependencies.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dependencies",
    )
    args = parser.parse_args()
    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, spec in manifest["dependencies"].items():
        fetch(name, spec, args.output)


if __name__ == "__main__":
    main()
