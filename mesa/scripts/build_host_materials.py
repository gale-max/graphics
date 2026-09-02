#!/usr/bin/env python3
"""在 WSL 中构建 Mesa 主机工具并导出 Windows 可复用材料。"""

from pathlib import Path
import argparse
import subprocess


MESA_VERSION = "25.2.8"
SPIRV_TOOLS_VERSION = "v2024.4"
SPIRV_HEADERS_REVISION = "3f17b2af6784bfa2c5aa5dbb8e0e74a607dd8b3b"
ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "generated" / "panfrost" / MESA_VERSION


def wsl(distro: str, command: str, user: str | None = None) -> None:
    arguments = ["wsl.exe", "-d", distro]
    if user:
        arguments.extend(["-u", user])
    arguments.extend(["--", "bash", "-lc", command])
    subprocess.run(arguments, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distro", default="ubuntu20.04")
    parser.add_argument("--user", default="surest")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()

    if args.install:
        wsl(args.distro, "apt-get update && apt-get install -y "
            "build-essential git ninja-build python3-pip clang-15 llvm-15 "
            "libclang-15-dev libclc-15-dev llvm-spirv-15 libzstd-dev",
            "root")

    workspace = str(ROOT).replace("\\", "/").replace("D:/", "/mnt/d/")
    script = f"""
set -euo pipefail
python3 -m pip install --user 'meson==1.7.2' 'cmake==3.31.10'
test -x /home/{args.user}/mesa-{MESA_VERSION}-host-tools/bin/mesa_clc
cd '{workspace}'
python3 scripts/export_panfrost_materials.py \
  --build build/mesa-{MESA_VERSION} \
  --output generated/panfrost/{MESA_VERSION}
"""
    wsl(args.distro, script, args.user)
    print(f"materials exported to {MATERIALS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
