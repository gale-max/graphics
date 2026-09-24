"""验证 Weston 打包阶段按 ELF 结构清理主机构建路径。"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "scripts/sanitize_elf_rpath.py"


def load_tool():
    spec = spec_from_file_location("sanitize_elf_rpath", TOOL_PATH)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_test_elf(path: Path) -> None:
    shstr = b"\x00.shstrtab\x00.dynstr\x00.dynamic\x00"
    old_path = b"D:/host/sdk/lib:D:/host/stage/lib"
    dynstr = b"\x00" + old_path + b"\x00"
    dynamic = struct.pack("<QQQQ", 15, 1, 0, 0)
    shstr_offset = 64
    dynstr_offset = shstr_offset + len(shstr)
    dynamic_offset = dynstr_offset + len(dynstr)
    section_offset = (dynamic_offset + len(dynamic) + 7) & ~7
    header = bytearray(64)
    header[:16] = b"\x7fELF\x02\x01\x01" + b"\x00" * 9
    struct.pack_into("<HHIQQQIHHHHHH", header, 16,
                     3, 183, 1, 0, 0, section_offset, 0,
                     64, 0, 0, 64, 4, 1)
    sections = bytearray(64 * 4)
    struct.pack_into("<IIQQQQIIQQ", sections, 64,
                     1, 3, 0, 0, shstr_offset, len(shstr), 0, 0, 1, 0)
    struct.pack_into("<IIQQQQIIQQ", sections, 128,
                     11, 3, 0, 0, dynstr_offset, len(dynstr), 0, 0, 1, 0)
    struct.pack_into("<IIQQQQIIQQ", sections, 192,
                     19, 6, 0, 0, dynamic_offset, len(dynamic), 2, 0, 8, 16)
    blob = header + shstr + dynstr + dynamic
    blob.extend(b"\x00" * (section_offset - len(blob)))
    blob.extend(sections)
    path.write_bytes(blob)


def test_rewriter_replaces_host_rpath_with_origin(tmp_path: Path) -> None:
    elf = tmp_path / "product.elf"
    make_test_elf(elf)

    tool = load_tool()
    assert tool.sanitize_elf_rpath(elf) == 1
    data = elf.read_bytes()
    assert b"$ORIGIN\x00" in data
    assert b"D:/host/sdk" not in data


def test_product_packager_sanitizes_every_elf_product() -> None:
    source = (ROOT / "scripts/compile_products.py").read_text(encoding="utf-8")

    assert "sanitize_elf_rpath" in source
    assert "for product in output.iterdir()" in source
