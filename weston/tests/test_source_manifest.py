"""验证 Weston 上游来源固定且可复现。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_pins_official_weston_9_release():
    manifest = (ROOT / "sources.yaml").read_text(encoding="utf-8")

    assert "https://gitlab.freedesktop.org/wayland/weston.git" in manifest
    assert "tag: 9.0.0" in manifest
    assert "revision: 04d3ae265d8d8f84352c8dac21ec40b2fe07e7d2" in manifest


def test_fetch_script_rejects_revision_mismatch_and_removes_git_metadata():
    script = (ROOT / "scripts/fetch_sources.py").read_text(encoding="utf-8")

    assert "expected_revision" in script
    assert "actual_revision != expected_revision" in script
    assert 'source / ".git"' in script
