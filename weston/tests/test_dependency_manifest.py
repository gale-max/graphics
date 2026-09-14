"""检查 Weston 产品依赖的来源、版本和仓库边界。"""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_desktop_shell_dependencies_are_fixed_to_commits():
    manifest = yaml.safe_load(
        (ROOT / "dependencies.yaml").read_text(encoding="utf-8")
    )["dependencies"]
    required = {
        "pixman", "xkbcommon", "libinput", "libevdev",
        "cairo", "pango", "glib", "libpng",
    }

    assert set(manifest) == required
    for spec in manifest.values():
        assert spec["remote"].startswith("https://")
        assert len(spec["revision"]) == 40
        assert spec["tag"]


def test_dependency_sources_do_not_contain_nested_git_repositories():
    dependencies = ROOT / "dependencies"
    if dependencies.exists():
        assert not list(dependencies.rglob(".git"))
