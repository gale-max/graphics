"""验证 Weston 产品构建入口和产物契约。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_catboy_is_the_single_windows_build_entry():
    build = (ROOT / "build.yaml").read_text(encoding="utf-8")

    assert "project: luna-weston" in build
    assert "python" in build
    assert "scripts/build_windows.py" in build
    assert "wsl" not in build.lower()


def test_windows_builder_declares_complete_desktop_shell_products():
    script = (ROOT / "scripts/build_windows.py").read_text(encoding="utf-8")

    for artifact in (
        "weston.elf",
        "desktop-shell.so",
        "weston-desktop-shell.elf",
        "drm-backend.so",
        "gl-renderer.so",
        "libexec_weston.so.0",
        "libweston-9.so.0",
        "libweston-desktop-9.so.0",
    ):
        assert artifact in script

    assert "generated/materials.json" in script.replace("\\", "/")
    assert "D:/workspace" not in script
    assert "/home/surest" not in script


def test_compile_stage_uses_clean_meson_cross_build_and_transitive_search_paths():
    script = (ROOT / "scripts/compile_products.py").read_text(encoding="utf-8")

    assert "--wipe" in script
    assert "rpath-link" in script
    assert "luna-pregenerated-protocols=true" in script
    assert "backend-drm=true" in script
    assert "renderer-gl=true" in script
    assert ".codex_tmp" not in script


def test_compile_stage_uses_target_runtime_prefix():
    script = (ROOT / "scripts/compile_products.py").read_text(encoding="utf-8")
    meson = (ROOT / "upstream/meson.build").read_text(encoding="utf-8")
    options = (ROOT / "upstream/meson_options.txt").read_text(encoding="utf-8")

    assert 'TARGET_PREFIX = "/graphics/weston"' in script
    assert "-Dluna-runtime-prefix={TARGET_PREFIX}" in script
    assert "prefix = '{STAGE.as_posix()}'" in script
    assert "luna-runtime-prefix" in options
    assert "get_option('luna-runtime-prefix')" in meson


def test_product_paths_are_reproducible_on_target():
    script = (ROOT / "scripts/compile_products.py").read_text(encoding="utf-8")
    main = (ROOT / "upstream/compositor/main.c").read_text(encoding="utf-8")

    assert 'LUNA_LIBEXECDIR "/graphics/weston"' in main
    assert '"%s/%s.elf"' in main
    assert '"clients/weston-keyboard": "weston-keyboard.elf"' in script


def test_runtime_configuration_selects_desktop_shell_and_drm():
    config = (ROOT / "weston.ini").read_text(encoding="utf-8")

    assert "shell=desktop-shell.so" in config
    assert "backend=drm-backend.so" in config
    assert "idle-time=0" in config


def test_luna_entry_prepares_private_xdg_runtime_directory():
    main = (ROOT / "upstream/compositor/main.c").read_text(encoding="utf-8")

    assert "luna_prepare_xdg_runtime_dir" in main
    assert "mkdir(dir, 0700)" in main
    assert "chmod(dir, 0700)" in main
    assert main.index("luna_prepare_xdg_runtime_dir();") < main.index(
        "verify_xdg_runtime_dir();"
    )
    assert 'setenv("LIBINPUT_QUIRKS_DIR",' in main
    assert '"/graphics/weston/share/libinput"' in main
