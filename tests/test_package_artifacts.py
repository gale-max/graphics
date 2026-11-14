"""External delivery packaging validates inputs and records copied hashes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import pytest

PATH = Path(__file__).resolve().parents[1] / 'scripts/package_artifacts.py'
spec = importlib.util.spec_from_file_location('graphics_package', PATH)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


@pytest.fixture
def source(tmp_path):
    root = tmp_path / 'graphics'
    root.mkdir()
    subprocess.run(['git','init',str(root)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(root),'-c','user.name=test','-c','user.email=test@example.invalid',
                    'commit','--allow-empty','-m','fixture'],check=True,capture_output=True)
    elf = bytearray(64)
    elf[:6] = b'\x7fELF\x02\x01'
    elf[18:20] = (183).to_bytes(2,'little')
    for path in package.FILES.values():
        p = root/path
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(b'!<arch>\n' if p.suffix == '.a' else elf)
    for name in ('mesa','kmscube','glmark2','libdrm'):
        (root/name/'sources.yaml').write_text('revision: fixture-pinned-revision\n')
    return root


def test_complete_external_package(source, tmp_path):
    out = tmp_path/'delivery'
    manifest = json.loads(package.package(source,out).read_text())
    assert manifest['schema_version'] == 2
    assert len(manifest['artifacts']) == len(package.FILES)
    assert manifest['packaging_checkout']['dirty']
    for item in manifest['artifacts']:
        original = source/item['source']
        exported = out/item['path']
        assert exported.read_bytes() == original.read_bytes()
        assert hashlib.sha256(exported.read_bytes()).hexdigest() == item['sha256']
        assert exported.stat().st_size == item['size']
    assert not (source/'artifacts').exists()
    with pytest.raises(ValueError,match='absent or empty'):
        package.package(source,out)


def test_rejects_output_inside_or_above_source(source, tmp_path):
    for out in (source,source/'artifacts',tmp_path):
        with pytest.raises(ValueError,match='outside and disjoint'):
            package.package(source,out)


@pytest.mark.parametrize('failure', ['missing','wrong_arch','wrong_archive'])
def test_invalid_inputs_do_not_create_partial_delivery(source,tmp_path,failure):
    name = 'libdrm/libdrm.a' if failure == 'wrong_archive' else 'kmscube/kmscube.elf'
    p = source/package.FILES[name]
    if failure == 'missing':
        p.unlink()
    else:
        p.write_bytes(b'not a target binary')
    out = tmp_path/'delivery'
    with pytest.raises((ValueError,FileNotFoundError)):
        package.package(source,out)
    assert not out.exists()


def test_thin_archive_is_self_contained_after_export(source,tmp_path):
    ar = shutil.which('ar')
    assert ar, 'GNU ar is required for the thin archive delivery test'
    archive = source/package.FILES['mesa/libglapi.a']
    archive.unlink()
    member = archive.parent/'member.o'
    # A tiny ELF header is sufficient for ar's opaque member storage.
    member.write_bytes((source/package.FILES['kmscube/kmscube.elf']).read_bytes())
    subprocess.run([ar,'qcT',str(archive),str(member)],check=True,capture_output=True)
    out=tmp_path/'delivery'
    with pytest.raises(ValueError,match='require --ar'):
        package.package(source,out)
    assert not out.exists()
    manifest=json.loads(package.package(source,out,ar).read_text())
    item=next(entry for entry in manifest['artifacts'] if entry['path']=='mesa/libglapi.a')
    assert item['format']=='ar' and len(item['archive_members'])==1
    expected=member.read_bytes()
    member.unlink()
    copied=out/item['path']
    assert copied.read_bytes().startswith(b'!<arch>\n')
    assert subprocess.check_output([ar,'p',str(copied),'member.o'])==expected
