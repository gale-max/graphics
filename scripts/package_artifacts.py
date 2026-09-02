#!/usr/bin/env python3
"""收集图形栈可部署产物，并生成可审计的 SHA256 清单。"""

import hashlib
import json
from pathlib import Path
import shutil

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "armv8a-user"
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


def revision(component: str) -> str:
    manifest = yaml.safe_load((ROOT / component / "sources.yaml").read_text(encoding="utf-8"))
    return str(manifest["revision"])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    entries = []
    for destination_name, source_name in FILES.items():
        source = ROOT / source_name
        if not source.is_file():
            raise FileNotFoundError(source)
        destination = ARTIFACT_ROOT / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        entries.append({
            "path": destination.relative_to(ROOT).as_posix(),
            "size": destination.stat().st_size,
            "sha256": sha256(destination),
        })

    manifest = {
        "architecture": "armv8a-user",
        "sources": {name: revision(name) for name in ("libdrm", "mesa", "kmscube", "glmark2")},
        "artifacts": entries,
    }
    output = ARTIFACT_ROOT / "manifest.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
