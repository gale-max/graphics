"""Configure and build the supported Qt 5.15.19 modules for Luna ARMv8A."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "qtbase-everywhere-src-5.15.19"
BUILD = ROOT / "build" / os.environ.get("LUNA_QT_BUILD_NAME", "qt5-armv8a")
STAGING = BUILD / "staging"
STAGING_BIN = STAGING / "bin"
STAGING_LIB = STAGING / "lib"
STAGING_PKGCONFIG = STAGING_LIB / "pkgconfig"
SPEC_TEMPLATE = ROOT / "mkspecs" / "luna-armv8a"
TOOLCHAIN_ROOT = Path(
    os.environ.get(
        "LUNA_QT_TOOLCHAIN",
        "D:/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu",
    )
)
TOOLCHAIN_BIN = TOOLCHAIN_ROOT / "bin"
SYSROOT = TOOLCHAIN_ROOT / "aarch64-none-linux-gnu" / "libc"
SYSROOT_LIB = SYSROOT / "usr" / "lib64"
GRAPHICS_ROOT = ROOT.parent
MESA = GRAPHICS_ROOT / "mesa"
LIBDRM = GRAPHICS_ROOT / "libdrm"
MESA_INCLUDE = MESA / "upstream" / "include"
MESA_GBM_INCLUDE = MESA / "upstream" / "src" / "gbm" / "main"
MESA_EGL_LIB = MESA / "build" / "mesa-25.2.8" / "src" / "egl"
MESA_GLES_LIB = MESA / "build" / "mesa-25.2.8" / "src" / "mapi" / "es2api"
MESA_GBM_LIB = MESA / "build" / "mesa-25.2.8" / "src" / "gbm"
MESA_GLAPI_LIB = MESA / "build" / "mesa-25.2.8" / "src" / "mapi" / "shared-glapi"
MESA_EXPAT_LIB = (
    MESA / "build" / "mesa-25.2.8" / "subprojects" / "expat-2.5.0"
)
LIBDRM_INCLUDE = LIBDRM / "upstream"
LIBDRM_UAPI_INCLUDE = LIBDRM_INCLUDE / "include" / "drm"
LIBDRM_LIB = LIBDRM / "build" / "libdrm" / "armv8a-user"
SMOKE_SOURCE = ROOT / "examples" / "eglfs-smoke"
SMOKE_BUILD = BUILD / "examples" / "eglfs-smoke"


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


def stage_graphics_libraries() -> None:
    egl = versioned_library(MESA_EGL_LIB, "libEGL")
    gles = versioned_library(MESA_GLES_LIB, "libGLESv2")
    gbm = versioned_library(MESA_GBM_LIB, "libgbm")
    glapi = versioned_library(MESA_GLAPI_LIB, "libglapi")
    expat = versioned_library(MESA_EXPAT_LIB, "libexpat")
    libraries = {
        "libEGL.so": egl,
        "libEGL.so.1": egl,
        "libGLESv2.so": gles,
        "libGLESv2.so.2": gles,
        "libgbm.so": gbm,
        "libgbm.so.1": gbm,
        "libglapi.so": glapi,
        "libglapi.so.0": glapi,
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
        "Libs: -L${libdir} -lgbm -lglapi -lexpat -ldrm\n"
        "Cflags: -I${includedir}\n",
        encoding="utf-8",
        newline="\n",
    )


def stage_pkg_config() -> Path:
    """Expose pkgconf under the executable name expected by Qt configure."""
    source = shutil.which("pkg-config") or shutil.which("pkgconf")
    if not source:
        raise SystemExit("Qt GBM detection requires pkg-config or pkgconf")
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
            (spec / name).write_text(content, encoding="utf-8", newline="\n")
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
    require_file(TOOLCHAIN_BIN / "aarch64-none-linux-gnu-gcc.exe", "ARM C compiler")
    require_file(TOOLCHAIN_BIN / "aarch64-none-linux-gnu-g++.exe", "ARM C++ compiler")
    reset_configure_state()
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
        "win32-g++",
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
    git_usr_bin = Path(r"C:\Program Files\Git\usr\bin")
    git_bin = Path(r"C:\Program Files\Git\bin")
    path_entries = [
        str(STAGING_BIN),
        str(git_usr_bin),
        str(git_bin),
        str(TOOLCHAIN_BIN),
    ]
    make_path = Path(os.environ.get("QT_MAKE", ""))
    if make_path.is_file():
        path_entries.append(str(make_path.parent))
    path_entries.append(env.get("PATH", ""))
    env["PATH"] = os.pathsep.join(path_entries)
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
    make = os.environ.get("QT_MAKE") or shutil.which("make")
    if not make:
        raise SystemExit("Qt build requires make.exe; set QT_MAKE to its path")
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        [r"C:\Program Files\Git\usr\bin", r"C:\Program Files\Git\bin", env["PATH"]]
    )
    run([make, "-j1", "sub-src-qmake_all"], BUILD, env)
    for host_target in ("sub-moc", "sub-rcc", "sub-uic"):
        run([make, "-j1", host_target], BUILD / "src", env)
    if stage in ("core", "gui-eglfs"):
        target = {"core": "sub-corelib", "gui-eglfs": "sub-gui"}[stage]
        run([make, f"-j{jobs}", target], BUILD / "src", env)
    else:
        run([make, f"-j{jobs}", "sub-platformsupport"], BUILD / "src", env)
        run(
            [make, f"-j{jobs}", "sub-eglfs"],
            BUILD / "src" / "plugins" / "platforms",
            env,
        )


def build_smoke(jobs: int) -> None:
    qmake = BUILD / "bin" / "qmake.exe"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("configure", "core", "gui-eglfs", "kms", "smoke"),
        required=True,
    )
    parser.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 1))
    args = parser.parse_args()
    if args.stage == "configure":
        configure()
    elif args.stage == "smoke":
        build_smoke(args.jobs)
    else:
        build(args.stage, args.jobs)


if __name__ == "__main__":
    main()
