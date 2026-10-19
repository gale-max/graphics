"""把 sdktool 创建的 Qt Creator Kit 固化为用户配置。"""

from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def persist_kit(path: Path, kit_id: str) -> None:
    """清除指定 Kit 的临时 SDK 标记，避免 Qt Creator 启动时删除它。"""
    tree = ET.parse(path)
    root = tree.getroot()
    for profile in root.findall("./data/valuemap"):
        values = {node.get("key"): node for node in profile.findall("value")}
        identifier = values.get("PE.Profile.Id")
        if identifier is None or identifier.text != kit_id:
            continue
        for key in ("PE.Profile.SDK", "PE.Profile.AutoDetected"):
            node = values.get(key)
            if node is not None:
                node.text = "false"
        tree.write(path, encoding="utf-8", xml_declaration=True)
        return
    raise ValueError(f"Qt Creator Kit not found: {kit_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--kit-id", required=True)
    args = parser.parse_args()
    persist_kit(args.settings / "profiles.xml", args.kit_id)


if __name__ == "__main__":
    main()
