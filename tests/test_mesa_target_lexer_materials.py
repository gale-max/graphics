from pathlib import Path
import importlib.util
import configparser

ROOT = Path(__file__).resolve().parents[1]


def test_target_lexers_are_selected_as_prebuilt_sources():
    for relative in ('src/compiler/glsl/glcpp/meson.build',
                     'src/compiler/glsl/meson.build', 'src/mesa/program/meson.build'):
        source = (ROOT / 'mesa/upstream' / relative).read_text(encoding='utf-8')
        assert "get_option('luna-prebuilt-lexers')" in source
        assert 'generated/lexers/25.2.8' in source


def test_local_cross_file_does_not_reference_original_workspace(tmp_path):
    spec = importlib.util.spec_from_file_location('mesa_windows_config', ROOT / 'mesa/scripts/build_windows.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path / 'graphics/mesa'
    module.BUILD = tmp_path / 'build'
    module.BUILD.mkdir()
    path = module.prepare_cross_file()
    assert not path.is_relative_to(module.BUILD)
    config = configparser.ConfigParser(interpolation=None)
    config.read(path, encoding='utf-8')
    assert str(module.ROOT / 'pkgconfig').replace('\\', '/') in config['properties']['pkg_config_libdir']
    for key in ('c_args', 'cpp_args'):
        assert str(module.ROOT.parent / 'libdrm/include/luna_graphics_compat.h').replace('\\', '/') in config['built-in options'][key]
        assert 'D:/workspace/luna-workspace/os/' not in config['built-in options'][key]
    options = module.cross_builtin_options(path)
    assert any(value.startswith('-Dc_args=') for value in options)
    assert any(value.startswith('-Dcpp_args=') for value in options)
