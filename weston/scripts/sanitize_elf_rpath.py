"""将 ELF64 动态搜索路径改写为可部署的相对路径。"""

from argparse import ArgumentParser
from pathlib import Path
import struct


ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
SECTION_HEADER = struct.Struct("<IIQQQQIIQQ")
DYNAMIC_ENTRY = struct.Struct("<QQ")
SHT_DYNAMIC = 6
DT_RPATH = 15
DT_RUNPATH = 29


def sanitize_elf_rpath(path: Path, runtime_path: bytes = b"$ORIGIN") -> int:
    """原位改写 ELF64 的 RPATH/RUNPATH，返回修改的动态项数量。"""
    data = bytearray(path.read_bytes())
    if len(data) < ELF_HEADER.size or data[:6] != b"\x7fELF\x02\x01":
        return 0

    header = ELF_HEADER.unpack_from(data)
    section_offset = header[6]
    section_entry_size = header[11]
    section_count = header[12]
    if section_entry_size < SECTION_HEADER.size:
        raise ValueError(f"invalid ELF section entry size: {path}")

    sections = []
    for index in range(section_count):
        offset = section_offset + index * section_entry_size
        if offset + SECTION_HEADER.size > len(data):
            raise ValueError(f"truncated ELF section table: {path}")
        sections.append(SECTION_HEADER.unpack_from(data, offset))

    changed = 0
    for section in sections:
        section_type = section[1]
        if section_type != SHT_DYNAMIC:
            continue
        dynamic_offset = section[4]
        dynamic_size = section[5]
        string_section_index = section[6]
        entry_size = section[9] or DYNAMIC_ENTRY.size
        if entry_size < DYNAMIC_ENTRY.size or string_section_index >= len(sections):
            raise ValueError(f"invalid ELF dynamic section: {path}")
        string_section = sections[string_section_index]
        string_offset = string_section[4]
        string_size = string_section[5]

        for entry_offset in range(dynamic_offset,
                                  dynamic_offset + dynamic_size,
                                  entry_size):
            if entry_offset + DYNAMIC_ENTRY.size > len(data):
                raise ValueError(f"truncated ELF dynamic table: {path}")
            tag, value = DYNAMIC_ENTRY.unpack_from(data, entry_offset)
            if tag not in (DT_RPATH, DT_RUNPATH):
                continue
            start = string_offset + value
            limit = string_offset + string_size
            if start >= limit or limit > len(data):
                raise ValueError(f"invalid ELF dynamic string offset: {path}")
            end = data.find(0, start, limit)
            if end < 0 or len(runtime_path) > end - start:
                raise ValueError(f"ELF runtime path slot is too small: {path}")
            data[start:end] = runtime_path + b"\x00" * (end - start - len(runtime_path))
            changed += 1

    if changed:
        path.write_bytes(data)
    return changed


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    arguments = parser.parse_args()
    for path in arguments.paths:
        sanitize_elf_rpath(path)


if __name__ == "__main__":
    main()
