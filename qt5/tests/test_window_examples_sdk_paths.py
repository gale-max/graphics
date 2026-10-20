"""Mock qmake output so no compiler or installed SDK is modified."""

import importlib.util
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build_window_examples.py"
ORIGINAL = "D:/workspace/luna-workspace/os"


@pytest.mark.parametrize("unmapped_source", [False, True])
def test_generated_makefile_preserves_explicit_sdk_and_relocates_sources(monkeypatch, tmp_path, unmapped_source):
    spec = importlib.util.spec_from_file_location("window_examples_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path / "checkout/os/graphics/qt5"
    module.GRAPHICS = module.ROOT.parent
    sdk = Path(ORIGINAL + "/luna-sdk/qt5-5.15.19")
    make = tmp_path / "make.exe"
    make.touch()
    qmake = sdk / "bin/qmake.exe"
    original_is_file = Path.is_file
    monkeypatch.setattr(Path, "is_file", lambda path: path == qmake or original_is_file(path))
    for name in ("analogclock", "calculator"):
        source = module.ROOT / "upstream/qtbase-everywhere-src-5.15.19/examples/widgets/widgets" / name
        source.mkdir(parents=True)
        (source / (name + ".pro")).touch()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--sdk", str(sdk), "--make", str(make)])
    checked = []

    def run(arguments, cwd, **kwargs):
        if Path(arguments[0]) == qmake:
            (cwd / "Makefile").write_text(
                f"QMAKE = {qmake.as_posix()}\n"
                f"INCPATH = -I{sdk.as_posix()}/include\n"
                f"LIBS = -L{ORIGINAL}/graphics/qt5/build/qt5-armv8a/staging/lib\n"
                f"SOURCES = {ORIGINAL}/graphics/qt5/upstream/example.cpp\n"
                + (f"OLD_SOURCE = {ORIGINAL}/components/old.cpp\n" if unmapped_source else ""),
                encoding="utf-8",
            )
        else:
            text = (cwd / "Makefile").read_text(encoding="utf-8")
            assert f"QMAKE = {qmake.as_posix()}" in text
            assert f"-I{sdk.as_posix()}/include" in text
            assert f"-L{sdk.as_posix()}/staging/lib" in text
            assert ORIGINAL + "/graphics/" not in text
            assert module.ROOT.as_posix() + "/upstream/example.cpp" in text
            checked.append(arguments)
            (cwd / (cwd.name + ".elf")).write_bytes(b"mock executable")

    monkeypatch.setattr(module.subprocess, "run", run)
    if unmapped_source:
        with pytest.raises(RuntimeError, match="Makefile"):
            module.main()
        assert not checked
        return
    module.main()
    assert len(checked) == 4
