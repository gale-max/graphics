"""验证 Weston 生成材料不会依赖生成主机。"""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_generator_selects_required_desktop_stack():
    script = (ROOT / "scripts/generate_wsl_materials.py").read_text(
        encoding="utf-8"
    )

    for item in ("desktop-shell", "drm-backend", "gl-renderer"):
        assert item in script


def test_checked_in_generated_files_have_no_absolute_workspace_paths():
    generated = ROOT / "generated"
    if not generated.exists():
        return

    violations = []
    for path in generated.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "D:\\workspace" in text or "/home/surest/" in text:
            violations.append(path.relative_to(ROOT).as_posix())

    assert violations == []


def test_desktop_and_drm_protocol_materials_are_checked_in():
    required = (
        "protocol/xdg-shell-server-protocol.h",
        "protocol/xdg-shell-protocol.c",
        "protocol/weston-desktop-shell-client-protocol.h",
        "protocol/weston-desktop-shell-protocol.c",
        "protocol/linux-dmabuf-unstable-v1-server-protocol.h",
        "protocol/linux-dmabuf-unstable-v1-protocol.c",
        "include/libweston/version.h",
    )

    for relative in required:
        assert (ROOT / "generated" / relative).is_file(), relative


def test_build_target_sources_are_normalized_and_checked_in():
    manifest = json.loads(
        (ROOT / "generated/materials.json").read_text(encoding="utf-8")
    )
    required = (
        "weston-9",
        "weston",
        "desktop-shell",
        "weston-desktop-shell",
        "drm-backend",
        "gl-renderer",
    )

    for target in required:
        sources = manifest["target_sources"][target]
        assert sources
        assert all(not Path(source).is_absolute() for source in sources)
        assert all(source.startswith(("upstream/", "generated/")) for source in sources)
        assert all((ROOT / source).is_file() for source in sources)
