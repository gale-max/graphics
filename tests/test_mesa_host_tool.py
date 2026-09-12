#!/usr/bin/env python3
"""验证 Mesa 宿主材料生成与 Windows 独立构建边界。"""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "mesa/scripts/build_host_materials.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_wsl_host_tool", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_host_material_versions_are_pinned():
    module = load_module()

    assert module.MESA_VERSION == "25.2.8"
    assert module.SPIRV_TOOLS_VERSION == "v2024.4"
    assert module.SPIRV_HEADERS_REVISION == \
        "3f17b2af6784bfa2c5aa5dbb8e0e74a607dd8b3b"


def test_regular_windows_build_does_not_invoke_wsl():
    source = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert "run_wsl_host_tool" not in source
    assert "wsl.exe" not in source
    assert "generated/panfrost/25.2.8" in source
    assert "-Dluna-prebuilt-panfrost=true" in source


def test_meson_can_consume_prebuilt_panfrost_materials():
    options = (ROOT / "mesa/upstream/meson.options").read_text(
        encoding="utf-8"
    )
    libpan = (ROOT / "mesa/upstream/src/panfrost/libpan/meson.build").read_text(
        encoding="utf-8"
    )

    assert "luna-prebuilt-panfrost" in options
    assert "get_option('luna-prebuilt-panfrost')" in libpan
    assert "generated/panfrost/25.2.8" in libpan


def test_cross_configuration_drops_host_arc4random_detection():
    source = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert 'replace("#define HAVE_ARC4RANDOM\\n", "")' in source
    assert 'replace("#define HAVE_ARC4RANDOM_BUF\\n", "")' in source


def test_target_compilation_only_serializes_windows_link_jobs():
    source = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert '"-Dbackend_max_links=1"' in source
    assert 'run(["ninja", "-j4"' in source


def test_windows_build_includes_standard_gbm_backend():
    """Mesa 25 的 GBM 前端必须随标准 DRI GBM 后端一起交付。"""
    source = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert '"src/gbm/backends/dri/dri_gbm.so"' in source


def test_windows_build_exports_wayland_display_binding_extension():
    """Qt Wayland compositor 依赖 Mesa 的 EGL_WL_bind_wayland_display。"""
    source = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert "-Dlegacy-wayland=bind-wayland-display" in source


def test_windows_build_uses_luna_runtime_driver_paths():
    """交叉构建不得把 Windows 盘符固化到目标机的 Mesa 搜索路径。"""
    source = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert "-Dgbm-backends-path=/media/mmcblk1p1/graphics" in source
    assert "-Ddri-drivers-path=/media/mmcblk1p1/graphics/dri" in source


def test_target_lexer_materials_are_versioned_and_complete():
    directory = ROOT / "mesa/generated/lexers/25.2.8"
    assert {path.name for path in directory.iterdir()} == {
        "glcpp-lex.c", "glsl_lexer.cpp", "lex.yy.c"
    }


def test_installed_lexers_are_newer_than_host_generator_inputs():
    source = (ROOT / "mesa/scripts/build_windows.py").read_text(
        encoding="utf-8"
    )

    assert "os.utime(output, None)" in source
