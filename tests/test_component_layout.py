"""图形用户态资产的目录和构建入口契约。"""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("libdrm", "mesa", "kmscube", "glmark2", "qt5")
ROOT_ENTRIES = {
    "README.md",
    ".gitignore",
    "artifacts",
    "glmark2",
    "kmscube",
    "libdrm",
    "mesa",
    "platforms",
    "qt5",
    "scripts",
    "tests",
}
GENERATED_DIRECTORIES = {"build", "output", "dist", "stage", ".pytest_cache", "__pycache__"}


def test_graphics_root_contains_only_catboy_projects_and_shared_assets():
    entries = {
        path.name for path in ROOT.iterdir()
        if path.name not in {".pytest_cache", "__pycache__"}
    }
    assert entries == ROOT_ENTRIES


def test_intermediate_output_directories_are_ignored():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for name in GENERATED_DIRECTORIES:
        assert name in ignore
    assert "!artifacts/**" in ignore


def test_artifact_manifest_is_generated_by_a_repository_script():
    assert (ROOT / "scripts/package_artifacts.py").is_file()
    assert (ROOT / "artifacts/armv8a-user/manifest.json").is_file()


def test_every_graphics_component_is_a_standalone_catboy_project():
    for name in COMPONENTS:
        component = ROOT / name
        assert component.is_dir(), name
        assert (component / "build.yaml").is_file(), name
        assert (component / "sources.yaml").is_file(), name
        assert (component / "README.md").is_file(), name


def test_windows_build_descriptions_do_not_depend_on_wsl_or_external_workspaces():
    forbidden = ("command: wsl", "/mnt/", "sylixos_workspace")

    for name in COMPONENTS:
        build = (ROOT / name / "build.yaml").read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in build, (name, marker)


def test_component_versions_are_pinned():
    expected = {
        "libdrm": "76a1e97a6e49b7ee6d0bcba36d40927fd18324f9",
        "mesa": "f97d7dcca0e51d7e20ed4342bb5ea8afea7db7fa",
        "kmscube": "60be8e4bd4eb27b5b7c68b4c609304edb87bde8d",
        "glmark2": "42e3d8fe3aa88743ef90348138f643f7b04a9237",
        "qt5": "5.15.19",
    }

    for name, revision in expected.items():
        manifest = yaml.safe_load(
            (ROOT / name / "sources.yaml").read_text(encoding="utf-8")
        )
        assert manifest["revision"] == revision, name


def test_glmark2_builds_the_drm_gles2_flavor():
    build = yaml.safe_load(
        (ROOT / "glmark2" / "build.yaml").read_text(encoding="utf-8")
    )
    target = build["targets"]["glmark2-drm"]['build']

    assert target["artifact"] == "glmark2-drm.elf"
    assert "GLMARK2_USE_DRM=1" in target["defines"]
    assert "GLMARK2_USE_GLESv2=1" in target["defines"]


def test_modetest_is_owned_by_the_libdrm_component():
    build = yaml.safe_load(
        (ROOT / "libdrm" / "build.yaml").read_text(encoding="utf-8")
    )
    target = build["targets"]["modetest"]["build"]

    assert target["artifact"] == "modetest.elf"
    assert target["depends_on"] == ["libdrm"]


def test_mesa_windows_build_uses_versioned_generated_lexers():
    script = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert "def install_target_lexers" in script
    assert 'generated/lexers/25.2.8' in script
    assert "WinGet" not in script
