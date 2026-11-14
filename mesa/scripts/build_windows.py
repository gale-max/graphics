"""Build Mesa 25.2.8: unchanged Panfrost default, opt-in isolated QEMU profile."""

from pathlib import Path
import os
import ast
import configparser
import shutil
import subprocess
import sys
import argparse
import hashlib
import json
import re
import time
from collections import deque


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream"
BUILD = ROOT / "build" / "mesa-25.2.8"
CROSS_FILE = ROOT / "toolchains" / "luna-armv8a-windows.ini"
HOST_TOOL_DIRECTORY = ROOT / "build" / "host-tools"
GENERATED_MATERIALS = ROOT / Path("generated/panfrost/25.2.8")
GENERATED_LEXERS = ROOT / Path("generated/lexers/25.2.8")
HOST_TOOLS = ("mesa_clc", "vtn_bindgen2", "panfrost_compile")
TARGETS = (
    "src/gbm/libgbm.so.1.0.0",
    "src/egl/libEGL.so.1.0.0",
    "src/mapi/es2api/libGLESv2.so.2.0.0",
    "src/gallium/targets/dri/libgallium-25.2.8.so",
    "src/gbm/backends/dri/dri_gbm.so",
)
# With GLX disabled, Mesa 25's GBM/EGL directly link libgallium. The dril
# compatibility library is an Xorg/GLX-only target, not a GPU runtime loader.
QEMU_TARGETS = TARGETS
OPTIONS = (
    "-Dplatforms=wayland", "-Degl-native-platform=drm",
    "-Dlegacy-wayland=bind-wayland-display",
    "-Dgallium-drivers=panfrost", "-Dvulkan-drivers=",
    "-Degl=enabled", "-Dgbm=enabled", "-Dgles1=disabled",
    "-Dgles2=enabled", "-Dopengl=true", "-Dglx=disabled",
    "-Dglvnd=false", "-Dshared-glapi=enabled", "-Dllvm=disabled",
    "-Ddraw-use-llvm=false", "-Dshader-cache=disabled",
    "-Dmesa-clc=system", "-Dprecomp-compiler=system",
    "-Dbuild-tests=false", "-Dgallium-vdpau=disabled",
    "-Dgallium-va=disabled", "-Dgallium-rusticl=false",
    "-Dvalgrind=disabled", "-Dlibunwind=disabled",
    "-Dlmsensors=disabled", "-Dzstd=disabled", "-Dzlib=disabled",
    "-Dtools=", "-Dvideo-codecs=", "-Dselinux=false",
    "-Dperfetto=false", "-Dbuildtype=release", "-Db_ndebug=true",
    "-Dgbm-backends-path=/media/mmcblk1p1/graphics",
    "-Ddri-drivers-path=/media/mmcblk1p1/graphics/dri",
    "-Dluna-prebuilt-panfrost=true",
    "-Dluna-prebuilt-wayland=true",
    "-Dluna-prebuilt-lexers=true",
    "-Dbackend_max_links=1",
)

QT_SDK_STAGING = Path(os.environ.get(
    "LUNA_GRAPHICS_SDK", str(ROOT.parents[1] / "luna-sdk/qt5-5.15.19/staging")))
TOOLCHAIN = Path(os.environ.get(
    "LUNA_GRAPHICS_TOOLCHAIN",
    str(ROOT.parents[2] / "tools/toolchains/aarch64-none-linux-gnu/bin")))
PKGCONFIG_DIRECTORY = ROOT / "pkgconfig"
WAYLAND_PACKAGES = (
    "wayland-client.pc",
    "wayland-server.pc",
    "wayland-egl.pc",
    "wayland-egl-backend.pc",
    "wayland-cursor.pc",
    "libffi.pc",
)


def run(arguments: list[str], environment: dict[str, str]) -> None:
    subprocess.run(arguments, cwd=ROOT, env=environment, check=True)


def prepare_host_tools(environment: dict[str, str]) -> None:
    """生成仅供 Meson 发现的占位工具；正式构建使用固化材料。"""
    HOST_TOOL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for tool in HOST_TOOLS:
        wrapper = HOST_TOOL_DIRECTORY / f"{tool}.cmd"
        wrapper.write_text(
            "@echo Mesa host material is missing. 1>&2\r\n@exit /b 86\r\n",
            encoding="utf-8",
            newline="\r\n",
        )
    environment["PATH"] = (
        str(HOST_TOOL_DIRECTORY) + os.pathsep + environment.get("PATH", "")
    )


