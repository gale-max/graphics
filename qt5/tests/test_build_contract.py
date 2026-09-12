from pathlib import Path
import importlib.util
import shutil

ROOT = Path(__file__).resolve().parents[1]


def load_driver():
    path = ROOT / "scripts" / "qt5_build.py"
    spec = importlib.util.spec_from_file_location("qt5_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_qt5_is_built_directly_on_linux():
    assert not (ROOT / "build.yaml").exists()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "/home/surest/nanopc-workspace/graphics/qt5" in readme
    assert "不通过 Catboy 构建" in readme


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
    assert "-lgbm -l:libgallium-25.2.8.so -lexpat" in text


def test_qt5_driver_keeps_outputs_under_linux_build_directory():
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
    assert '"libgallium-25.2.8.so"' in text
    assert '"libexpat.so.1"' in text
    assert "LIBDRM_UAPI_INCLUDE" in text
    assert '"gbm.pc"' in text
    assert '"-pkg-config"' in text
    assert '"-no-pch"' in text
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


def test_qt5_uses_windows_target_sysroot_and_checks_abi():
    text = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    assert "REFERENCE_SYSROOT" in text
    assert "verify_target_abi()" in text
    assert 'Path("usr/include/features.h")' in text
    assert 'Path("lib64/libc.so.6")' in text
    assert 'Path("lib/ld-linux-aarch64.so.1")' in text
    assert 'Path("usr/lib64/crt1.o")' in text
    assert 'BUILD / "target-abi.json"' in text


def test_qt5_stages_use_qtbase_make_targets():
    text = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    build_body = text.split("def build(stage: str, jobs: int)", 1)[1]
    assert "materialize_spec()" in build_body.split("def build_smoke", 1)[0]
    assert "if destination.read_text(encoding=\"utf-8\") == content" in text
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
    project = (app / "eglfs-smoke.pro").read_text(encoding="utf-8")
    assert "QT += gui\n" in project
    assert "opengl" not in project
    source = (app / "main.cpp").read_text(encoding="utf-8")
    assert "QOpenGLWindow" in source
    assert "QOpenGLFunctions" in source

    text = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    assert 'elif args.stage == "smoke"' in text


def test_qt5_has_widgets_display_application():
    app = ROOT / "examples" / "widgets-display"
    assert (app / "widgets-display.pro").is_file()
    project = (app / "widgets-display.pro").read_text(encoding="utf-8")
    assert "QT += widgets\n" in project

    source = (app / "main.cpp").read_text(encoding="utf-8")
    assert "QLineEdit" in source
    assert "setReadOnly(true)" in source
    assert "QCheckBox" in source
    assert "setChecked(true)" in source
    assert "showFullScreen()" in source

    build = (ROOT / "scripts" / "qt5_build.py").read_text(encoding="utf-8")
    assert '"widgets"' in build
    assert '"widgets-display"' in build
