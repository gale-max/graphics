"""Validate Weston wrapper arguments without invoking Catboy or its recipe."""

import importlib.util
from pathlib import Path
import shutil
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("dry_run", [False, True])
def test_weston_wrapper_renders_explicit_platform_and_preserves_recipe(monkeypatch, tmp_path, dry_run):
    spec = importlib.util.spec_from_file_location("component_under_test", ROOT / "scripts/build_component.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "weston").mkdir()
    (tmp_path / "platforms").mkdir()
    shutil.copy2(ROOT / "weston/build.yaml", tmp_path / "weston/build.yaml")
    shutil.copy2(ROOT / "platforms/armv8a-user.yaml", tmp_path / "platforms/armv8a-user.yaml")
    module.ROOT = tmp_path
    toolchain = tmp_path / "explicit-tools/bin"
    monkeypatch.setenv("LUNA_GRAPHICS_TOOLCHAIN", str(toolchain))
    catboy = tmp_path / "catboy.exe"
    arguments = ["build_component.py", "weston", "weston-desktop", "--catboy", str(catboy)]
    if dry_run:
        arguments.append("--dry-run")
    monkeypatch.setattr(sys, "argv", arguments)
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda command, **kwargs: calls.append((command, kwargs)))
    module.main()
    expected = [str(catboy.resolve()), "build", "-f", "build.local.yaml", "weston-desktop"]
    if dry_run:
        expected.append("--dry-run")
    assert calls == [(expected, {"cwd": tmp_path / "weston", "check": True})]
    config = yaml.safe_load((tmp_path / "weston/build.local.yaml").read_text(encoding="utf-8"))
    assert "$include" not in config["platforms"]
    for tool in config["platforms"]["armv8a-user"]["toolchain"].values():
        assert Path(tool["path"]).parent == toolchain
    assert config["targets"]["weston-desktop"]["build"]["recipe"] == "weston_windows_build"
    assert config["recipes"]["weston_windows_build"]["steps"][0]["args"] == ["scripts/build_windows.py"]
