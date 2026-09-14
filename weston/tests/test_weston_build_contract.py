"""验证 Weston 产品构建入口和产物契约。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_catboy_is_the_single_windows_build_entry():
    build = (ROOT / "build.yaml").read_text(encoding="utf-8")

    assert "project: luna-weston" in build
    assert "python" in build
    assert "scripts/build_windows.py" in build
    assert "wsl" not in build.lower()


def test_windows_builder_declares_complete_desktop_shell_products():
    script = (ROOT / "scripts/build_windows.py").read_text(encoding="utf-8")

    for artifact in (
        "weston.elf",
        "desktop-shell.so",
        "weston-desktop-shell.elf",
        "drm-backend.so",
        "gl-renderer.so",
    ):
        assert artifact in script

    assert "generated/materials.json" in script.replace("\\", "/")
    assert "D:/workspace" not in script
    assert "/home/surest" not in script


def test_runtime_configuration_selects_desktop_shell_and_drm():
    config = (ROOT / "weston.ini").read_text(encoding="utf-8")

    assert "shell=desktop-shell.so" in config
    assert "backend=drm-backend.so" in config
    assert "idle-time=0" in config
