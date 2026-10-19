"""使用原生 Windows 工具链生成 Qt 5.15.19 SDK 主机工具。"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
from pathlib import Path

from sdk_paths import SdkPaths

ROOT = Path(__file__).resolve().parents[1]
PATHS = SdkPaths(ROOT / "build")
DEFAULT_STAGE = Path(os.environ.get("QT_WINDOWS_STAGE", "D:/q5w"))
REQUIRED_TOOLS = (
    "qmake.exe", "moc.exe", "uic.exe", "rcc.exe",
    "qmlcachegen.exe", "qmlimportscanner.exe", "lrelease.exe", "lupdate.exe",
)
MODULES = {
    "qtbase": "qtbase-everywhere-src-5.15.19",
    "qtdeclarative": "qtdeclarative-everywhere-src-5.15.19",
    "qttools": "qttools-everywhere-src-5.15.19",
}


def windows_path(path: Path) -> str:
    """返回 Windows 可访问的绝对路径。"""
    raw = path.as_posix()
    if raw.startswith("/home/"):
        raise ValueError(f"path is not Windows-visible: {path}")
    if os.name == "nt":
        return str(path.resolve())
    if not raw.startswith("/mnt/"):
        raise ValueError(f"path is not Windows-visible: {path}")
    return subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()


def windows_source_path(path: Path, distro: str) -> str:
    """把 WSL 路径转换成 Windows UNC 路径。"""
    if not path.as_posix().startswith("/"):
        return windows_path(path)
    return "\\\\wsl.localhost\\" + distro + path.as_posix().replace("/", "\\")


def validate_windows_stage(path: Path, maximum_length: int = 80) -> Path:
    """限制暂存路径长度，避免 Qt 私有头文件超过 MAX_PATH。"""
    resolved = Path(windows_path(path))
    if len(str(resolved)) > maximum_length:
        raise ValueError(
            f"Windows build stage must be shorter than {maximum_length} characters: {resolved}"
        )
    return resolved


def native_tar_extract_command(
    archive: Path, destination: Path, distro: str = "ubuntu20.04"
) -> list[str]:
    """生成 Windows tar 解包命令。"""
    archive_win = (windows_source_path(archive, distro)
                   if archive.as_posix().startswith("/home/")
                   else windows_path(archive))
    return ["tar.exe", "-xf", archive_win, "-C", windows_path(destination)]


def windows_environment(winlibs: Path, perl: Path, inherited: str) -> str:
    """生成原生构建 PATH。"""
    return ";".join((windows_path(winlibs), windows_path(perl), inherited))


def normalized_jobs(jobs: int) -> int:
    """将构建并行度限制为最多四个作业。"""
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    return min(jobs, 4)


def native_module_build_command(
    qmake: Path, project: Path, build: Path, environment_path: str,
    jobs: int = 1, qmake_arguments: tuple[str, ...] = (),
) -> list[str]:
    """生成 Qt 子模块配置、编译和安装命令。"""
    arguments = " ".join(qmake_arguments)
    command = (
        f'set "PATH={environment_path}" && cd /d "{windows_path(build)}" && '
        f'"{windows_path(qmake)}" "{windows_path(project)}" {arguments} && '
        f'mingw32-make.exe -j{normalized_jobs(jobs)} && '
        f'mingw32-make.exe -j{normalized_jobs(jobs)} install'
    )
    return ["cmd.exe", "/d", "/s", "/c", command]


def native_windows_configure_command(
    source: Path, build: Path, prefix: Path, winlibs: Path,
    distro: str = "ubuntu20.04",
) -> list[str]:
    """生成 QtBase 原生 Windows 配置命令。"""
    source_win = windows_path(source) if os.name == "nt" else windows_source_path(source, distro)
    command = (
        f'set "PATH={windows_path(winlibs)};%PATH%" && '
        f'cd /d "{windows_path(build)}" && "{source_win}\\configure.bat" '
        "-platform win32-g++ -opensource -confirm-license -release -static "
        "-no-opengl -no-dbus -no-icu -no-openssl -nomake examples -nomake tests "
        f'-prefix "{windows_path(prefix)}"'
    )
    return ["cmd.exe", "/d", "/s", "/c", command]


def linguist_build_commands(build: Path, jobs: int) -> tuple[list[str], list[str]]:
    """生成仅构建和安装 Linguist 子树的命令。"""
    count = f"-j{normalized_jobs(jobs)}"
    return (
        ["mingw32-make.exe", "-C", str(build / "src"), count,
         "sub-linguist-make_first"],
        ["mingw32-make.exe", "-C", str(build / "src" / "linguist"), count,
         "install"],
    )


def verify_pe(path: Path) -> None:
    """验证 DOS 头和 PE 签名。"""
    data = path.read_bytes()
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError(f"not a Windows PE executable: {path}")
    offset = struct.unpack_from("<I", data, 0x3C)[0]
    if offset + 4 > len(data) or data[offset:offset + 4] != b"PE\0\0":
        raise ValueError(f"invalid Windows PE signature: {path}")


def run(command: list[str], cwd: Path, environment: dict[str, str]) -> None:
    """执行并显示构建命令。"""
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def require_directory(path: Path, description: str) -> Path:
    """校验外部工具目录。"""
    if not path.is_dir():
        raise SystemExit(f"missing {description}: {path}")
    return path


def locate_source(stage: Path, name: str) -> Path:
    """查找暂存源码，缺失时从 upstream 归档原生解包。"""
    destination = stage / "src"
    source = destination / MODULES[name]
    if source.is_dir():
        return source
    destination.mkdir(parents=True, exist_ok=True)
    archives = [item for item in sorted(
        (ROOT / "upstream").glob(f"{name}-everywhere-*-5.15.19.tar.xz")
    ) if ".bad-" not in item.name]
    if not archives:
        raise SystemExit(f"missing source archive for {name}")
    subprocess.run(native_tar_extract_command(archives[0], destination), check=True)
    if not source.is_dir():
        raise SystemExit(f"archive did not create expected directory: {source}")
    return source


def build(jobs: int, stage: Path, winlibs: Path, perl: Path) -> None:
    """生成并核验 Windows Qt 主机工具。"""
    if os.name != "nt":
        raise SystemExit("run this script with native Windows Python")
    jobs = normalized_jobs(jobs)
    stage = validate_windows_stage(stage)
    winlibs = require_directory(winlibs, "WinLibs bin directory")
    perl = require_directory(perl, "Perl bin directory")
    environment = os.environ.copy()
    environment["PATH"] = windows_environment(winlibs, perl, environment["PATH"])
    make = str(winlibs / "mingw32-make.exe")
    prefix = stage / "install"
    build_root = stage / "build"
    sources = {name: locate_source(stage, name) for name in MODULES}

    base_build = build_root / "qtbase"
    base_build.mkdir(parents=True, exist_ok=True)
    if not (base_build / "Makefile").is_file():
        run(native_windows_configure_command(
            sources["qtbase"], base_build, prefix, winlibs
        ), base_build, environment)
    run([make, f"-j{jobs}"], base_build, environment)
    run([make, f"-j{jobs}", "install"], base_build, environment)

    declarative_build = build_root / "qtdecl-nod3d"
    declarative_build.mkdir(parents=True, exist_ok=True)
    if not (declarative_build / "Makefile").is_file():
        run([str(prefix / "bin" / "qmake.exe"),
             str(sources["qtdeclarative"] / "qtdeclarative.pro"),
             "--", "-no-d3d12"], declarative_build, environment)
    run([make, f"-j{jobs}"], declarative_build, environment)
    run([make, f"-j{jobs}", "install"], declarative_build, environment)

    tools_build = build_root / "qttools"
    tools_build.mkdir(parents=True, exist_ok=True)
    if not (tools_build / "Makefile").is_file():
        run([str(prefix / "bin" / "qmake.exe"),
             str(sources["qttools"] / "qttools.pro")], tools_build, environment)
    for command in linguist_build_commands(tools_build, jobs):
        run(command, tools_build, environment)

    destination = PATHS.host_windows / "sdk-bin"
    destination.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_TOOLS:
        tool = prefix / "bin" / name
        verify_pe(tool)
        shutil.copy2(tool, destination / name)
    shutil.copytree(
        prefix / "mkspecs", PATHS.host_windows / "mkspecs", dirs_exist_ok=True
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--winlibs-bin", type=Path,
                        default=Path(os.environ.get("WINLIBS_BIN", "C:/winlibs/mingw64/bin")))
    parser.add_argument("--perl-bin", type=Path,
                        default=Path(os.environ.get("PERL_BIN", "C:/Program Files/Git/usr/bin")))
    args = parser.parse_args()
    build(args.jobs, args.stage, args.winlibs_bin, args.perl_bin)


if __name__ == "__main__":
    main()
