from pathlib import Path
import importlib.util
import shutil

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_driver():
    path = ROOT / "scripts" / "qt5_build.py"
    spec = importlib.util.spec_from_file_location("qt5_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_build_file():
    return yaml.safe_load((ROOT / "build.yaml").read_text(encoding="utf-8"))


def test_qt5_declares_split_catboy_targets():
    data = load_build_file()
    targets = data["targets"]

    assert set(targets) == {
        "qt5-prepare",
        "qt5-configure",
        "qt5-core",
        "qt5-gui-eglfs",
        "qt5-kms",
        "qt5-eglfs-smoke",
    }
    assert targets["qt5-configure"]["build"]["recipe"] == "qt5_configure"
    assert targets["qt5-core"]["build"]["recipe"] == "qt5_core"
    assert targets["qt5-gui-eglfs"]["build"]["recipe"] == "qt5_gui_eglfs"
    assert targets["qt5-kms"]["build"]["recipe"] == "qt5_kms"
    assert targets["qt5-eglfs-smoke"]["build"]["recipe"] == "qt5_eglfs_smoke"


def test_qt5_recipes_use_the_windows_python_driver():
    data = load_build_file()
    recipes = data["recipes"]

    for name in ("qt5_configure", "qt5_core", "qt5_gui_eglfs", "qt5_kms"):
        step = recipes[name]["steps"][0]
        assert step["command"] == "python"
        assert step["args"][0] == "scripts/qt5_build.py"
        assert "--stage" in step["args"]


def test_qt5_driver_and_arm_mkspec_are_tracked():
    assert (ROOT / "scripts" / "qt5_build.py").is_file()
    spec = ROOT / "mkspecs" / "luna-armv8a" / "qmake.conf"
    assert spec.is_file()
    text = spec.read_text(encoding="utf-8")
    assert "QMAKE_CXX" in text
    assert "aarch64-none-linux-gnu" in text
    assert "QMAKE_INCDIR_OPENGL_ES2" in text
    assert "QMAKE_SYSROOT" in text
    assert "QMAKE_PLATFORM         = linux unix posix" in text
    assert "-lgbm -lglapi -lexpat" in text


def test_qt5_driver_keeps_outputs_under_catboy_build_directory():
    text = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    assert 'BUILD = ROOT / "build"' in text
    assert 'SOURCE = ROOT / "upstream"' in text


def test_qt5_driver_stages_graphics_libraries_and_passes_search_paths():
    text = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    assert 'STAGING = BUILD / "staging"' in text
    assert "stage_graphics_libraries()" in text
    assert '"-I"' in text
    assert '"-L"' in text
    assert '"-opengl"' in text
    assert '"es2"' in text
    assert '"libEGL.so"' in text
    assert '"libGLESv2.so"' in text
    assert '"libgbm.so"' in text
    assert '"libgbm.so.1"' in text
    assert '"libglapi.so.0"' in text
    assert '"libexpat.so.1"' in text
    assert "LIBDRM_UAPI_INCLUDE" in text
    assert '"gbm.pc"' in text
    assert '"-pkg-config"' in text
    assert '"-no-pch"' not in text
    assert 'env["PKG_CONFIG_PATH"]' in text
    assert 'env["PKG_CONFIG"]' in text
    assert 'STAGING_BIN / "pkg-config.exe"' in text
    assert "stage_pkg_config()" in text


def test_qt5_configure_discards_stale_cache_and_protects_unix_prefixes():
    text = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    assert "reset_configure_state()" in text
    assert '(BUILD / "bin").mkdir(parents=True, exist_ok=True)' in text
    assert '(BUILD / "qmake").mkdir(parents=True, exist_ok=True)' in text
    assert 'env["MSYS2_ARG_CONV_EXCL"] = "/usr"' in text


def test_qt5_stages_use_qtbase_make_targets():
    text = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    assert '"core": "sub-corelib"' in text
    assert '"gui-eglfs": "sub-gui"' in text
    assert '"sub-platformsupport"' in text
    assert '"sub-eglfs"' in text
    assert "module-qtcore" not in text
    assert "module-qtgui" not in text
    assert '[make, "-j1", "sub-src-qmake_all"]' in text
    assert 'for host_target in ("sub-moc", "sub-rcc", "sub-uic")' in text
    assert 'env["PATH"] = os.pathsep.join' in text


def test_luna_platformdefs_inherits_complete_linux_definitions():
    text = (ROOT / "mkspecs" / "luna-armv8a" / "qplatformdefs.h").read_text(
        encoding="utf-8"
    )
    assert 'linux-g++/qplatformdefs.h' in text
    assert 'common/posix/qplatformdefs.h' not in text


def test_qt5_configure_cleanup_retries_transient_windows_lock(tmp_path, monkeypatch):
    driver = load_driver()
    build = tmp_path / "qt5-armv8a"
    build.mkdir()
    (build / "cache").write_text("stale", encoding="utf-8")
    monkeypatch.setattr(driver, "BUILD", build)

    real_rmtree = shutil.rmtree
    calls = []

    def flaky_rmtree(path):
        calls.append(path)
        if len(calls) == 1:
            raise PermissionError("transient sharing violation")
        real_rmtree(path)

    monkeypatch.setattr(driver.shutil, "rmtree", flaky_rmtree)
    monkeypatch.setattr(driver.time, "sleep", lambda _: None)
    driver.reset_configure_state()

    assert len(calls) == 2
    assert not build.exists()


def test_qt5_has_armv8_eglfs_smoke_application():
    app = ROOT / "examples" / "eglfs-smoke"
    assert (app / "eglfs-smoke.pro").is_file()
    source = (app / "main.cpp").read_text(encoding="utf-8")
    assert "QOpenGLWindow" in source
    assert "QOpenGLFunctions" in source

    data = load_build_file()
    step = data["recipes"]["qt5_eglfs_smoke"]["steps"][0]
    assert step["args"] == ["scripts/qt5_build.py", "--stage", "smoke"]
