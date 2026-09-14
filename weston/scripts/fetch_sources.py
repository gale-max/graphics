"""获取并校验固定版本的 Weston 上游源码。"""

from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def read_manifest() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / "sources.yaml").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def run(*command: str, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE)
    return result.stdout.strip()


def main() -> None:
    manifest = read_manifest()
    expected_revision = manifest["revision"]
    source = ROOT / "upstream"

    with tempfile.TemporaryDirectory(prefix="weston-source-") as directory:
        checkout = Path(directory) / "checkout"
        run("git", "clone", "--depth", "1", "--branch", manifest["tag"],
            manifest["remote"], str(checkout))
        actual_revision = run("git", "rev-parse", "HEAD", cwd=checkout)
        if actual_revision != expected_revision:
            raise RuntimeError(
                f"Weston revision mismatch: {actual_revision} != {expected_revision}"
            )

        if source.exists():
            shutil.rmtree(source)
        shutil.copytree(checkout, source, ignore=shutil.ignore_patterns(".git"))

    git_metadata = source / ".git"
    if git_metadata.exists():
        shutil.rmtree(git_metadata)
    print(f"Weston {manifest['tag']} imported at {expected_revision}")


if __name__ == "__main__":
    main()
