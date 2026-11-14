"""QEMU Mesa must be opt-in and must never reuse the Panfrost output tree."""
import ast
import configparser
import importlib.util
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("mesa_qemu_build", ROOT / "mesa/scripts/build_windows.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_options_and_old_paths_stay_panfrost():
    module = load()
    assert "-Dgallium-drivers=panfrost" in module.OPTIONS
    assert "-Dgbm-backends-path=/media/mmcblk1p1/graphics" in module.OPTIONS
    assert module.BUILD == ROOT / "mesa/build/mesa-25.2.8"
    assert module.HOST_TOOL_DIRECTORY == ROOT / "mesa/build/host-tools"


def test_qemu_profile_uses_actual_mesa_25_driver_names(tmp_path):
    module = load()
    options = module.qemu_options("/opt/luna/qemu-graphics")
    assert "-Dgallium-drivers=virgl,softpipe" in options
    assert "-Dllvm=disabled" in options and "-Ddraw-use-llvm=false" in options
    assert "-Dluna-prebuilt-panfrost=false" in options
    assert "-Dmesa-clc=auto" in options and "-Dprecomp-compiler=auto" in options
    assert "-Dluna-prebuilt-wayland=true" in options and "-Dluna-prebuilt-lexers=true" in options
    assert not any("mmcblk" in option for option in options)
    assert module.QEMU_TARGETS == module.TARGETS
    assert "-Dglx=disabled" in options
    assert len({value.split("=", 1)[0] for value in options}) == len(options)


def test_external_cross_file_and_pkgconfig_are_explicit(tmp_path):
    module = load()
    output = tmp_path / "external"
    cross = module.prepare_cross_file(output / "target.ini", output / "pkgconfig")
    config = configparser.ConfigParser(interpolation=None)
    config.read(cross)
    assert ast.literal_eval(config["properties"]["pkg_config_libdir"]) == (output / "pkgconfig").as_posix()
    assert cross == output / "target.ini"
    assert ast.literal_eval(config["binaries"]["pkg-config"])[-1] == "--dont-define-prefix"


def test_owned_output_root_is_required_and_cannot_be_repository(tmp_path):
    module = load()
    for path in (module.ROOT, module.ROOT / "build", module.ROOT.parent, module.QT_SDK_STAGING):
        with pytest.raises(ValueError):
            module.claim_qemu_output(path)
    unrelated = tmp_path / "unowned"
    (unrelated / "build").mkdir(parents=True)
    with pytest.raises(ValueError):
        module.claim_qemu_output(unrelated)
    owned = tmp_path / "owned"
    module.claim_qemu_output(owned)
    module.claim_qemu_output(owned)
    assert (owned / ".luna-mesa-qemu.json").is_file()


def test_qemu_environment_keeps_caches_and_temp_external(tmp_path):
    module = load()
    env = module.qemu_environment(tmp_path)
    for key in ("TEMP", "TMP", "TMPDIR", "XDG_CACHE_HOME", "CCACHE_DIR",
                "MESON_PACKAGE_CACHE_DIR", "MESA_SHADER_CACHE_DIR", "PKG_CONFIG_PATH"):
        assert Path(env[key]).is_relative_to(tmp_path)
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"


def test_qemu_target_is_separate_and_panfrost_entry_unchanged():
    config = yaml.safe_load((ROOT / "mesa/build.yaml").read_text(encoding="utf-8"))
    assert config["recipes"]["mesa_windows_build"]["steps"][0]["args"] == ["scripts/build_windows.py"]
    assert config["targets"]["mesa-qemu"]["build"]["recipe"] == "mesa_qemu_windows_build"
    args = config["recipes"]["mesa_qemu_windows_build"]["steps"][0]["args"]
    assert args == ["scripts/build_windows.py", "--profile", "qemu"]


def test_qemu_refuses_missing_output_before_build(monkeypatch):
    module = load()
    monkeypatch.delenv("LUNA_MESA_QEMU_OUTPUT", raising=False)
    with pytest.raises(ValueError, match="output"):
        module.main(["--profile", "qemu"])


def test_runtime_copies_are_relocatable_and_hash_the_export(tmp_path):
    module = load()
    compiler = module.TOOLCHAIN / "aarch64-none-linux-gnu-gcc.exe"
    if not compiler.is_file():
        pytest.skip("aarch64 cross compiler unavailable")
    build = tmp_path / "build"
    build.mkdir()
    source = build / "small.c"
    source.write_text("int sample(void) { return 1; }\n")
    library = build / "libgbm.so.1.0.0"
    subprocess.run([str(compiler), "-shared", "-nostdlib", "-fPIC", str(source),
                    "-Wl,-soname,libgbm.so.1", "-Wl,-rpath,/host/build/should/not/escape",
                    "-o", str(library)], check=True, capture_output=True)
    before = library.read_bytes()
    module.QEMU_TARGETS = (library.name,)
    module.package_qemu(tmp_path, "/opt/luna/qemu-graphics")
    artifact = json.loads((tmp_path / "libraries.json").read_text())["artifacts"][0]
    assert artifact["runpath"] in ([], ["$ORIGIN"])
    assert artifact["soname"] == ["libgbm.so.1"]
    assert artifact["needed"] == []
    assert library.read_bytes() == before
    for name in ("libgbm.so.1.0.0", "libgbm.so.1", "libgbm.so"):
        assert hashlib.sha256((tmp_path / "runtime" / name).read_bytes()).hexdigest() == artifact["sha256"]
