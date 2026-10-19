import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'scripts/export_sdk_copy.py'


def module():
    spec = importlib.util.spec_from_file_location('sdk_copy', SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_longest_prefix_and_windows_paths():
    rewrite = module().rewrite
    pairs = {'D:/old': 'E:/new', 'D:/old/build/staging': 'E:/new/staging'}
    assert rewrite('x=D:/old/build/staging/lib y=D:\\old\\bin', pairs) == 'x=E:/new/staging/lib y=E:/new/bin'


def test_boundary_does_not_corrupt_other_root():
    assert module().rewrite('D:/old-other/lib D:/old/lib', {'D:/old': 'E:/new'}) == 'D:/old-other/lib E:/new/lib'


def test_refuse_existing_destination(tmp_path):
    import pytest
    with pytest.raises(FileExistsError):
        module().require_new_destination(tmp_path)
