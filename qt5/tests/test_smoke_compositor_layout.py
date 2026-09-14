"""验证 Qt smoke compositor 的产品边界和多窗口布局。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_smoke_compositor_has_explicit_product_name():
    project = (ROOT / "examples/qwindow-compositor/qwindow-compositor.pro").read_text(
        encoding="utf-8"
    )

    assert "TARGET = qt-wayland-smoke-compositor" in project


def test_top_level_windows_use_two_column_non_overlapping_layout():
    source = (ROOT / "examples/qwindow-compositor/compositor.cpp").read_text(
        encoding="utf-8"
    )

    assert "topLevelIndex % 2" in source
    assert "topLevelIndex / 2" in source
    assert "SMOKE_WINDOW_MARGIN" in source
    assert "SMOKE_WINDOW_GAP" in source
    assert "topLevelIndex * 72" not in source


def test_smoke_layout_constrains_maximized_and_fullscreen_requests():
    source = (ROOT / "examples/qwindow-compositor/compositor.cpp").read_text(
        encoding="utf-8"
    )

    assert "configureStableTopLevel(top, view)" in source
    assert "top->sendMaximized(m_window->size())" not in source
    assert "top->sendFullscreen(output ? output->geometry().size()" not in source
