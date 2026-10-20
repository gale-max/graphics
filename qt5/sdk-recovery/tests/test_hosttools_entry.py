"""Exercise the standalone recovery entry without building Qt host tools."""

from pathlib import Path
import os
import runpy
import shutil
import subprocess
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def test_hosttools_help_imports_without_pythonpath(tmp_path):
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-E", str(SCRIPTS / "build_windows_host_tools.py"), "--help"],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--winlibs-bin" in result.stdout
    assert "--stage" in result.stdout
    assert not list(tmp_path.iterdir())


def test_packaged_hosttools_help_includes_import_dependency(tmp_path):
    delivery = runpy.run_path(str(SCRIPTS / "package_windows_sdk.py"))["DELIVERY_SCRIPTS"]
    assert "sdk_paths.py" in delivery
    for name in delivery:
        shutil.copy2(SCRIPTS / name, tmp_path / name)
    result = subprocess.run(
        [sys.executable, "-E", str(tmp_path / "build_windows_host_tools.py"), "--help"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_restored_sdk_paths_preserves_isolated_layout():
    values = runpy.run_path(str(SCRIPTS / "sdk_paths.py"))
    root = Path("build")
    paths = values["SdkPaths"](root)
    assert paths.host_linux == root / "host-linux"
    assert paths.host_windows == root / "host-windows"
    assert paths.target == root / "target-armv8a-luna"
    assert paths.package_root == root / "package/qt5-luna-armv8a-5.15.19"
