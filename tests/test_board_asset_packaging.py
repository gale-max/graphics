"""分发目录边界与双读校验测试，不依赖板卡。"""

import importlib.util
from pathlib import Path
from ftplib import error_perm

import pytest

SPEC = importlib.util.spec_from_file_location(
    "board_packaging", Path(__file__).parents[1] / "scripts/package_board_assets.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeFTP:
    def __init__(self, corrupt=False):
        self.reads = 0
        self.corrupt = corrupt

    def cwd(self, path):
        if path != "/graphics":
            raise error_perm("550 Not a directory")

    def nlst(self):
        return ["glmark2-wayland.elf"]

    def retrbinary(self, command, callback):
        assert command == "RETR /graphics/glmark2-wayland.elf"
        self.reads += 1
        callback(b"changed" if self.corrupt and self.reads == 2 else b"ELF")


@pytest.mark.parametrize("name", ["", ".", "..", "../evil", "a/b", "a\\b"])
def test_filename_rejects_escape(name):
    with pytest.raises(ValueError):
        MODULE.safe_name(name)


def test_capture_preserves_deployment_path(tmp_path):
    rows = []
    ftp = FakeFTP()
    MODULE.capture(ftp, "graphics", tmp_path, rows)
    assert (tmp_path / "graphics/glmark2-wayland.elf").read_bytes() == b"ELF"
    assert ftp.reads == 2
    assert rows[0]["path"] == "graphics/glmark2-wayland.elf"


def test_changed_file_does_not_publish(tmp_path):
    with pytest.raises(RuntimeError):
        MODULE.capture(FakeFTP(True), "graphics", tmp_path, [])
    assert not list(tmp_path.rglob("*.elf"))
    assert not list(tmp_path.rglob("*.partial"))
