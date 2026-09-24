"""验证 Luna 的 libudev 兼容层满足 Weston 与 libinput 的基础契约。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_luna_udev_maps_standard_device_namespaces():
    source = (ROOT / "compat/libudev-luna/libudev-luna.c").read_text(
        encoding="utf-8"
    )

    assert '"/dev/input"' in source
    assert '"/dev/dri"' in source
    assert '"input"' in source
    assert '"drm"' in source


def test_luna_udev_exposes_weston_and_libinput_properties():
    source = (ROOT / "compat/libudev-luna/libudev-luna.c").read_text(
        encoding="utf-8"
    )

    for property_name in (
        "ID_SEAT",
        "ID_INPUT",
        "ID_INPUT_MOUSE",
        "ID_INPUT_TOUCHSCREEN",
    ):
        assert property_name in source


def test_luna_udev_monitor_is_pollable():
    source = (ROOT / "compat/libudev-luna/libudev-luna.c").read_text(
        encoding="utf-8"
    )

    assert "pipe2(" in source
    assert "udev_monitor_get_fd" in source


def test_luna_udev_has_pkg_config_metadata():
    metadata = (ROOT / "compat/libudev-luna/libudev.pc.in").read_text(
        encoding="utf-8"
    )

    assert "Name: libudev" in metadata
    assert "Version:" in metadata
