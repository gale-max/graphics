import ast
import configparser
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    spec = importlib.util.spec_from_file_location("entry_under_test", ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mesa_defaults_follow_checkout(monkeypatch):
    monkeypatch.delenv("LUNA_GRAPHICS_SDK", raising=False)
    module = load("mesa/scripts/build_windows.py")
    assert module.QT_SDK_STAGING == ROOT.parent / "luna-sdk/qt5-5.15.19/staging"


def test_mesa_cross_file_honors_overrides(monkeypatch, tmp_path):
    sdk = tmp_path / "sdk with spaces/staging"
    toolchain = tmp_path / "linux toolchain/bin"
    monkeypatch.setenv("LUNA_GRAPHICS_SDK", str(sdk))
    monkeypatch.setenv("LUNA_GRAPHICS_TOOLCHAIN", str(toolchain))
    module = load("mesa/scripts/build_windows.py")
    module.ROOT = tmp_path / "mesa"
    config = configparser.ConfigParser(interpolation=None)
    config.read(module.prepare_cross_file())
    assert ast.literal_eval(config["binaries"]["c"]) == (toolchain / "aarch64-none-linux-gnu-gcc.exe").as_posix()
    assert "-I" + sdk.as_posix() + "/include" in ast.literal_eval(config["built-in options"]["c_args"])
    assert "D:/luna-sdk" not in str(dict(config["built-in options"]))


def test_catboy_configuration_honors_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("LUNA_GRAPHICS_SDK", str(tmp_path / "sdk/staging"))
    monkeypatch.setenv("LUNA_GRAPHICS_TOOLCHAIN", str(tmp_path / "tools/bin"))
    module = load("scripts/build_component.py")
    config = module.project_configuration("glmark2")
    assert config["platforms"]["armv8a-user"]["toolchain"]["c-compiler"]["path"] == (tmp_path / "tools/bin/aarch64-none-linux-gnu-gcc.exe").as_posix()
    assert (tmp_path / "sdk/staging/include").as_posix() in config["targets"]["glmark2-wayland"]["build"]["includes"]


def test_mesa_changed_cross_file_invalidates_compiler_cache(monkeypatch, tmp_path):
    module = load("mesa/scripts/build_windows.py")
    module.ROOT = tmp_path / "mesa"
    module.BUILD = module.ROOT / "build/mesa-25.2.8"
    module.BUILD.mkdir(parents=True)
    (module.BUILD / "build.ninja").touch()
    cross = module.ROOT / "build/luna-armv8a-local.ini"
    cross.write_text("old compiler configuration", encoding="utf-8")
    private = module.BUILD / "meson-private"
    private.mkdir()
    (private / "cmd_line.txt").write_text(
        "[properties]\ncross_file = " + repr([str(cross)]) + "\n", encoding="utf-8")
    for name in ("prepare_wayland_pkgconfig", "fix_cross_detected_configuration", "install_target_lexers"):
        monkeypatch.setattr(module, name, lambda: None)
    monkeypatch.setattr(module, "prepare_host_tools", lambda env: None)
    commands = []
    monkeypatch.setattr(module, "run", lambda args, env: commands.append(args))
    module.main()
    assert "--wipe" in commands[0]


@pytest.mark.parametrize("relative", [
    "qt5/scripts/build_window_examples.py", "qt5/scripts/deploy_window_examples.py",
    "qt5/sdk-recovery/scripts/package_windows_sdk.py",
])
def test_sdk_entry_help_needs_no_installed_workspace(relative):
    result = subprocess.run([sys.executable, str(ROOT / relative), "--help"], capture_output=True)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def test_sdk_packager_uses_source_qt_root():
    module = load("qt5/sdk-recovery/scripts/package_windows_sdk.py")
    assert (module.ROOT / "mkspecs/luna-armv8a/qmake.conf").is_file()


@pytest.mark.parametrize("relative", [
    "mesa/scripts/build_windows.py", "mesa/toolchains/luna-armv8a-windows.ini",
    "glmark2/build.yaml", "platforms/armv8a-user.yaml",
    "qt5/scripts/build_window_examples.py", "qt5/scripts/deploy_window_examples.py",
    "qt5/sdk-recovery/scripts/package_windows_sdk.py",
    "qt5/sdk-recovery/scripts/register_qtcreator_kit.ps1",
    *[p.relative_to(ROOT).as_posix() for p in (ROOT / "mesa/pkgconfig").glob("*.pc")],
])
def test_active_entries_have_no_deleted_sdk_or_baremetal(relative):
    text = (ROOT / relative).read_text(encoding="utf-8").lower().replace("\\", "/")
    for forbidden in ("d:/luna-sdk", "cortexa", "aarch64-none-elf", "aarch64-elf"):
        assert forbidden not in text, relative
