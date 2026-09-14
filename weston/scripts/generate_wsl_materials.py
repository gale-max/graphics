"""在 Linux 主机生成 Weston 的配置头、协议代码和目标源文件清单。"""

from argparse import ArgumentParser
from pathlib import Path
import json
import shutil
import subprocess


REQUIRED_TARGETS = (
    "weston-9",
    "weston",
    "desktop-shell",
    "weston-desktop-shell",
    "drm-backend",
    "gl-renderer",
)
REQUIRED_PROTOCOLS = (
    "xdg-shell",
    "weston-desktop-shell",
    "linux-dmabuf-unstable-v1",
    "linux-explicit-synchronization-unstable-v1",
    "presentation-time",
    "viewporter",
)


def run(*command: str, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def relative_files(root: Path, pattern: str) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob(pattern))


def normalize_source(path: str, source: Path, build: Path) -> str | None:
    candidate = Path(path)
    try:
        return "upstream/" + candidate.relative_to(source).as_posix()
    except ValueError:
        pass
    try:
        return "generated/" + candidate.relative_to(build).as_posix()
    except ValueError:
        return None


def read_target_sources(source: Path, build: Path) -> dict[str, list[str]]:
    result = subprocess.run(
        ("meson", "introspect", "--targets", str(build)),
        check=True,
        capture_output=True,
        text=True,
    )
    targets = json.loads(result.stdout)
    selected = {}
    for target in targets:
        name = target["name"]
        if name not in REQUIRED_TARGETS:
            continue
        files = set()
        for group in target.get("target_sources", []):
            for path in group.get("sources", []):
                normalized = normalize_source(path, source, build)
                if normalized is not None:
                    files.add(normalized)
            for path in group.get("generated_sources", []):
                normalized = normalize_source(path, source, build)
                if normalized is not None:
                    files.add(normalized)
        selected[name] = sorted(files)
    missing = sorted(set(REQUIRED_TARGETS) - set(selected))
    if missing:
        raise RuntimeError(f"Weston targets missing from Meson output: {missing}")
    return selected


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    build = args.build.resolve()
    output = args.output.resolve()
    if build.exists():
        shutil.rmtree(build)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    run(
        "meson", "setup", str(build), str(source),
        "-Dbackend-drm=true",
        "-Dbackend-drm-screencast-vaapi=false",
        "-Dbackend-headless=false",
        "-Drenderer-gl=true",
        "-Dshell-desktop=true",
        "-Dshell-fullscreen=false",
        "-Dshell-ivi=false",
        "-Dshell-kiosk=false",
        "-Dxwayland=false",
        "-Dbackend-wayland=false",
        "-Dbackend-x11=false",
        "-Dbackend-rdp=false",
        "-Dbackend-fbdev=false",
        "-Dscreenshare=false",
        "-Dweston-launch=false",
        "-Dremoting=false",
        "-Dpipewire=false",
        "-Dsystemd=false",
        "-Dlauncher-logind=false",
        "-Dcolor-management-lcms=false",
        "-Dcolor-management-colord=false",
        "-Dimage-jpeg=false",
        "-Dimage-webp=false",
        "-Dtools=[]",
        "-Ddemo-clients=false",
        "-Dsimple-clients=[]",
        "-Dwcap-decode=false",
        "-Dtest-junit-xml=false",
        "-Dtest-gl-renderer=false",
    )

    protocol_targets = []
    for protocol in REQUIRED_PROTOCOLS:
        protocol_targets.extend((
            f"protocol/{protocol}-client-protocol.h",
            f"protocol/{protocol}-server-protocol.h",
            f"protocol/{protocol}-protocol.c",
        ))
    run("ninja", "-C", str(build), *protocol_targets)

    target_sources = read_target_sources(source, build)
    generated_sources = sorted({
        path.removeprefix("generated/")
        for sources in target_sources.values()
        for path in sources
        if path.startswith("generated/")
    })
    run("ninja", "-C", str(build), *generated_sources)

    shutil.copy2(build / "config.h", output / "config.h")
    shutil.copytree(build / "protocol", output / "protocol")
    version = output / "include/libweston/version.h"
    version.parent.mkdir(parents=True)
    shutil.copy2(build / "include/libweston/version.h", version)

    manifest = {
        "targets": list(REQUIRED_TARGETS),
        "target_sources": target_sources,
        "generated_c": relative_files(build, "*.c"),
        "generated_headers": relative_files(build, "*.h"),
    }
    (output / "materials.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
