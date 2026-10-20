"""在 Windows 上交叉构建 Weston desktop-shell 产品。"""

from argparse import ArgumentParser
import os
from pathlib import Path
import shutil
import subprocess

from sanitize_elf_rpath import sanitize_elf_rpath


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[2]
TOOLCHAIN = Path(os.environ.get("LUNA_GRAPHICS_TOOLCHAIN",
                               str(WORKSPACE / "tools/toolchains/aarch64-none-linux-gnu/bin")))
SDK_ROOT = Path(os.environ.get("LUNA_GRAPHICS_SDK", str(ROOT.parents[1] / "luna-sdk/qt5-5.15.19/staging")))
STAGE = ROOT / "stage"
BUILD = ROOT / "build/weston-armv8-product"
CROSS_FILE = ROOT / "build/armv8-luna.ini"
TARGET_PREFIX = "/graphics/weston"

MESON_OPTIONS = (
    "-Dluna-pregenerated-protocols=true",
    f"-Dluna-runtime-prefix={TARGET_PREFIX}",
    "-Dbackend-drm=true",
    "-Drenderer-gl=true",
    "-Dshell-desktop=true",
    "-Dbackend-drm-screencast-vaapi=false",
    "-Dbackend-fbdev=false",
    "-Dbackend-headless=false",
    "-Dbackend-rdp=false",
    "-Dbackend-wayland=false",
    "-Dbackend-x11=false",
    "-Dcolor-management-colord=false",
    "-Dcolor-management-lcms=false",
    "-Ddemo-clients=false",
    "-Ddoc=false",
    "-Dimage-jpeg=false",
    "-Dimage-webp=false",
    "-Dlauncher-logind=false",
    "-Dpipewire=false",
    "-Dremoting=false",
    "-Dscreenshare=false",
    "-Dshell-fullscreen=false",
    "-Dshell-ivi=false",
    "-Dshell-kiosk=false",
    "-Dsimple-clients=[]",
    "-Dsystemd=false",
    "-Dtools=[]",
    "-Dweston-launch=false",
    "-Dxwayland=false",
)

PRODUCTS = {
    "compositor/weston": "weston.elf",
    "desktop-shell/desktop-shell.so": "desktop-shell.so",
    "clients/weston-desktop-shell": "weston-desktop-shell.elf",
    "clients/weston-keyboard": "weston-keyboard.elf",
    "libweston/backend-drm/drm-backend.so": "drm-backend.so",
    "libweston/renderer-gl/gl-renderer.so": "gl-renderer.so",
    "compositor/libexec_weston.so.0.0.0": "libexec_weston.so.0",
    "libweston/libweston-9.so.0.0.0": "libweston-9.so.0",
    "libweston-desktop/libweston-desktop-9.so.0.0.0": "libweston-desktop-9.so.0",
}

RUNTIME_LIBRARIES = {
    "lib/libinput.so.10": "libinput.so.10",
    "lib/libudev.so.1.7.5": "libudev.so.1",
    "lib/libevdev.so.2": "libevdev.so.2",
    "lib/libxkbcommon.so.0.0.0": "libxkbcommon.so.0",
    "lib/libmtdev.so.1.0.0": "libmtdev.so.1",
    "lib/libcairo.so.2": "libcairo.so.2",
    "lib/libpixman-1.so.0": "libpixman-1.so.0",
    "lib/libpng16.so.16": "libpng16.so.16",
    "lib/libz.so.1": "libz.so.1",
}


def executable(name: str) -> str:
    """解析构建工具，缺失时直接给出明确错误。"""
    result = shutil.which(name)
    if result is None:
        raise RuntimeError(f"required build tool not found: {name}")
    return result


def write_cross_file() -> None:
    """生成只引用当前工作空间和 SDK 的 ARMv8 交叉配置。"""
    compiler = lambda name: (TOOLCHAIN / f"aarch64-none-linux-gnu-{name}.exe").as_posix()
    pkg_config = executable("pkgconf").replace("\\", "/")
    search = (
        f"-Wl,-rpath-link,{(STAGE / 'lib').as_posix()},"
        f"-rpath-link,{(SDK_ROOT / 'lib').as_posix()}"
    )
    content = f"""[binaries]
c = '{compiler('gcc')}'
cpp = '{compiler('g++')}'
ar = '{compiler('ar')}'
strip = '{compiler('strip')}'
pkg-config = '{pkg_config}'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'armv8-a'
endian = 'little'

[properties]
needs_exe_wrapper = true

[built-in options]
c_args = ['-march=armv8-a', '-fPIC', '-DLUNA_OS=1']
cpp_args = ['-march=armv8-a', '-fPIC', '-DLUNA_OS=1']
c_link_args = ['{search}']
cpp_link_args = ['{search}']
default_library = 'shared'
buildtype = 'release'
prefix = '{STAGE.as_posix()}'
libdir = 'lib'
"""
    CROSS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CROSS_FILE.write_text(content, encoding="utf-8")


def run_build() -> None:
    """从干净 Meson 配置构建完整产品集合。"""
    subprocess.run(("python", str(ROOT / "scripts/prepare_graphics_pkgconfig.py")), check=True)
    write_cross_file()
    environment = os.environ.copy()
    environment["PKG_CONFIG_LIBDIR"] = os.pathsep.join(
        (str(STAGE / "lib/pkgconfig"), str(SDK_ROOT / "lib/pkgconfig"))
    )
    setup = [executable("meson"), "setup"]
    if (BUILD / "meson-private/coredata.dat").is_file():
        setup.append("--wipe")
    setup.extend((str(BUILD), str(ROOT / "upstream"), "--cross-file", str(CROSS_FILE)))
    setup.extend(MESON_OPTIONS)
    subprocess.run(setup, env=environment, check=True)
    subprocess.run((executable("ninja"), "-C", str(BUILD), "-j", "4"), env=environment, check=True)


def package_products(output: Path) -> None:
    """按 Luna 图形资产约定输出稳定的产品名称。"""
    output.mkdir(parents=True, exist_ok=True)
    for source, target in PRODUCTS.items():
        artifact = BUILD / source
        if not artifact.is_file():
            raise RuntimeError(f"Weston product was not built: {artifact}")
        shutil.copy2(artifact, output / target)
    for source, target in RUNTIME_LIBRARIES.items():
        artifact = STAGE / source
        if not artifact.is_file():
            raise RuntimeError(f"Weston runtime library is missing: {artifact}")
        shutil.copy2(artifact, output / target)
    shutil.copytree(
        ROOT / "upstream/data",
        output / "share/weston",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("meson.build", "COPYING", "*.svg"),
    )
    shutil.copytree(
        STAGE / "share/libinput",
        output / "share/libinput",
        dirs_exist_ok=True,
    )
    xkb_source = ROOT / "dependencies/xkeyboard-config"
    xkb_output = output / "share/X11/xkb"
    for directory in ("compat", "geometry", "keycodes", "symbols", "types"):
        shutil.copytree(
            xkb_source / directory,
            xkb_output / directory,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("meson.build"),
        )
    shutil.copytree(
        ROOT / "generated/xkeyboard-config/rules",
        xkb_output / "rules",
        dirs_exist_ok=True,
    )
    for config in ("weston.ini", "weston-grid.ini"):
        shutil.copy2(ROOT / config, output / config)
    for product in output.iterdir():
        if product.is_file():
            sanitize_elf_rpath(product)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--materials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if not arguments.materials.is_file():
        raise RuntimeError(f"Weston materials manifest missing: {arguments.materials}")
    run_build()
    package_products(arguments.output)


if __name__ == "__main__":
    main()
