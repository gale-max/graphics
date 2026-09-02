#!/usr/bin/env python3
"""Check Mesa's Panfrost userspace UAPI against Luna Linux 5.10."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources.yaml"


def _definition(text: str, name: str) -> str:
    match = re.search(rf"^\s*#define\s+{re.escape(name)}.*$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing definition: {name}")
    return " ".join(match.group(0).split())


def _struct(text: str, name: str) -> str:
    match = re.search(
        rf"struct\s+{re.escape(name)}\s*\{{(?P<body>.*?)\}};",
        text,
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"missing struct: {name}")
    return " ".join(match.group(0).split())


def check_headers(linux_header: Path, mesa_header: Path | None = None) -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    uapi = manifest["uapi"]
    linux_text = linux_header.read_text(encoding="utf-8")

    for name in uapi["required_macros"] + uapi["required_ioctls"]:
        _definition(linux_text, name)
    for name in uapi["required_structs"]:
        _struct(linux_text, name)

    if mesa_header is None:
        return

    mesa_text = mesa_header.read_text(encoding="utf-8")
    for name in uapi["required_macros"] + uapi["required_ioctls"]:
        assert _definition(linux_text, name) == _definition(mesa_text, name), name
    for name in uapi["required_structs"]:
        assert _struct(linux_text, name) == _struct(mesa_text, name), name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesa-root", type=Path)
    args = parser.parse_args()
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    uapi = manifest["uapi"]
    linux_header = Path(uapi["linux_5_10_header"])
    mesa_header = None
    if args.mesa_root is not None:
        mesa_header = args.mesa_root / uapi["mesa_header"]
    check_headers(linux_header, mesa_header)
    print("PANFROST_UAPI_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