def prepare_wayland_pkgconfig(destination: Path | None = None) -> None:
    """为 Windows 交叉构建生成指向 Luna Qt SDK 的 Wayland 元数据。"""
    source_directory = QT_SDK_STAGING / "lib/pkgconfig"
    if not QT_SDK_STAGING.is_dir():
        raise FileNotFoundError(f"Qt SDK staging not found: {QT_SDK_STAGING}")

    destination = destination if destination is not None else PKGCONFIG_DIRECTORY
    destination.mkdir(parents=True, exist_ok=True)
    for package in WAYLAND_PACKAGES:
        source = source_directory / package
        if not source.is_file():
            raise FileNotFoundError(f"Wayland pkg-config file not found: {source}")
        content = source.read_text(encoding="utf-8")
        lines = content.splitlines()
        lines[0] = f"prefix={QT_SDK_STAGING.as_posix()}"
        for index, line in enumerate(lines):
            if line.startswith("Cflags:"):
                lines[index] = f"Cflags: -I{(QT_SDK_STAGING / 'include').as_posix()}"
            elif line.startswith("Libs: -L"):
                library = line.split(" ")[-1]
                lines[index] = (
                    f"Libs: -L{(QT_SDK_STAGING / 'lib').as_posix()} {library}"
                )
        (destination / package).write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )


def fix_cross_detected_configuration(build: Path | None = None) -> None:
    """修正只应在目标机上探测、却被 Windows 主机污染的配置。"""
    build = build if build is not None else BUILD
    expat_config = build / "subprojects" / "expat-2.5.0" / "expat_config.h"
    if expat_config.is_file():
        content = expat_config.read_text(encoding="utf-8")
        content = content.replace("#define HAVE_ARC4RANDOM\n", "")
        content = content.replace("#define HAVE_ARC4RANDOM_BUF\n", "")
        expat_config.write_text(content, encoding="utf-8", newline="\n")


def install_target_lexers(build: Path | None = None) -> None:
    """安装仓库内固化的目标 lexer，避免依赖开发者本机的 Flex 路径。"""
    build = build if build is not None else BUILD
    generators = (
        (
            GENERATED_LEXERS / "glcpp-lex.c",
            build / "src/compiler/glsl/glcpp/glcpp-lex.c",
        ),
        (
            GENERATED_LEXERS / "glsl_lexer.cpp",
            build / "src/compiler/glsl/glsl_lexer.cpp",
        ),
        (
            GENERATED_LEXERS / "lex.yy.c",
            build / "src/mesa/program/lex.yy.c",
        ),
    )

    for source, output in generators:
        if not source.is_file():
            raise FileNotFoundError(f"generated lexer not found: {source}")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
        os.utime(output, None)


def prepare_cross_file(path: Path | None = None, pkgconfig: Path | None = None) -> Path:
    """在构建目录生成本副本的 include/pkgconfig 路径，保留工具链配置。"""
    config = configparser.ConfigParser(interpolation=None)
    config.read(CROSS_FILE, encoding="utf-8")
    for key, name in (("c", "gcc"), ("cpp", "g++"), ("ar", "ar"), ("strip", "strip")):
        config["binaries"][key] = repr((TOOLCHAIN / f"aarch64-none-linux-gnu-{name}.exe").as_posix())
    if pkgconfig is not None:
        # pkgconf on Windows otherwise relocates ${prefix} to the external
        # metadata directory, even when the .pc file has an absolute prefix.
        command = ast.literal_eval(config["binaries"]["pkg-config"])
        command = [command] if isinstance(command, str) else command
        config["binaries"]["pkg-config"] = repr([*command, "--dont-define-prefix"])
    pkgconfig = pkgconfig if pkgconfig is not None else ROOT / "pkgconfig"
    config["properties"]["pkg_config_libdir"] = repr(pkgconfig.as_posix())
    compat = (ROOT.parent / "libdrm/include/luna_graphics_compat.h").as_posix()
    for key in ("c_args", "cpp_args"):
        args = ast.literal_eval(config["built-in options"][key])
        config["built-in options"][key] = repr([
            compat if arg.endswith("graphics/libdrm/include/luna_graphics_compat.h")
            else "-I" + (QT_SDK_STAGING / "include").as_posix()
            if arg == "-I@GRAPHICS_SDK@/include" else arg
            for arg in args
        ])
    path = path if path is not None else ROOT / "build/luna-armv8a-local.ini"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        config.write(stream)
    return path


