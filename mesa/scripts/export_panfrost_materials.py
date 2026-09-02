#!/usr/bin/env python3
"""从已生成的 Mesa 构建目录导出 Panfrost 主机工具产物。"""

from pathlib import Path
import argparse
import shutil


ARCHITECTURES = (4, 5, 6, 7, 9, 10, 12, 13)
NAMES = (
    "libpan_v{arch}.spv", "libpan_v{arch}.cpp", "libpan_v{arch}.h",
    "libpan_shaders_v{arch}.c", "libpan_shaders_v{arch}.h",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.build / "src/panfrost/libpan"
    args.output.mkdir(parents=True, exist_ok=True)

    for arch in ARCHITECTURES:
        for pattern in NAMES:
            name = pattern.format(arch=arch)
            shutil.copy2(source / name, args.output / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
