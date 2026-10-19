"""在 Windows 上配置并构建 Mesa 25.2.8 Panfrost。"""

from pathlib import Path
import os
import ast
import configparser
import shutil
import subprocess
import sys


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

QT_SDK_STAGING = Path(r"D:/luna-sdk/qt5-5.15.19/staging")
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


def prepare_wayland_pkgconfig() -> None:
    """为 Windows 交叉构建生成指向 Luna Qt SDK 的 Wayland 元数据。"""
    source_directory = QT_SDK_STAGING / "lib/pkgconfig"
    if not QT_SDK_STAGING.is_dir():
        raise FileNotFoundError(f"Qt SDK staging not found: {QT_SDK_STAGING}")

    PKGCONFIG_DIRECTORY.mkdir(parents=True, exist_ok=True)
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
        (PKGCONFIG_DIRECTORY / package).write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )


def fix_cross_detected_configuration() -> None:
    """修正只应在目标机上探测、却被 Windows 主机污染的配置。"""
    expat_config = BUILD / "subprojects" / "expat-2.5.0" / "expat_config.h"
    if expat_config.is_file():
        content = expat_config.read_text(encoding="utf-8")
        content = content.replace("#define HAVE_ARC4RANDOM\n", "")
        content = content.replace("#define HAVE_ARC4RANDOM_BUF\n", "")
        expat_config.write_text(content, encoding="utf-8", newline="\n")


def install_target_lexers() -> None:
    """安装仓库内固化的目标 lexer，避免依赖开发者本机的 Flex 路径。"""
    generators = (
        (
            GENERATED_LEXERS / "glcpp-lex.c",
            BUILD / "src/compiler/glsl/glcpp/glcpp-lex.c",
        ),
        (
            GENERATED_LEXERS / "glsl_lexer.cpp",
            BUILD / "src/compiler/glsl/glsl_lexer.cpp",
        ),
        (
            GENERATED_LEXERS / "lex.yy.c",
            BUILD / "src/mesa/program/lex.yy.c",
        ),
    )

    for source, output in generators:
        if not source.is_file():
            raise FileNotFoundError(f"generated lexer not found: {source}")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
        os.utime(output, None)


def prepare_cross_file() -> Path:
    """在构建目录生成本副本的 include/pkgconfig 路径，保留工具链配置。"""
    config = configparser.ConfigParser(interpolation=None)
    config.read(CROSS_FILE, encoding="utf-8")
    config["properties"]["pkg_config_libdir"] = repr((ROOT / "pkgconfig").as_posix())
    compat = (ROOT.parent / "libdrm/include/luna_graphics_compat.h").as_posix()
    for key in ("c_args", "cpp_args"):
        args = ast.literal_eval(config["built-in options"][key])
        config["built-in options"][key] = repr([
            compat if arg.endswith("graphics/libdrm/include/luna_graphics_compat.h") else arg
            for arg in args
        ])
    path = ROOT / "build/luna-armv8a-local.ini"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        config.write(stream)
    return path


def cross_builtin_options(path: Path) -> list[str]:
    config = configparser.ConfigParser(interpolation=None)
    config.read(path, encoding="utf-8")
    return ["-D" + key + "=" + config["built-in options"][key]
            for key in ("c_args", "cpp_args")]


def main() -> int:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PKG_CONFIG_PATH"] = str(ROOT / "pkgconfig")
    prepare_wayland_pkgconfig()
    prepare_host_tools(environment)
    configured = (BUILD / "build.ninja").is_file()
    BUILD.mkdir(parents=True, exist_ok=True)
    cross_file = prepare_cross_file()
    setup = [
        sys.executable, "-m", "mesonbuild.mesonmain", "setup",
        str(BUILD), str(SOURCE), "--cross-file", str(cross_file),
        *OPTIONS, *cross_builtin_options(cross_file),
    ]
    if configured:
        saved = configparser.ConfigParser(interpolation=None)
        saved.read(BUILD / "meson-private/cmd_line.txt", encoding="utf-8")
        previous = ast.literal_eval(saved.get("properties", "cross_file", fallback="[]"))
        if [Path(value).resolve() for value in previous] != [cross_file.resolve()]:
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


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
