#!/usr/bin/env python3
"""收集图形栈可部署产物，并生成可审计的 SHA256 清单。"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "mesa/libgbm.so.1.0.0": "mesa/build/mesa-25.2.8/src/gbm/libgbm.so.1.0.0",
    "mesa/libEGL.so.1.0.0": "mesa/build/mesa-25.2.8/src/egl/libEGL.so.1.0.0",
    "mesa/libGLESv2.so.2.0.0": "mesa/build/mesa-25.2.8/src/mapi/es2api/libGLESv2.so.2.0.0",
    "mesa/libgallium-25.2.8.so": "mesa/build/mesa-25.2.8/src/gallium/targets/dri/libgallium-25.2.8.so",
    "mesa/dri_gbm.so": "mesa/build/mesa-25.2.8/src/gbm/backends/dri/dri_gbm.so",
    "mesa/libglapi.a": "mesa/build/mesa-25.2.8/src/mapi/shared-glapi/libglapi.a",
    "mesa/libexpat.so.1.8.10": "mesa/build/mesa-25.2.8/subprojects/expat-2.5.0/libexpat.so.1.8.10",
    "glmark2/glmark2-drm.elf": "glmark2/build/glmark2-drm/armv8a-user/glmark2-drm.elf",
    "libdrm/libdrm.a": "libdrm/build/libdrm/armv8a-user/libdrm.a",
    "libdrm/modetest.elf": "libdrm/build/modetest/armv8a-user/modetest.elf",
    "kmscube/kmscube.elf": "kmscube/build/kmscube/armv8a-user/kmscube.elf",
}


def revision(root: Path, component: str) -> str:
    manifest = yaml.safe_load((root / component / "sources.yaml").read_text(encoding="utf-8"))
    return str(manifest["revision"])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_binary(path: Path) -> str:
    with path.open('rb') as stream:
        header = stream.read(64)
    if path.suffix == '.a':
        if header[:8] == b'!<thin>\n':
            return 'thin-ar'
        if header[:8] != b'!<arch>\n':
            raise ValueError(f'invalid archive: {path}')
        return 'ar'
    if (len(header) != 64 or header[:6] != b'\x7fELF\x02\x01' or
            int.from_bytes(header[18:20], 'little') != 183):
        raise ValueError(f'expected aarch64 ELF64 little-endian: {path}')
    return 'elf64-aarch64'


def package(root: Path, output: Path, ar: str | None = None) -> Path:
    root, output = root.resolve(), output.resolve()
    if output == root or root in output.parents or output in root.parents:
        raise ValueError('output must be outside and disjoint from the source tree')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('output must be absent or empty; use a new delivery directory')
    # Preflight the complete set before publishing any partial package.
    inputs = [(name, root / path, validate_binary(root / path)) for name, path in FILES.items()]
    members = {}
    for _, source, kind in inputs:
        if kind != 'thin-ar':
            continue
        if not ar:
            raise ValueError('thin archives require --ar to create a self-contained archive')
        names = subprocess.check_output([ar, 't', str(source)], text=True).splitlines()
        objects = [Path(name) if Path(name).is_absolute() else source.parent/name for name in names]
        if not objects:
            raise ValueError(f'empty thin archive: {source}')
        for obj in objects:
            validate_binary(obj)
        members[source] = [(obj, sha256(obj)) for obj in objects]
    sources = {name: revision(root, name) for name in ('libdrm','mesa','kmscube','glmark2')}
    head = subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'], text=True).strip()
    status = subprocess.check_output(['git','-C',str(root),'status','--porcelain=v1','--untracked-files=normal'])
    entries = []
    for destination_name, source, kind in inputs:
        source_hash = sha256(source)
        destination = output / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if kind == 'thin-ar':
            subprocess.run([ar, 'qcs', str(destination), *[str(obj) for obj, _ in members[source]]], check=True)
            if validate_binary(destination) != 'ar':
                raise RuntimeError(f'archive materialization failed: {source}')
            if any(sha256(obj) != digest for obj, digest in members[source]):
                raise RuntimeError(f'thin archive member changed while packaging: {source}')
        else:
            shutil.copy2(source, destination)
        if (kind != 'thin-ar' and sha256(destination) != source_hash) or sha256(source) != source_hash:
            raise RuntimeError(f'artifact changed while packaging: {source}')
        entries.append({
            "path": destination.relative_to(output).as_posix(),
            "source": source.relative_to(root).as_posix(),
            "format": 'ar' if kind == 'thin-ar' else kind,
            "source_sha256": source_hash,
            "archive_members": [{"source": str(obj), "sha256": digest} for obj, digest in members.get(source, [])],
            "size": destination.stat().st_size,
            "sha256": sha256(destination),
        })

    manifest = {
        "schema_version": 2,
        "architecture": "armv8a-user",
        "sources": sources,
        "packaging_checkout": {"head": head, "dirty": bool(status),
                               "status_sha256": hashlib.sha256(status).hexdigest()},
        "validation": "binary format and copy hashes only; build provenance and runtime acceptance require separate evidence",
        "artifacts": entries,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--ar', help='target GNU ar for materializing thin archives')
    args = parser.parse_args()
    print(package(args.source_root, args.output_root, args.ar))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
