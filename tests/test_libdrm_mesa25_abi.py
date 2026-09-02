#!/usr/bin/env python3
"""验证 Mesa 25 所需的标准 libdrm GEM 句柄关闭接口。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_libdrm_exports_close_buffer_handle():
    header = (ROOT / "libdrm/upstream/xf86drm.h").read_text(encoding="utf-8")
    source = (ROOT / "libdrm/upstream/xf86drm.c").read_text(encoding="utf-8")

    assert "drmCloseBufferHandle(int fd, uint32_t handle)" in header
    assert "drmCloseBufferHandle(int fd, uint32_t handle)" in source
    assert "DRM_IOCTL_GEM_CLOSE" in source


def test_libdrm_is_locked_to_linux_baseline_version():
    source_manifest = (ROOT / "libdrm/sources.yaml").read_text(
        encoding="utf-8"
    )
    meson = (ROOT / "libdrm/upstream/meson.build").read_text(
        encoding="utf-8"
    )

    assert "tag: libdrm-2.4.125" in source_manifest
    assert "76a1e97a" in source_manifest
    assert "version : '2.4.125'" in meson


def test_luna_platform_device_exposes_primary_and_render_nodes():
    """kmsro 必须能从 KMS 主节点发现 Panfrost render 节点。"""
    source = (ROOT / "libdrm/upstream/xf86drm.c").read_text(
        encoding="utf-8"
    )

    assert "dev->nodes[DRM_NODE_PRIMARY]" in source
    assert "dev->nodes[DRM_NODE_RENDER]" in source
    assert "(1 << DRM_NODE_PRIMARY)" in source
    assert "(1 << DRM_NODE_RENDER)" in source
    assert "drm_public int drmGetDevices2" in source
    assert '"/luna/drm/platform0"' in source
    assert '"/luna/drm/%d"' not in source
