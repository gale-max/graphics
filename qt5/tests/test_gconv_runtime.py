"""Charset modules are runtime dlopen edges, not ELF DT_NEEDED entries."""
import importlib.util
from pathlib import Path
import pytest

PATH=Path(__file__).resolve().parents[1]/'scripts/package_runtime.py'
spec=importlib.util.spec_from_file_location('qt_runtime_gconv',PATH)
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def fixture(tmp_path):
    source=tmp_path/'source'
    source.mkdir()
    (source/'gconv-modules').write_text('module UTF-16// INTERNAL UTF-16 1\nmodule INTERNAL UTF-16// UTF-16 1\n')
    header=bytearray(64);header[:6]=b'\x7fELF\x02\x01';header[18:20]=(183).to_bytes(2,'little')
    (source/'UTF-16.so').write_bytes(header)
    (source/'unused.so').write_bytes(b'not selected')
    return source


def test_base_modules_copied_once_with_config(tmp_path):
    source=fixture(tmp_path);output=tmp_path/'output'
    runtime.package_gconv(source,output)
    assert {p.name for p in output.iterdir()}=={'UTF-16.so','gconv-modules'}
    for p in output.iterdir():assert p.read_bytes()==(source/p.name).read_bytes()


@pytest.mark.parametrize('error',['missing','host','escape'])
def test_invalid_charset_inputs_fail_before_copy(tmp_path,error):
    source=fixture(tmp_path);output=tmp_path/'output'
    if error=='missing':(source/'UTF-16.so').unlink()
    if error=='host':(source/'UTF-16.so').write_bytes(b'host binary')
    if error=='escape':(source/'gconv-modules').write_text('module UTF-16// INTERNAL ../outside 1\n')
    with pytest.raises((FileNotFoundError,ValueError)):
        runtime.package_gconv(source,output)
    assert not output.exists()


def test_source_is_protected(tmp_path):
    source=fixture(tmp_path)
    with pytest.raises(ValueError):runtime.package_gconv(source,source/'output')
