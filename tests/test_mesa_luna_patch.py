#!/usr/bin/env python3
"""验证 Mesa loader 的 Luna 无 sysfs 平台适配。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_loader_uses_render_node_and_drm_version_without_pci_sysfs():
    source = (ROOT / "mesa/upstream/src/loader/loader.c").read_text(
        encoding="utf-8"
    )

    assert '#ifdef LUNA_GRAPHICS' in source
    assert 'return strdup("/dev/dri/renderD128")' in source
    assert "drmVersionPtr version = drmGetVersion(fd)" in source
    assert "driver = strndup(version->name, version->name_len)" in source


def test_driver_override_precedes_luna_drm_name_detection():
    source = (ROOT / "mesa/upstream/src/loader/loader.c").read_text(
        encoding="utf-8"
    )
    function = source[source.index("loader_get_driver_for_fd(int fd)") :]

    assert function.index('os_get_option("MESA_LOADER_DRIVER_OVERRIDE")') < \
        function.index("loader_get_kernel_driver_name(fd)")


def test_luna_reads_driver_environment_without_uid_gate():
    source = (ROOT / "mesa/upstream/src/loader/loader.c").read_text(
        encoding="utf-8"
    )

    override = source[source.index("loader_get_driver_for_fd(int fd)") :]
    assert override.index("#ifdef LUNA_GRAPHICS") < \
        override.index("if (__normal_user())")
    assert 'os_get_option("MESA_LOADER_DRIVER_OVERRIDE")' in source
    search = source[source.index("loader_open_driver") :]
    assert search.index("#ifdef LUNA_GRAPHICS") < \
        search.index("if (__normal_user() && search_path_vars)")


def test_luna_tiler_heap_does_not_depend_on_gpu_page_fault_growth():
    source = (
        ROOT / "mesa/upstream/src/gallium/drivers/panfrost/pan_device.c"
    ).read_text(
        encoding="utf-8"
    )
    allocation = source[source.index("dev->tiler_heap = panfrost_bo_create") :]
    allocation = allocation[:allocation.index(");") + 2]

    assert "PAN_BO_INVISIBLE" in allocation
    assert "PAN_BO_GROWABLE" not in allocation
    assert "32 * 1024 * 1024" in source
