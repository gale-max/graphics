"""Execute product packaging with Windows text resources and binary controls."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_quirks_are_linux_text_without_changing_sources_or_binaries(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('test_products',ROOT/'scripts/compile_products.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    project=tmp_path/'project';stage=tmp_path/'stage';output=tmp_path/'output'
    for relative in ['upstream/data','generated/xkeyboard-config/rules']:
        (project/relative).mkdir(parents=True)
    for name in ['compat','geometry','keycodes','symbols','types']:
        (project/'dependencies/xkeyboard-config'/name).mkdir(parents=True)
    (stage/'share/libinput').mkdir(parents=True)
    original=b'# original\r\n\r\n[Keyboard]\r\nMatchUdevType=keyboard\r\nAttrKeyboardIntegration=internal\r\n'
    resource=stage/'share/libinput/10-keyboard.quirks';resource.write_bytes(original)
    binary=b'\x7fELF\r\n\x00opaque';(stage/'binary.so').write_bytes(binary)
    monkeypatch.setattr(module,'ROOT',project)
    monkeypatch.setattr(module,'STAGE',stage)
    monkeypatch.setattr(module,'PRODUCTS',{})
    monkeypatch.setattr(module,'RUNTIME_LIBRARIES',{'binary.so':'binary.so'})
    monkeypatch.setattr(module,'sanitize_elf_rpath',lambda path:None)
    module.package_products(output)
    assert (output/'share/libinput/10-keyboard.quirks').read_bytes()==original.replace(b'\r\n',b'\n')
    assert resource.read_bytes()==original
    assert (output/'binary.so').read_bytes()==binary
