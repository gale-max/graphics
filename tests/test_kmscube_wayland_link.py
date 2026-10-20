"""Keep Mesa's Wayland dependencies resolvable without weakening ELF checks."""

import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SDK = "../../luna-sdk/qt5-5.15.19/staging"


@pytest.mark.parametrize("override", [False, True])
def test_kmscube_resolves_mesa_wayland_dependencies(monkeypatch, tmp_path, override):
    if override:
        sdk = (tmp_path / "sdk/staging").as_posix()
        monkeypatch.setenv("LUNA_GRAPHICS_SDK", sdk)
        spec = importlib.util.spec_from_file_location("kmscube_wrapper", ROOT / "scripts/build_component.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        config = module.project_configuration("kmscube")
    else:
        sdk = DEFAULT_SDK
        config = yaml.safe_load((ROOT / "kmscube/build.yaml").read_text(encoding="utf-8"))
    flags = config["targets"]["kmscube"]["build"]["linker_flags"].split()
    assert "-L" + sdk + "/lib" in flags
    assert "-Wl,-rpath-link," + sdk + "/lib" in flags
    for library in ("-lwayland-client", "-lwayland-server"):
        assert library in flags
        assert flags.index(library) > flags.index("../mesa/build/mesa-25.2.8/src/egl/libEGL.so.1.0.0")
    assert "-Wl,-rpath,$ORIGIN" in flags
    assert not any("allow-shlib-undefined" in flag or "unresolved-symbols" in flag for flag in flags)
    if override:
        assert DEFAULT_SDK not in " ".join(flags)
