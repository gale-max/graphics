"""为 Weston 生成 Luna Mesa SDK 的 pkg-config 元数据。"""

from pathlib import Path
import os
import shutil


ROOT = Path(__file__).resolve().parents[1]
GRAPHICS_ROOT = ROOT.parent
SDK_ROOT = Path(os.environ.get("LUNA_GRAPHICS_SDK", str(ROOT.parents[1] / "luna-sdk/qt5-5.15.19/staging")))
OUTPUT = ROOT / "stage/lib/pkgconfig"


def copy_shared_library_aliases(source: Path, aliases: tuple[str, ...]) -> None:
    """为 Windows stage 生成 ELF 构建所需的 SONAME 别名。"""
    if not source.is_file():
        return

    for alias in aliases:
        shutil.copy2(source, source.parent / alias)


def write_pc(name: str, description: str, libraries: str, include: Path) -> None:
    content = (
        f"libdir={(SDK_ROOT / 'lib').as_posix()}\n"
        f"includedir={include.as_posix()}\n\n"
        f"Name: {name}\n"
        f"Description: {description}\n"
        "Version: 25.2.8\n"
        f"Libs: -L${{libdir}} {libraries}\n"
        "Cflags: -I${includedir}\n"
    )
    (OUTPUT / f"{name}.pc").write_text(content, encoding="utf-8")


def main() -> None:
    mesa_include = GRAPHICS_ROOT / "mesa/upstream/include"
    gbm_include = GRAPHICS_ROOT / "mesa/upstream/src/gbm/main"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for directory in ("EGL", "GLES", "GLES2", "GLES3", "KHR"):
        shutil.copytree(
            mesa_include / directory,
            ROOT / "stage/include" / directory,
            dirs_exist_ok=True,
        )

    copy_shared_library_aliases(
        ROOT / "stage/lib/libinput.so.10.13.0",
        ("libinput.so.10", "libinput.so"),
    )
    copy_shared_library_aliases(
        ROOT / "stage/lib/libevdev.so.2.3.0",
        ("libevdev.so.2", "libevdev.so"),
    )
    copy_shared_library_aliases(
        ROOT / "stage/lib/libpixman-1.so.0.40.0",
        ("libpixman-1.so.0", "libpixman-1.so"),
    )

    write_pc("egl", "Luna Mesa EGL", "-lEGL", mesa_include)
    write_pc("glesv2", "Luna Mesa OpenGL ES 2", "-lGLESv2", mesa_include)
    write_pc("gbm", "Luna Mesa GBM", "-lgbm -ldrm", gbm_include)


if __name__ == "__main__":
    main()
