"""从空目录构建 Luna Qt SDK 随附的全部示例。"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def discover_projects(examples: Path) -> list[Path]:
    """按稳定顺序返回 SDK 中交付的全部 qmake 工程。"""
    return sorted(examples.rglob("*.pro"))


def project_build_directory(sdk: Path, output: Path, project: Path) -> Path:
    """为示例生成与 SDK examples 层次一致的独立构建目录。"""
    return output / project.parent.relative_to(sdk / "examples")


def build_project(sdk: Path, output: Path, project: Path, jobs: int) -> None:
    """清理并构建一个 qmake 示例，失败时立即终止。"""
    build = project_build_directory(sdk, output, project)
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)
    subprocess.run(
        [str(sdk / "bin" / "qmake.exe"), str(project)],
        cwd=build,
        check=True,
    )
    subprocess.run(["mingw32-make", f"-j{jobs}"], cwd=build, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    sdk = args.sdk.resolve()
    output = (args.output or sdk / "example-build").resolve()
    projects = discover_projects(sdk / "examples")
    if not projects:
        raise FileNotFoundError(sdk / "examples")
    for project in projects:
        print(f"build: {project.relative_to(sdk)}", flush=True)
        build_project(sdk, output, project, args.jobs)
    print(f"all {len(projects)} SDK examples built successfully")


if __name__ == "__main__":
    main()