def cross_builtin_options(path: Path) -> list[str]:
    config = configparser.ConfigParser(interpolation=None)
    config.read(path, encoding="utf-8")
    return ["-D" + key + "=" + config["built-in options"][key]
            for key in ("c_args", "cpp_args")]


def build_panfrost() -> int:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PKG_CONFIG_PATH"] = str(ROOT / "pkgconfig")
    prepare_wayland_pkgconfig()
    prepare_host_tools(environment)
    configured = (BUILD / "build.ninja").is_file()
    BUILD.mkdir(parents=True, exist_ok=True)
    local_cross = ROOT / "build/luna-armv8a-local.ini"
    previous_cross = local_cross.read_text(encoding="utf-8") if local_cross.is_file() else None
    cross_file = prepare_cross_file()
    cross_changed = previous_cross != cross_file.read_text(encoding="utf-8")
    setup = [
        sys.executable, "-m", "mesonbuild.mesonmain", "setup",
        str(BUILD), str(SOURCE), "--cross-file", str(cross_file),
        *OPTIONS, *cross_builtin_options(cross_file),
    ]
    if configured:
        saved = configparser.ConfigParser(interpolation=None)
        saved.read(BUILD / "meson-private/cmd_line.txt", encoding="utf-8")
        previous = ast.literal_eval(saved.get("properties", "cross_file", fallback="[]"))
        if cross_changed or [Path(value).resolve() for value in previous] != [cross_file.resolve()]:
            if not BUILD.resolve().is_relative_to((ROOT / "build").resolve()):
                raise RuntimeError("refusing to wipe outside the Mesa build directory")
            setup.append("--wipe")
        else:
            setup.append("--reconfigure")
    run(setup, environment)
    if not GENERATED_MATERIALS.is_dir():
        raise FileNotFoundError(
            f"generated materials not found: {GENERATED_MATERIALS}"
        )
    fix_cross_detected_configuration()
    install_target_lexers()
    # 目标 lexer 与 Panfrost 主机工具输出均已固化，目标编译可直接并行执行。
    # 链接由 Meson job pool 串行，编译仍保持并行。
    run(["ninja", "-j4", "-C", str(BUILD), *TARGETS], environment)
    return 0


def qemu_options(runtime_prefix: str) -> tuple[str, ...]:
    """Mesa 25.2 uses softpipe as a Gallium option, not the old swrast name."""
    if not runtime_prefix.startswith("/") or "\\" in runtime_prefix or ":" in runtime_prefix:
        raise ValueError("runtime prefix must be an absolute guest POSIX path")
    overrides = {
        "gallium-drivers": "virgl,softpipe",
        "luna-prebuilt-panfrost": "false",
        "mesa-clc": "auto",
        "precomp-compiler": "auto",
        "gbm-backends-path": runtime_prefix.rstrip("/"),
        "dri-drivers-path": runtime_prefix.rstrip("/") + "/dri",
    }
    return tuple("-D" + key + "=" + overrides.get(key, value)
                 for key, value in (option[2:].split("=", 1) for option in OPTIONS))


def claim_qemu_output(output: Path) -> Path:
    """Permit reconfiguration/wipe only in this profile's explicitly owned tree."""
    output = output.resolve()
    for protected in (ROOT.parent.resolve(), QT_SDK_STAGING.resolve()):
        if output.is_relative_to(protected) or protected.is_relative_to(output):
            raise ValueError(f"output overlaps existing graphics/SDK tree: {output}")
    marker = output / ".luna-mesa-qemu.json"
    identity = {"profile": "qemu", "version": "25.2.8", "source": str(SOURCE.resolve())}
    if marker.is_file():
        if json.loads(marker.read_text(encoding="utf-8")) != identity:
            raise ValueError(f"output belongs to another Mesa build: {output}")
    elif any((output / name).exists() for name in ("build", "pkgconfig", "runtime", "cache", "temp")):
        raise ValueError(f"output has unowned build artifacts: {output}")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("build", "pkgconfig", "runtime", "cache", "temp"):
        if not (output / name).resolve().is_relative_to(output):
            raise ValueError(f"output child escapes owned directory: {name}")
    marker.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return output


