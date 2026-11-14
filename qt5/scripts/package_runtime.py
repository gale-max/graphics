#!/usr/bin/env python3
"""从同一 sysroot 组装 Luna Qt/Wayland 目标机运行时。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


WAYLAND_LIBRARIES = (
    "libwayland-client.so.0",
    "libwayland-server.so.0",
    "libwayland-cursor.so.0",
    "libwayland-egl.so.1",
)

RUNTIME_LIBRARIES = (
    ("usr/lib/aarch64-linux-gnu/libc.so.6", "lib/libc.so.6"),
    ("usr/lib/aarch64-linux-gnu/libm.so.6", "lib/libm.so.6"),
    ("usr/lib/aarch64-linux-gnu/libdl.so.2", "lib/libdl.so.2"),
    ("usr/lib/aarch64-linux-gnu/libpthread.so.0", "lib/libpthread.so.0"),
    ("usr/lib/aarch64-linux-gnu/librt.so.1", "lib/librt.so.1"),
    ("usr/lib/aarch64-linux-gnu/libgcc_s.so.1", "lib/libgcc_s.so.1"),
    ("usr/lib/aarch64-linux-gnu/libstdc++.so.6", "lib/libstdc++.so.6"),
)


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def resolve_file(path: Path) -> Path:
    """解析 WSL UNC 下无法由 Windows 跟随的 Linux SONAME 链接。"""
    if path.is_file() and path.stat().st_size > 128:
        return path
    matches = sorted(
        item for item in path.parent.glob(f"{path.name}.*")
        if item.is_file() and item.stat().st_size > 128
    )
    if not matches:
        raise FileNotFoundError(path)
    return matches[-1]


def copy_file(source: Path, destination: Path) -> None:
    source = resolve_file(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_gconv(source: Path, output: Path) -> None:
    """Copy the base charset configuration and its complete module set.

    glibc opens these modules dynamically, so DT_NEEDED alone misses them.
    Keep them from the same target libc; optional extra charset configs are
    intentionally not copied without their own dependency closure.
    """
    source, output = source.resolve(), output.resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('gconv output must be separate from its source')
    config = source / 'gconv-modules'
    modules = set()
    for line in config.read_text(encoding='utf8').splitlines():
        fields = line.split('#', 1)[0].split()
        if not fields or fields[0] != 'module':
            continue
        if len(fields) < 4 or not re.fullmatch(r'[A-Za-z0-9_.-]+', fields[3]):
            raise ValueError('invalid gconv module name')
        modules.add(fields[3] + '.so')
    inputs = [config] + [source / name for name in sorted(modules)]
    for path in inputs:
        require_file(path)
        if path.suffix == '.so':
            with path.open('rb') as stream:
                header = stream.read(20)
            if header[:6] != b'\x7fELF\x02\x01' or int.from_bytes(header[18:20], 'little') != 183:
                raise ValueError(f'expected target aarch64 gconv module: {path}')
    output.mkdir(parents=True, exist_ok=True)
    for path in inputs:
        destination = output / path.name
        shutil.copyfile(path, destination)
        if sha256(path) != sha256(destination):
            raise RuntimeError(f'gconv copy hash mismatch: {path}')


def package_runtime(qt_root: Path, graphics_root: Path,
                    runtime_root: Path, output: Path, gconv_root: Path | None = None) -> None:
    qt_root = qt_root.resolve()
    graphics_root = graphics_root.resolve()
    runtime_root = runtime_root.resolve()
    output = output.resolve()

    require_file(qt_root / "lib/libQt5Core.so.5")
    require_file(qt_root / "plugins/platforms/libqwayland-generic.so")
    require_file(
        qt_root / "plugins/wayland-decoration-client/libbradient.so"
    )
    for library in WAYLAND_LIBRARIES:
        require_file(graphics_root / "lib" / library)

    output.mkdir(parents=True, exist_ok=True)
    for directory in ("lib", "plugins", "fonts", "examples"):
        source = qt_root / directory
        if source.is_dir():
            shutil.copytree(source, output / directory, dirs_exist_ok=True)

    shutil.copytree(graphics_root / "lib", output / "lib",
                    dirs_exist_ok=True)

    copy_file(runtime_root / "usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1",
              output / "bin/ld-linux-aarch64.so.1")
    for source, destination in RUNTIME_LIBRARIES:
        copy_file(runtime_root / source, output / destination)

    if gconv_root is not None:
        package_gconv(gconv_root, output / 'lib/gconv')

    files = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        if path.name == "runtime-manifest.json":
            continue
        files.append({
            "path": path.relative_to(output).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256(path),
        })

    manifest = {
        "qt_root": str(qt_root),
        "graphics_root": str(graphics_root),
        "runtime_root": str(runtime_root),
        "gconv_root": str(gconv_root.resolve()) if gconv_root is not None else None,
        "files": files,
    }
    (output / "runtime-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qt-root", type=Path, required=True)
    parser.add_argument("--graphics-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gconv-root", type=Path,
                        help="base gconv modules from the same target libc")
    args = parser.parse_args()
    package_runtime(args.qt_root, args.graphics_root,
                    args.runtime_root, args.output, args.gconv_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
