"""把 Windows Qt 主机工具与 Luna ARMv8A 目标安装树组合成 Qt Creator SDK。"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
ROOT = SCRIPT_DIRECTORY.parent
if ROOT.name == "sdk-recovery":
    ROOT = ROOT.parent
REQUIRED_HOST_TOOLS = (
    "qmake.exe", "moc.exe", "uic.exe", "rcc.exe",
    "qmlcachegen.exe", "qmlimportscanner.exe", "lrelease.exe", "lupdate.exe",
)
TARGET_DIRECTORIES = (
    "include", "lib", "plugins", "qml", "imports", "translations", "mkspecs",
    "staging", "src",
)
DELIVERY_SCRIPTS = (
    "build_windows_host_tools.py",
    "sdk_paths.py",
    "build_sdk_examples.py",
    "package_windows_sdk.py",
    "persist_qtcreator_kit.py",
    "register_qtcreator_kit.ps1",
)
DELIVERY_EXAMPLE_TREES = (
    (
        "upstream/qtbase-everywhere-src-5.15.19/examples",
        "qtbase",
    ),
    (
        "upstream/qtdeclarative-everywhere-src-5.15.19/examples",
        "qtdeclarative",
    ),
    (
        "upstream/qtwayland-everywhere-src-5.15.19/examples",
        "qtwayland",
    ),
)
DELIVERY_CUSTOM_EXAMPLES = (
    ("examples/eglfs-smoke", "luna/eglfs-smoke"),
    ("examples/widgets-display", "luna/widgets-display"),
)
REQUIRED_PUBLIC_HEADERS = (
    "QtCore/QObject",
    "QtGui/QPainter",
    "QtWidgets/QApplication",
    "QtWidgets/QWidget",
)
REQUIRED_TARGET_LIBRARIES = (
    "libQt5Core.so",
    "libQt5Gui.so",
    "libQt5Widgets.so",
    "libQt5Network.so",
    "libQt5Qml.so",
    "libQt5Quick.so",
    "libQt5WaylandClient.so",
    "libQt5WaylandCompositor.so",
)


def find_workspace_root(path: Path) -> Path:
    """根据工具链目录定位 luna-workspace，兼容普通目录和 worktree。"""
    for candidate in (path, *path.parents):
        if (candidate / "tools" / "toolchains").is_dir():
            return candidate
    raise FileNotFoundError(f"cannot locate luna-workspace from {path}")


def require_host_mkspecs(path: Path) -> Path:
    """确认主机 mkspec 包含 qmake 的通用 feature 文件。"""
    required = path / "features" / "spec_pre.prf"
    if not required.is_file():
        raise FileNotFoundError(required)
    return path


def relocate_metadata(
    text: str,
    sdk: Path,
    workspace: Path,
    target: Path | None = None,
) -> str:
    """把目标 Qt 元数据中的 WSL 构建路径迁移到 Windows SDK。"""
    replacements = [
        ("/home/surest/nanopc-workspace/graphics/qt5/build/target-armv8a-luna",
         as_qmake_path(sdk)),
        ("/home/surest/nanopc-workspace/graphics/qt5",
         as_qmake_path(workspace / "os" / "graphics" / "qt5")),
        ("/mnt/d/workspace/luna-workspace", as_qmake_path(workspace)),
    ]
    if target is not None:
        target_text = target.as_posix()
        if target.parts and target.parts[0].lower().startswith("\\\\wsl.localhost\\"):
            target_text = "/" + "/".join(target.parts[1:])
        replacements.insert(0, (target_text, as_qmake_path(sdk)))
    output = text
    for source, destination in replacements:
        output = output.replace("//" + source.lstrip("/"), destination)
        output = output.replace(source, destination)
    return output


def relocate_metadata_tree(
    root: Path, sdk: Path, workspace: Path, target: Path | None = None
) -> None:
    """重写 mkspecs 内所有 qmake 文本元数据。"""
    for pattern in ("*.pri", "*.prf", "*.conf"):
        for path in root.rglob(pattern):
            text = path.read_text(encoding="utf-8")
            relocated = relocate_metadata(text, sdk, workspace, target)
            if relocated != text:
                path.write_text(relocated, encoding="utf-8", newline="\n")


def as_qmake_path(path: Path) -> str:
    """返回 qmake 可稳定解析的 Windows 正斜杠路径。"""
    return str(path.resolve()).replace("\\", "/")


def render_qt_conf(sdk: Path, sysroot: Path) -> str:
    """生成主机工具与目标安装树分离的 qt.conf。"""
    del sdk
    return (
        "[EffectivePaths]\n"
        "Prefix=..\n"
        "[DevicePaths]\n"
        "Prefix=/usr\n"
        "[Paths]\n"
        "Prefix=..\n"
        "HostPrefix=..\n"
        f"Sysroot={as_qmake_path(sysroot)}\n"
        "SysrootifyPrefix=false\n"
        "TargetSpec=luna-armv8a\n"
        "HostSpec=win32-g++\n"
    )


def render_mkspec(
    template: str,
    toolchain: Path,
    sysroot: Path,
    replacements: dict[str, str],
) -> str:
    """展开 Luna mkspec 中的构建路径占位符。"""
    values = {
        "@TOOLCHAIN@": as_qmake_path(toolchain),
        "@EXE_SUFFIX@": ".exe",
        "@SYSROOT@": as_qmake_path(sysroot),
        "@SYSROOT_LIB@": as_qmake_path(sysroot / "usr" / "lib64"),
        **replacements,
    }
    output = template
    for marker, value in values.items():
        output = output.replace(marker, value)
    unresolved = [word for word in output.split() if word.startswith("@")]
    if unresolved:
        raise ValueError(f"unresolved mkspec placeholders: {unresolved}")
    return output


def wsl_copy_command(source: Path, destination: Path) -> list[str]:
    """生成由 WSL 解引用符号链接的目录复制命令。"""
    parts = source.parts
    if not parts or not parts[0].lower().startswith("\\\\wsl.localhost\\"):
        raise ValueError(f"not a WSL UNC path: {source}")
    distro = parts[0].strip("\\").split("\\", 1)[1]
    source_linux = "/" + "/".join(parts[1:]) + "/"
    destination = destination.resolve()
    drive = destination.drive.rstrip(":").lower()
    destination_linux = (
        f"/mnt/{drive}/" + "/".join(destination.parts[1:]) + "/"
    )
    return [
        "wsl.exe", "-d", distro, "--", "rsync", "-aL",
        source_linux, destination_linux,
    ]


def copy_directory(source: Path, destination: Path) -> None:
    """复制目录并保留已有 SDK 中无关内容。"""
    if source.is_dir():
        if source.resolve() == destination.resolve():
            return
        destination.mkdir(parents=True, exist_ok=True)
        if source.parts[0].lower().startswith("\\\\wsl.localhost\\"):
            subprocess.run(wsl_copy_command(source, destination), check=True)
        else:
            shutil.copytree(source, destination, dirs_exist_ok=True)


def copy_file(source: Path, destination: Path) -> None:
    """复制单个文件；增量打包复用同一 SDK 时保留原文件。"""
    if source.resolve() == destination.resolve():
        return
    shutil.copy2(source, destination)


def copy_target_install_tree(target: Path, sdk: Path) -> None:
    """合并 Qt 构建目录与附加模块写入的目标安装树。"""
    for name in TARGET_DIRECTORIES:
        copy_directory(target / name, sdk / name)
    install = target / "sysroot"
    for name in TARGET_DIRECTORIES:
        copy_directory(install / name, sdk / name)
    copy_directory(target / "host" / "mkspecs", sdk / "mkspecs")


def verify_qmake(sdk: Path) -> None:
    """确认组合 SDK 的 qmake 查询不再引用临时构建目录。"""
    output = subprocess.check_output(
        [str(sdk / "bin" / "qmake.exe"), "-query"], text=True
    )
    normalized = output.replace("\\", "/")
    expected = as_qmake_path(sdk)
    if expected.lower() not in normalized.lower():
        raise RuntimeError("qmake does not report the packaged SDK prefix")
    if "D:/q5w" in normalized or "/home/" in normalized:
        raise RuntimeError("qmake still exposes a build-time path")


def verify_public_headers(sdk: Path) -> None:
    """确认交付 SDK 包含可独立编译应用的 Qt 公共头。"""
    for relative in REQUIRED_PUBLIC_HEADERS:
        header = sdk / "include" / relative
        if not header.is_file():
            raise FileNotFoundError(header)


def verify_target_libraries(sdk: Path) -> None:
    """确认 SDK 包含需求范围内可实际链接的目标 Qt 库。"""
    for name in REQUIRED_TARGET_LIBRARIES:
        library = sdk / "lib" / name
        if not library.is_file():
            raise FileNotFoundError(library)


def verify_example_tree(source: Path, destination: Path) -> None:
    """确认 SDK 示例树完整包含源码树中的全部 qmake 工程。"""
    expected = {
        path.relative_to(source) for path in source.rglob("*.pro")
    }
    missing = sorted(
        str(path) for path in expected if not (destination / path).is_file()
    )
    if missing:
        raise RuntimeError("missing Qt examples: " + ", ".join(missing))


def syncqt_command(qtbase: Path, perl: Path, sdk: Path) -> list[str]:
    """生成 Qt 官方 syncqt 公共头文件安装命令。"""
    return [
        str(perl), str(qtbase / "bin" / "syncqt.pl"),
        "-copy", "-windows", "-quiet", "-version", "5.15.19",
        "-outdir", str(sdk), str(qtbase),
    ]


def generate_public_headers(sdk: Path, perl: Path) -> None:
    """从固定版本 QtBase 源码生成 SDK 公共头和转发头。"""
    qtbase = ROOT / "upstream" / "qtbase-everywhere-src-5.15.19"
    script = qtbase / "bin" / "syncqt.pl"
    if not perl.is_file():
        raise FileNotFoundError(perl)
    if not script.is_file():
        raise FileNotFoundError(script)
    subprocess.run(syncqt_command(qtbase, perl, sdk), check=True)


def package(
    sdk: Path,
    target: Path,
    host_tools: Path,
    host_mkspecs: Path,
    toolchain: Path,
    sysroot: Path,
    perl: Path,
) -> None:
    """生成可由 Windows Qt Creator 使用的 Luna Qt SDK。"""
    sdk.mkdir(parents=True, exist_ok=True)
    (sdk / "config-temp").mkdir(exist_ok=True)
    copy_directory(require_host_mkspecs(host_mkspecs), sdk / "mkspecs")
    copy_target_install_tree(target, sdk)
    generate_public_headers(sdk, perl)

    binary = sdk / "bin"
    binary.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_HOST_TOOLS:
        source = host_tools / name
        if not source.is_file():
            raise FileNotFoundError(source)
        copy_file(source, binary / name)
        copy_file(source, binary / Path(name).stem)
    (binary / "qt.conf").write_text(
        render_qt_conf(sdk, sysroot), encoding="utf-8", newline="\n"
    )

    workspace = ROOT.parents[2]
    repository = workspace / "os" / "graphics"
    relocate_metadata_tree(sdk / "mkspecs", sdk, workspace, target)
    template = (ROOT / "mkspecs" / "luna-armv8a" / "qmake.conf").read_text(
        encoding="utf-8"
    )
    replacements = {
        "@QT_MKSPECS@": as_qmake_path(sdk / "mkspecs"),
        "@QT_HOST_BINS@": as_qmake_path(sdk / "bin"),
        "@MESA_INCLUDE@": as_qmake_path(repository / "mesa" / "upstream" / "include"),
        "@MESA_GBM_INCLUDE@": as_qmake_path(
            repository / "mesa" / "upstream" / "src" / "gbm" / "main"
        ),
        "@LIBDRM_INCLUDE@": as_qmake_path(repository / "libdrm" / "upstream"),
        "@LIBDRM_UAPI_INCLUDE@": as_qmake_path(
            repository / "libdrm" / "upstream" / "include" / "drm"
        ),
        "@STAGING_LIB@": as_qmake_path(sdk / "staging" / "lib"),
    }
    spec = sdk / "mkspecs" / "luna-armv8a"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "qmake.conf").write_text(
        render_mkspec(template, toolchain, sysroot, replacements),
        encoding="utf-8", newline="\n",
    )
    shutil.copy2(ROOT / "mkspecs" / "luna-armv8a" / "qplatformdefs.h", spec)
    delivery_scripts = sdk / "scripts"
    delivery_scripts.mkdir(exist_ok=True)
    for name in DELIVERY_SCRIPTS:
        shutil.copy2(SCRIPT_DIRECTORY / name, delivery_scripts / name)
    shutil.copy2(ROOT / "sdk.md", sdk / "README.md")
    for source, destination in DELIVERY_EXAMPLE_TREES:
        source_path = ROOT / source
        destination_path = sdk / "examples" / destination
        copy_directory(source_path, destination_path)
        verify_example_tree(source_path, destination_path)
    for source, destination in DELIVERY_CUSTOM_EXAMPLES:
        copy_directory(ROOT / source, sdk / "examples" / destination)
    verify_public_headers(sdk)
    verify_target_libraries(sdk)
    verify_qmake(sdk)


def main() -> None:
    workspace = ROOT.parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, default=Path(os.environ.get("LUNA_GRAPHICS_SDK", str(ROOT.parent.parent / "luna-sdk/qt5-5.15.19/staging"))).parent)
    parser.add_argument(
        "--target", type=Path,
        default=Path(
            "//wsl.localhost/ubuntu20.04/home/surest/nanopc-workspace/graphics/qt5/"
            "build/target-armv8a-luna"
        ),
    )
    parser.add_argument(
        "--host-tools", type=Path,
        default=ROOT / "build" / "host-windows" / "sdk-bin",
    )
    parser.add_argument(
        "--host-mkspecs", type=Path,
        default=ROOT / "build" / "host-windows" / "mkspecs",
    )
    parser.add_argument(
        "--toolchain", type=Path,
        default=Path(os.environ.get("LUNA_GRAPHICS_TOOLCHAIN", str(workspace / "tools/toolchains/aarch64-none-linux-gnu/bin"))),
    )
    parser.add_argument(
        "--sysroot", type=Path,
        default=workspace / "tools" / "toolchains" / "aarch64-none-linux-gnu"
        / "aarch64-none-linux-gnu" / "libc",
    )
    parser.add_argument(
        "--perl", type=Path,
        default=Path(os.environ.get(
            "PERL_BIN", "C:/Program Files/Git/usr/bin/perl.exe"
        )),
    )
    args = parser.parse_args()
    package(
        args.sdk, args.target, args.host_tools, args.host_mkspecs,
        args.toolchain, args.sysroot, args.perl,
    )


if __name__ == "__main__":
    main()
