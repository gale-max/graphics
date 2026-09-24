"""验证 Weston 在 Luna 上使用无 VT 的直接设备启动器。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cross_build_marks_luna_target():
    source = (ROOT / "scripts/compile_products.py").read_text(encoding="utf-8")

    assert "-DLUNA_OS=1" in source


def test_luna_launcher_does_not_require_linux_vt():
    source = (ROOT / "upstream/libweston/launcher-direct.c").read_text(
        encoding="utf-8"
    )

    assert "setup_luna_session" in source
    assert "#ifdef LUNA_OS" in source
    assert "compositor->session_active = true" in source
    assert "launcher->tty = -1" in source


def test_luna_client_launcher_uses_process_spawn_semantics():
    source = (ROOT / "upstream/compositor/main.c").read_text(encoding="utf-8")

    assert "luna_client_spawn" in source
    assert "LUNA_NR_SPAWN" in source
    assert "WAYLAND_SOCKET=" in source
    assert "syscall(LUNA_NR_SPAWN" in source
    assert "#ifdef LUNA_OS" in source
