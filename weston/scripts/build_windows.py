"""在 Windows 上构建固定版本的 Weston desktop-shell 产品。

该脚本是 Catboy recipe 的实现边界。它先验证源码闭包和 SDK 运行库属于
同一套可部署环境，再调用独立的编译阶段。缺少依赖时必须立即失败，禁止
留下名称正确但不可运行的占位产物。
"""

from pathlib import Path
import json
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "generated/materials.json"
SDK_ROOT = Path("D:/luna-sdk/qt5-5.15.19/staging")
OUTPUT = ROOT / "output"
PRODUCTS = (
    "weston.elf",
    "desktop-shell.so",
    "weston-desktop-shell.elf",
    "drm-backend.so",
    "gl-renderer.so",
    "libexec_weston.so.0",
    "libweston-9.so.0",
    "libweston-desktop-9.so.0",
)
REQUIRED_SDK_LIBRARIES = (
    "libwayland-server.so",
    "libwayland-client.so",
    "libwayland-cursor.so",
    "libEGL.so.1",
    "libGLESv2.so.2",
    "libgbm.so.1",
)


def validate_materials() -> dict:
    manifest = json.loads(MATERIALS.read_text(encoding="utf-8"))
    missing = []
    for sources in manifest["target_sources"].values():
        missing.extend(source for source in sources if not (ROOT / source).is_file())
    if missing:
        raise RuntimeError("Weston source closure is incomplete: " + ", ".join(missing))
    return manifest


def validate_sdk() -> None:
    missing = [
        name for name in REQUIRED_SDK_LIBRARIES
        if not (SDK_ROOT / "lib" / name).is_file()
    ]
    if missing:
        raise RuntimeError("graphics SDK libraries missing: " + ", ".join(missing))


def run_build_stage(manifest: dict) -> None:
    stage = ROOT / "scripts/compile_products.py"
    if not stage.is_file():
        raise RuntimeError(
            "Weston compile stage is not generated; run the dependency build first"
        )
    subprocess.run(
        ("python", str(stage), "--materials", str(MATERIALS), "--output", str(OUTPUT)),
        cwd=ROOT,
        check=True,
    )
    missing = [name for name in PRODUCTS if not (OUTPUT / name).is_file()]
    if missing:
        raise RuntimeError("Weston products missing after build: " + ", ".join(missing))


def main() -> None:
    manifest = validate_materials()
    validate_sdk()
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    run_build_stage(manifest)


if __name__ == "__main__":
    main()
