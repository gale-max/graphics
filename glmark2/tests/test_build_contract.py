#!/usr/bin/env python3
"""检查 Luna glmark2 Catboy 工程的目标边界。"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_YAML = (ROOT / "build.yaml").read_text(encoding="utf-8")
SCENE_SOURCES = (ROOT / "scene-sources.yaml").read_text(encoding="utf-8")
CONFIG_HEADER = (ROOT / "include" / "luna_glmark_config.h").read_text(
    encoding="utf-8"
)


class Glmark2BuildContractTest(unittest.TestCase):
    """确保构建使用可见输出的 DRM/KMS 后端。"""

    def test_uses_explicit_drm_gles2_sources(self):
        self.assertIn("upstream/src/native-state-drm.cpp", BUILD_YAML)
        self.assertIn("upstream/src/gl-state-egl.cpp", SCENE_SOURCES)
        self.assertIn("upstream/src/glad/src/gles2.c", BUILD_YAML)
        self.assertIn("GLMARK2_USE_DRM=1", BUILD_YAML)
        self.assertNotIn("GLMARK2_USE_GBM=1", BUILD_YAML)
        self.assertNotIn("upstream/src/*.cpp", BUILD_YAML)

    def test_excludes_unrelated_platform_sources(self):
        forbidden = (
            "android.cpp",
            "native-state-gbm.cpp",
            "native-state-win32.cpp",
            "native-state-x11.cpp",
            "gl-state-glx.cpp",
            "gl-state-wgl.cpp",
        )
        for source in forbidden:
            self.assertNotIn(source, BUILD_YAML)

        drm_target = BUILD_YAML.split("  glmark2-wayland:", 1)[0]
        self.assertNotIn("native-state-wayland.cpp", drm_target)

    def test_wayland_target_is_separate_from_drm_backend(self):
        wayland_target = BUILD_YAML.split("  glmark2-wayland:", 1)[1]

        self.assertIn("native-state-wayland.cpp", wayland_target)
        self.assertNotIn("native-state-drm.cpp", wayland_target)
        self.assertIn("GLMARK2_USE_WAYLAND=1", wayland_target)

    def test_uses_bundled_image_libraries(self):
        for target in ("glmark2-zlib", "glmark2-png", "glmark2-jpeg"):
            self.assertIn(target + ":", BUILD_YAML)
        self.assertNotIn("-lpng", BUILD_YAML)
        self.assertNotIn("-ljpeg", BUILD_YAML)

    def test_zlib_does_not_compile_gzip_file_api(self):
        for source in ("gzlib.c", "gzread.c", "gzwrite.c", "gzclose.c"):
            self.assertNotIn(source, BUILD_YAML)

    def test_default_data_path_is_quoted_emmc_path(self):
        self.assertIn(
            '#define GLMARK_DATA_PATH "/media/mmcblk1p1/graphics/data"',
            CONFIG_HEADER,
        )
        self.assertIn("cpp: -include luna_glmark_config.h", BUILD_YAML)

    def test_luna_drm_backend_uses_card0_without_udev(self):
        drm = (ROOT / "upstream/src/native-state-drm.cpp").read_text(
            encoding="utf-8"
        )

        self.assertIn('open("/dev/dri/card0", O_RDWR)', drm)
        self.assertNotIn("#include <libudev.h>", drm)

    def test_links_mesa_runtime_dependencies(self):
        self.assertIn("libglapi.a", BUILD_YAML)
        self.assertNotIn("libglapi.so", BUILD_YAML)
        self.assertIn("libgallium-25.2.8.so", BUILD_YAML)
        self.assertIn("libexpat.so.1.8.10", BUILD_YAML)


if __name__ == "__main__":
    unittest.main()
