"""检查 Weston 使用的 Mesa SDK 元数据可在 Windows 上重建。"""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_graphics_pkgconfig_uses_windows_workspace_paths():
    subprocess.run(
        ("python", str(ROOT / "scripts/prepare_graphics_pkgconfig.py")),
        check=True,
    )

    for name in ("egl", "glesv2", "gbm"):
        content = (ROOT / f"stage/lib/pkgconfig/{name}.pc").read_text(
            encoding="utf-8"
        )
        assert "/home/" not in content
        assert "/mnt/" not in content
        assert "D:/" in content

    assert (ROOT / "stage/include/EGL/egl.h").is_file()
    assert (ROOT / "stage/include/GLES2/gl2.h").is_file()
    assert (ROOT / "stage/lib/libinput.so").is_file()
    assert (ROOT / "stage/lib/libinput.so.10").is_file()
    assert (ROOT / "stage/lib/libevdev.so").is_file()
    assert (ROOT / "stage/lib/libevdev.so.2").is_file()
    assert (ROOT / "stage/lib/libpixman-1.so.0").is_file()
