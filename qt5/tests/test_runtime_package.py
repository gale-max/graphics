import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package_runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location("package_runtime", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_runtime_package_uses_one_sysroot_and_includes_wayland(tmp_path):
    module = load_module()
    qt_root = tmp_path / "qt"
    graphics_root = tmp_path / "graphics"
    runtime_root = tmp_path / "rootfs"
    output = tmp_path / "runtime"

    write(qt_root / "lib/libQt5Core.so.5", b"qt")
    write(qt_root / "plugins/platforms/libqwayland-generic.so", b"plugin")
    write(graphics_root / "lib/libwayland-client.so.0", b"client")
    write(graphics_root / "lib/libwayland-server.so.0", b"server")
    write(graphics_root / "lib/libwayland-cursor.so.0", b"cursor")
    write(graphics_root / "lib/libwayland-egl.so.1", b"egl")
    write(runtime_root / "usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1",
          b"loader-data" * 16)
    for source, _ in module.RUNTIME_LIBRARIES:
        write(runtime_root / source, source.encode() * 8)

    module.package_runtime(qt_root, graphics_root, runtime_root, output)

    assert (output / "bin/ld-linux-aarch64.so.1").read_bytes() == \
        b"loader-data" * 16
    assert (output / "lib/libc.so.6").read_bytes() == \
        b"usr/lib/aarch64-linux-gnu/libc.so.6" * 8
    assert (output / "lib/libstdc++.so.6").is_file()
    assert (output / "lib/libwayland-cursor.so.0").read_bytes() == b"cursor"
    manifest = json.loads((output / "runtime-manifest.json").read_text(
        encoding="utf-8"
    ))
    assert manifest["qt_root"] == str(qt_root.resolve())
    assert manifest["graphics_root"] == str(graphics_root.resolve())
    assert manifest["runtime_root"] == str(runtime_root.resolve())
    assert any(item["path"] == "bin/ld-linux-aarch64.so.1"
               for item in manifest["files"])


def test_runtime_package_resolves_wsl_style_soname_file(tmp_path):
    module = load_module()
    link = tmp_path / "libstdc++.so.6"
    write(link, b"libstdc++.so.6.0.33")
    write(tmp_path / "libstdc++.so.6.0.33", b"runtime" * 32)

    assert module.resolve_file(link).name == "libstdc++.so.6.0.33"