def qemu_environment(output: Path) -> dict[str, str]:
    environment = os.environ.copy()
    locations = {
        "TEMP": "temp", "TMP": "temp", "TMPDIR": "temp",
        "XDG_CACHE_HOME": "cache", "CCACHE_DIR": "cache/ccache",
        "MESON_PACKAGE_CACHE_DIR": "cache/meson", "PIP_CACHE_DIR": "cache/pip",
        "MESA_SHADER_CACHE_DIR": "cache/mesa", "PKG_CONFIG_PATH": "pkgconfig",
    }
    for key, relative in locations.items():
        directory = output / relative
        directory.mkdir(parents=True, exist_ok=True)
        environment[key] = str(directory)
    environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return environment


def run_concise(arguments: list[str], environment: dict[str, str], output: Path) -> None:
    """Stream sparse progress; retain status and a bounded error tail, not full logs."""
    started = time.monotonic()
    tail: deque[str] = deque(maxlen=24)
    warnings = 0
    lines = 0
    print("mesa qemu: running " + ("ninja" if arguments[0] == "ninja" else "meson setup"), flush=True)
    with subprocess.Popen(arguments, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace") as process:
        for line in process.stdout:
            line = line.rstrip()
            tail.append(line if len(line) <= 400 else line[:400] + " ... [line truncated]")
            lines += 1
            warnings += "warning:" in line.lower()
            if line.startswith("[") and lines % 100 == 0:
                print("mesa qemu: " + line[:180], flush=True)
        code = process.wait()
    record = {"command": arguments, "exit_code": code, "seconds": round(time.monotonic() - started, 2),
              "output_lines": lines, "warning_lines": warnings, "error_tail": list(tail) if code else []}
    with (output / "command-results.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
    print(f"mesa qemu: exit={code}, seconds={record['seconds']}, warning lines={warnings}", flush=True)
    if code:
        print("\n".join(tail), flush=True)
        raise subprocess.CalledProcessError(code, arguments)


def package_qemu(output: Path, runtime_prefix: str) -> None:
    """Copy only this build's Mesa libraries, with SONAME aliases for Windows."""
    from mesonbuild.scripts.depfixer import fix_elf

    runtime = output / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    readelf = TOOLCHAIN / "aarch64-none-linux-gnu-readelf.exe"
    aliases = {
        "libgbm.so.1.0.0": ("libgbm.so", "libgbm.so.1"),
        "libEGL.so.1.0.0": ("libEGL.so", "libEGL.so.1"),
        "libGLESv2.so.2.0.0": ("libGLESv2.so", "libGLESv2.so.2"),
    }
    artifacts = []
    for target in QEMU_TARGETS:
        source = output / "build" / target
        header = subprocess.run([str(readelf), "-h", str(source)], capture_output=True, text=True, check=True).stdout
        if "AArch64" not in header:
            raise RuntimeError(f"not an aarch64 target library: {source}")
        exported = runtime / source.name
        shutil.copy2(source, exported)
        dynamic = subprocess.run([str(readelf), "-d", str(exported)], capture_output=True, text=True, check=True).stdout
        build_runpaths = re.findall(r"\((?:RUNPATH|RPATH)\).*\[([^]]*)\]", dynamic)
        if build_runpaths:
            # Use Meson's own ELF installer helper on the exported copy only.
            # Host SDK/build paths cannot be meaningful guest search paths.
            remove = {part.encode("utf-8") for path in build_runpaths for part in path.split(":")}
            fix_elf(str(exported), remove, b"", verbose=False)
            dynamic = subprocess.run([str(readelf), "-d", str(exported)], capture_output=True, text=True, check=True).stdout
        needed = re.findall(r"\(NEEDED\).*\[([^]]+)\]", dynamic)
        soname = re.findall(r"\(SONAME\).*\[([^]]+)\]", dynamic)
        runpaths = re.findall(r"\((?:RUNPATH|RPATH)\).*\[([^]]*)\]", dynamic)
        versions = subprocess.run([str(readelf), "--version-info", str(exported)],
                                  capture_output=True, text=True, check=True).stdout
        copies = (source.name, *aliases.get(source.name, ()))
        for name in copies[1:]:
            destination = runtime / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(exported, destination)
        artifacts.append({"source": str(source), "files": list(copies), "bytes": source.stat().st_size,
                          "sha256": hashlib.sha256(exported.read_bytes()).hexdigest(),
                          "build_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                          "needed": needed, "soname": soname, "runpath": runpaths,
                          "required_symbol_versions": sorted(set(re.findall(
                              r"Name:\s+((?:GLIBC|GLIBCXX|CXXABI)_[A-Za-z0-9_.]+)", versions)))})
    manifest = {"profile": "qemu", "mesa_version": (SOURCE / "VERSION").read_text().strip(),
                "gallium": ["virgl", "softpipe"], "llvm": False, "runtime_prefix": runtime_prefix,
                "runtime": str(runtime), "artifacts": artifacts,
                "acceptance": "cross-build only; no guest execution or acceleration claim",
                "dependency_note": "SDK/toolchain dependencies are listed, not overwritten or repackaged",
                "runtime_note": "build rpaths removed from runtime copies; set LD_LIBRARY_PATH and GBM_BACKENDS_PATH to this isolated runtime"}
    (output / "libraries.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"mesa qemu: packaged {len(artifacts)} aarch64 libraries into {runtime}", flush=True)


def build_qemu(output: Path, runtime_prefix: str, jobs: int) -> int:
    output = claim_qemu_output(output)
    environment = qemu_environment(output)
    build = output / "build"
    pkgconfig = output / "pkgconfig"
    prepare_wayland_pkgconfig(pkgconfig)
    drm_pc = (ROOT / "pkgconfig/libdrm.pc").read_text(encoding="utf-8")
    drm_pc = re.sub(r"^prefix=.*$", "prefix=" + ROOT.parent.as_posix(), drm_pc, flags=re.M)
    (pkgconfig / "libdrm.pc").write_text(drm_pc, encoding="utf-8")
    local_cross = output / "luna-armv8a-qemu.ini"
    previous_cross = local_cross.read_text(encoding="utf-8") if local_cross.is_file() else None
    cross_file = prepare_cross_file(local_cross, pkgconfig)
    build.mkdir(parents=True, exist_ok=True)
    setup = [sys.executable, "-m", "mesonbuild.mesonmain", "setup", str(build), str(SOURCE),
             "--cross-file", str(cross_file), "--wrap-mode=nodownload",
             *qemu_options(runtime_prefix), *cross_builtin_options(cross_file)]
    if (build / "build.ninja").is_file():
        saved = configparser.ConfigParser(interpolation=None)
        saved.read(build / "meson-private/cmd_line.txt", encoding="utf-8")
        previous = ast.literal_eval(saved.get("properties", "cross_file", fallback="[]"))
        if previous_cross != cross_file.read_text(encoding="utf-8") or [Path(p).resolve() for p in previous] != [cross_file.resolve()]:
            # claim_qemu_output has verified both ownership and resolved paths.
            if build.resolve() != output / "build":
                raise ValueError("refusing to wipe redirected Mesa build directory")
            setup.append("--wipe")
        else:
            setup.append("--reconfigure")
    run_concise(setup, environment, output)
    fix_cross_detected_configuration(build)
    install_target_lexers(build)
    run_concise(["ninja", f"-j{jobs}", "-C", str(build), *QEMU_TARGETS], environment, output)
    package_qemu(output, runtime_prefix)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("panfrost", "qemu"), default="panfrost")
    parser.add_argument("--output-root", type=Path, help="external QEMU output; or set LUNA_MESA_QEMU_OUTPUT")
    parser.add_argument("--runtime-prefix", default="/opt/luna/qemu-graphics", help="isolated guest runtime directory")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args(argv if argv is not None else [])
    if args.profile == "panfrost":
        if args.output_root:
            raise ValueError("output-root is only supported by the isolated qemu profile")
        return build_panfrost()
    output = args.output_root or os.environ.get("LUNA_MESA_QEMU_OUTPUT")
    if not output:
        raise ValueError("qemu profile needs --output-root or LUNA_MESA_QEMU_OUTPUT")
    if args.jobs < 1:
        raise ValueError("jobs must be positive")
    return build_qemu(Path(output), args.runtime_prefix, args.jobs)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
    except (ValueError, FileNotFoundError) as error:
        print(f"mesa build: {error}", file=sys.stderr)
        sys.exit(2)
