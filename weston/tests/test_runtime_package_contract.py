"""验证 Weston 产品包含运行时动态库闭包。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_product_packager_includes_runtime_dependencies() -> None:
    source = (ROOT / "scripts" / "compile_products.py").read_text(
        encoding="utf-8"
    )

    for soname in (
        "libinput.so.10",
        "libudev.so.1",
        "libevdev.so.2",
        "libxkbcommon.so.0",
        "libmtdev.so.1",
        "libcairo.so.2",
        "libpixman-1.so.0",
        "libpng16.so.16",
        "libz.so.1",
    ):
        assert soname in source

    assert "RUNTIME_LIBRARIES" in source
    assert "STAGE / source" in source


def test_product_packager_includes_weston_data_and_libinput_quirks() -> None:
    source = (ROOT / "scripts" / "compile_products.py").read_text(
        encoding="utf-8"
    )

    assert '"share/weston"' in source
    assert 'ROOT / "upstream/data"' in source
    assert '"share/libinput"' in source
    assert 'STAGE / "share/libinput"' in source
    assert '"share/X11/xkb"' in source
    assert 'ROOT / "dependencies/xkeyboard-config"' in source
    assert 'ROOT / "generated/xkeyboard-config/rules"' in source


def test_weston_uses_deployed_xkb_data_by_default() -> None:
    source = (ROOT / "upstream" / "compositor" / "main.c").read_text(
        encoding="utf-8"
    )

    assert 'getenv("XKB_CONFIG_ROOT")' in source
    assert '"/graphics/weston/share/X11/xkb"' in source
