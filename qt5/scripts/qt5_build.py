"""Configure and build the supported Qt 5.15.19 modules for Luna ARMv8A."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


IS_WINDOWS = os.name == "nt"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "qtbase-everywhere-src-5.15.19"
BUILD = ROOT / "build" / os.environ.get("LUNA_QT_BUILD_NAME", "qt5-armv8a-linux")
STAGING = BUILD / "staging"
STAGING_BIN = STAGING / "bin"
STAGING_LIB = STAGING / "lib"
STAGING_PKGCONFIG = STAGING_LIB / "pkgconfig"
SPEC_TEMPLATE = ROOT / "mkspecs" / "luna-armv8a"
TOOLCHAIN_ROOT = Path(
    os.environ.get(
        "LUNA_QT_TOOLCHAIN",
        (
            "D:/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu"
            if IS_WINDOWS
            else "/mnt/d/workspace/luna-workspace/tools/toolchains/"
            "arm-gnu-toolchain-14.3.rel1-x86_64-aarch64-none-linux-gnu"
        ),
    )
)
TOOLCHAIN_BIN = TOOLCHAIN_ROOT / "bin"
REFERENCE_SYSROOT = Path(
    os.environ.get(
        "LUNA_QT_REFERENCE_SYSROOT",
        (
            "D:/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu/"
            "aarch64-none-linux-gnu/libc"
            if IS_WINDOWS
            else "/mnt/d/workspace/luna-workspace/tools/toolchains/"
            "aarch64-none-linux-gnu/aarch64-none-linux-gnu/libc"
        ),
    )
)
SYSROOT = Path(os.environ.get("LUNA_QT_SYSROOT", str(REFERENCE_SYSROOT)))
SYSROOT_LIB = SYSROOT / "usr" / "lib64"
GRAPHICS_ROOT = ROOT.parent
MESA = GRAPHICS_ROOT / "mesa"
LIBDRM = GRAPHICS_ROOT / "libdrm"
MESA_INCLUDE = MESA / "upstream" / "include"
MESA_GBM_INCLUDE = MESA / "upstream" / "src" / "gbm" / "main"
MESA_EGL_LIB = MESA / "build" / "mesa-25.2.8" / "src" / "egl"
MESA_GLES_LIB = MESA / "build" / "mesa-25.2.8" / "src" / "mapi" / "es2api"
MESA_GBM_LIB = MESA / "build" / "mesa-25.2.8" / "src" / "gbm"
MESA_GALLIUM_LIB = (
    MESA / "build" / "mesa-25.2.8" / "src" / "gallium" / "targets" / "dri"
)
MESA_EXPAT_LIB = (
    MESA / "build" / "mesa-25.2.8" / "subprojects" / "expat-2.5.0"
)
LIBDRM_INCLUDE = LIBDRM / "upstream"
LIBDRM_UAPI_INCLUDE = LIBDRM_INCLUDE / "include" / "drm"
LIBDRM_LIB = LIBDRM / "build" / "libdrm" / "armv8a-user"
SMOKE_SOURCE = ROOT / "examples" / "eglfs-smoke"
SMOKE_BUILD = BUILD / "examples" / "eglfs-smoke"
WIDGETS_SOURCE = ROOT / "examples" / "widgets-display"
WIDGETS_BUILD = BUILD / "examples" / "widgets-display"


def slash(path: Path) -> str:
    return path.resolve().as_posix()


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise SystemExit(f"missing {description}: {path}")


def versioned_library(directory: Path, name: str) -> Path:
    matches = sorted(path for path in directory.glob(f"{name}.so.*") if path.is_file())
    if not matches:
        raise SystemExit(f"missing versioned library {name}: {directory}")
    return matches[0]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_target_abi() -> None:
    """确认 Qt 目标代码直接使用 Windows Catboy 的 glibc/sysroot。"""
    artifacts = (
        Path("usr/include/features.h"),
        Path("lib/ld-linux-aarch64.so.1"),
        Path("lib64/libc.so.6"),
        Path("usr/lib64/crt1.o"),
    )
    manifest: dict[str, dict[str, str]] = {}
    for relative in artifacts:
        target = SYSROOT / relative
        reference = REFERENCE_SYSROOT / relative
        require_file(target, f"Linux target ABI artifact {relative}")
        require_file(reference, f"Windows target ABI artifact {relative}")
        target_hash = file_sha256(target)
        reference_hash = file_sha256(reference)
        if target_hash != reference_hash:
            raise SystemExit(
                f"target ABI mismatch: {relative}\n"
                f"  Linux:  {target_hash}\n"
                f"  Windows:{reference_hash}"
            )
        manifest[relative.as_posix()] = {
            "sha256": target_hash,
            "linux": str(target),
            "windows": str(reference),
        }
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "target-abi.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def stage_graphics_libraries() -> None:
    egl = versioned_library(MESA_EGL_LIB, "libEGL")
    gles = versioned_library(MESA_GLES_LIB, "libGLESv2")
    gbm = versioned_library(MESA_GBM_LIB, "libgbm")
    gallium = MESA_GALLIUM_LIB / "libgallium-25.2.8.so"
    require_file(gallium, "Mesa Gallium shared library")
    expat = versioned_library(MESA_EXPAT_LIB, "libexpat")
    libraries = {
        "libEGL.so": egl,
        "libEGL.so.1": egl,
        "libGLESv2.so": gles,
        "libGLESv2.so.2": gles,
        "libgbm.so": gbm,
        "libgbm.so.1": gbm,
        "libgallium-25.2.8.so": gallium,
        "libexpat.so": expat,
        "libexpat.so.1": expat,
        "libdrm.a": LIBDRM_LIB / "libdrm.a",
    }
    STAGING_LIB.mkdir(parents=True, exist_ok=True)
    for name, source in libraries.items():
        require_file(source, f"{name} source library")
        shutil.copyfile(source, STAGING_LIB / name)
    STAGING_PKGCONFIG.mkdir(parents=True, exist_ok=True)
    (STAGING_PKGCONFIG / "gbm.pc").write_text(
        "prefix=/\n"
        f"includedir={slash(MESA_GBM_INCLUDE)}\n"
        f"libdir={slash(STAGING_LIB)}\n\n"
        "Name: gbm\n"
        "Description: Luna staged Mesa GBM\n"
        "Version: 25.2.8\n"
        "Libs: -L${libdir} -lgbm -lexpat -ldrm\n"
        "Cflags: -I${includedir}\n",
        encoding="utf-8",
        newline="\n",
    )


def stage_pkg_config() -> Path:
    """Expose pkgconf under the executable name expected by Qt configure."""
    source = shutil.which("pkg-config") or shutil.which("pkgconf")
    if not source:
        raise SystemExit("Qt GBM detection requires pkg-config or pkgconf")
    if not IS_WINDOWS:
        return Path(source)
    destination = STAGING_BIN / "pkg-config.exe"
    STAGING_BIN.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def reset_configure_state() -> None:
    """Remove cached qmake probes before configuring with current dependencies."""
    for attempt in range(5):
        if not BUILD.is_dir():
            return
        try:
            shutil.rmtree(BUILD)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(1.0)


def materialize_spec() -> Path:
    replacements = {
        "@QT_MKSPECS@": slash(SOURCE / "mkspecs"),
        "@TOOLCHAIN@": slash(TOOLCHAIN_BIN),
        "@SYSROOT@": slash(SYSROOT),
        "@SYSROOT_LIB@": slash(SYSROOT_LIB),
        "@STAGING_LIB@": slash(STAGING_LIB),
        "@MESA_INCLUDE@": slash(MESA_INCLUDE),
        "@MESA_GBM_INCLUDE@": slash(MESA_GBM_INCLUDE),
        "@MESA_EGL_LIB@": slash(MESA_EGL_LIB),
        "@MESA_GLES_LIB@": slash(MESA_GLES_LIB),
        "@MESA_GBM_LIB@": slash(MESA_GBM_LIB),
        "@LIBDRM_INCLUDE@": slash(LIBDRM_INCLUDE),
        "@LIBDRM_UAPI_INCLUDE@": slash(LIBDRM_UAPI_INCLUDE),
        "@LIBDRM_LIB@": slash(LIBDRM_LIB),
        "@EXE_SUFFIX@": ".exe" if IS_WINDOWS else "",
    }
    destinations = (
        SOURCE / "mkspecs" / "luna-armv8a",
        BUILD / "mkspecs" / "luna-armv8a",
    )
    for spec in destinations:
        spec.mkdir(parents=True, exist_ok=True)
        for name in ("qmake.conf", "qplatformdefs.h"):
            content = (SPEC_TEMPLATE / name).read_text(encoding="utf-8")
            for key, value in replacements.items():
                content = content.replace(key, value)
            destination = spec / name
            if destination.is_file():
                if destination.read_text(encoding="utf-8") == content:
                    continue
            destination.write_text(content, encoding="utf-8", newline="\n")
    return destinations[0]


def find_shell() -> str:
    candidates = (
        os.environ.get("QT_SHELL"),
        r"C:\Program Files\Git\bin\bash.exe",
        shutil.which("bash"),
        shutil.which("sh"),
    )
    shell = next((item for item in candidates if item and Path(item).is_file()), None)
    if not shell:
        raise SystemExit(
            "Qt configuration requires bash.exe or sh.exe; set QT_SHELL to its path"
        )
    return shell


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def configure() -> None:
    require_file(SOURCE / "configure", "Qt configure script")
    executable_suffix = ".exe" if IS_WINDOWS else ""
    require_file(
        TOOLCHAIN_BIN / f"aarch64-none-linux-gnu-gcc{executable_suffix}",
        "ARM C compiler",
    )
    require_file(
        TOOLCHAIN_BIN / f"aarch64-none-linux-gnu-g++{executable_suffix}",
        "ARM C++ compiler",
    )
    reset_configure_state()
    verify_target_abi()
    stage_graphics_libraries()
    pkg_config = stage_pkg_config()
    materialize_spec()
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "bin").mkdir(parents=True, exist_ok=True)
    (BUILD / "qmake").mkdir(parents=True, exist_ok=True)
    command = [
        find_shell(),
        slash(SOURCE / "configure"),
        "-platform",
        "win32-g++" if IS_WINDOWS else "linux-g++",
        "-xplatform",
        "luna-armv8a",
        "-I",
        slash(MESA_INCLUDE),
        "-I",
        slash(MESA_GBM_INCLUDE),
        "-I",
        slash(LIBDRM_INCLUDE),
        "-I",
        slash(LIBDRM_UAPI_INCLUDE),
        "-L",
        slash(STAGING_LIB),
        "-L",
        slash(SYSROOT_LIB),
        "-pkg-config",
        "-opensource",
        "-confirm-license",
        "-release",
        "-no-pch",
        "-prefix",
        "/usr",
        "-extprefix",
        slash(BUILD / "sysroot"),
        "-hostprefix",
        slash(BUILD / "host"),
        "-opengl",
        "es2",
        "-eglfs",
        "-kms",
        "-no-xcb",
        "-no-linuxfb",
        "-no-dbus",
        "-no-openssl",
        "-no-icu",
        "-nomake",
        "examples",
        "-nomake",
        "tests",
        "-skip",
        "qtwebengine",
    ]
    env = os.environ.copy()
    for name in ("QMAKESPEC", "XQMAKESPEC", "QMAKEPATH", "QMAKEFEATURES"):
        env.pop(name, None)
    path_entries = [str(STAGING_BIN), str(TOOLCHAIN_BIN)]
    if IS_WINDOWS:
        path_entries.extend(
            [r"C:\Program Files\Git\usr\bin", r"C:\Program Files\Git\bin"]
        )
    make_path = Path(os.environ.get("QT_MAKE", ""))
    if make_path.is_file():
        path_entries.append(str(make_path.parent))
    path_entries.append(env.get("PATH", ""))
    env["PATH"] = os.pathsep.join(path_entries)
    if IS_WINDOWS:
        env["MSYS2_ARG_CONV_EXCL"] = "/usr"
    env["PKG_CONFIG"] = slash(pkg_config)
    env["PKG_CONFIG_PATH"] = slash(STAGING_PKGCONFIG)
    env["PKG_CONFIG_LIBDIR"] = slash(STAGING_PKGCONFIG)
    env["PKG_CONFIG_SYSROOT_DIR"] = "/"
    print("Qt build root:", BUILD)
    subprocess.run(command, cwd=BUILD, env=env, check=True)


def build(stage: str, jobs: int) -> None:
    if not (BUILD / "Makefile").is_file():
        configure()
    # 源码可能从 Windows 工作区重新同步，每个阶段都按当前主机重建 mkspec。
    materialize_spec()
    make = os.environ.get("QT_MAKE") or shutil.which("make")
    if not make:
        raise SystemExit("Qt build requires make.exe; set QT_MAKE to its path")
    env = os.environ.copy()
    if IS_WINDOWS:
        env["PATH"] = os.pathsep.join(
            [r"C:\Program Files\Git\usr\bin", r"C:\Program Files\Git\bin", env["PATH"]]
        )
    qmake_name = "qmake.exe" if IS_WINDOWS else "qmake"
    run(
        [
            str(BUILD / "bin" / qmake_name),
            "-o",
            "Makefile",
            slash(SOURCE / "src" / "src.pro"),
        ],
        BUILD / "src",
        env,
    )
    for host_target in ("sub-moc", "sub-rcc", "sub-uic"):
        run([make, "-j1", host_target], BUILD / "src", env)
    run([make, "-j1", "sub-src-qmake_all"], BUILD, env)
    if stage in ("core", "gui-eglfs", "widgets"):
        target = {
            "core": "sub-corelib",
            "gui-eglfs": "sub-gui",
            "widgets": "sub-widgets",
        }[stage]
        run([make, f"-j{jobs}", target], BUILD / "src", env)
    else:
        run([make, f"-j{jobs}", "sub-platformsupport"], BUILD / "src", env)
        run(
            [make, f"-j{jobs}", "sub-eglfs"],
            BUILD / "src" / "plugins" / "platforms",
            env,
        )


def build_smoke(jobs: int) -> None:
    qmake = BUILD / "bin" / ("qmake.exe" if IS_WINDOWS else "qmake")
    require_file(qmake, "cross qmake")
    require_file(SMOKE_SOURCE / "eglfs-smoke.pro", "EGLFS smoke project")
    make = os.environ.get("QT_MAKE") or shutil.which("make")
    if not make:
        raise SystemExit("Qt build requires make.exe; set QT_MAKE to its path")
    if SMOKE_BUILD.is_dir():
        shutil.rmtree(SMOKE_BUILD)
    SMOKE_BUILD.mkdir(parents=True)
    run([str(qmake), slash(SMOKE_SOURCE / "eglfs-smoke.pro")], SMOKE_BUILD)
    run([make, f"-j{jobs}"], SMOKE_BUILD)


def build_widgets_display(jobs: int) -> None:
    qmake = BUILD / "bin" / "qmake"
    require_file(qmake, "cross qmake")
    require_file(WIDGETS_SOURCE / "widgets-display.pro", "Qt Widgets display project")
    make = os.environ.get("QT_MAKE") or shutil.which("make")
    if not make:
        raise SystemExit("Qt build requires make; set QT_MAKE to its path")
    if WIDGETS_BUILD.is_dir():
        shutil.rmtree(WIDGETS_BUILD)
    WIDGETS_BUILD.mkdir(parents=True)
    run([str(qmake), slash(WIDGETS_SOURCE / "widgets-display.pro")], WIDGETS_BUILD)
    run([make, f"-j{jobs}"], WIDGETS_BUILD)


def main() -> None:
    if IS_WINDOWS:
        raise SystemExit("Qt 统一在 Linux 构建，请按 README 将源码同步到 nanopc-workspace")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("configure", "core", "gui-eglfs", "kms", "widgets", "smoke",
                 "widgets-display"),
        required=True,
    )
    parser.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 1))
    args = parser.parse_args()
    if args.stage == "configure":
        configure()
    elif args.stage == "smoke":
        build_smoke(args.jobs)
    elif args.stage == "widgets-display":
        build_widgets_display(args.jobs)
    else:
        build(args.stage, args.jobs)


if __name__ == "__main__":
    main()
