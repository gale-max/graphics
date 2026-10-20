"""Render checkout-local Catboy inputs without modifying shared configuration."""

import argparse
import os
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]


def project_configuration(component):
    sdk = Path(os.environ.get("LUNA_GRAPHICS_SDK", str(ROOT.parent / "luna-sdk/qt5-5.15.19/staging")))
    toolchain = Path(os.environ.get("LUNA_GRAPHICS_TOOLCHAIN", str(ROOT.parents[1] / "tools/toolchains/aarch64-none-linux-gnu/bin")))
    config = yaml.safe_load((ROOT / component / "build.yaml").read_text(encoding="utf-8"))
    platform = yaml.safe_load((ROOT / "platforms/armv8a-user.yaml").read_text(encoding="utf-8"))
    for tool in platform["armv8a-user"]["toolchain"].values():
        tool["path"] = (toolchain / Path(tool["path"]).name).as_posix()
    config["platforms"] = platform
    # Expand only our SDK token; Catboy still owns source-list includes and $ORIGIN.
    def expand(value):
        if isinstance(value, str):
            return value.replace("../../luna-sdk/qt5-5.15.19/staging", sdk.as_posix())
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            return {key: expand(item) for key, item in value.items()}
        return value
    return expand(config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("component", choices=("libdrm", "kmscube", "glmark2", "weston"))
    parser.add_argument("targets", nargs="+")
    parser.add_argument("--catboy", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = project_configuration(args.component)
    project = ROOT / args.component
    path = project / "build.local.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    command = [str(args.catboy.resolve()), "build", "-f", path.name, *args.targets]
    if args.dry_run:
        command.append("--dry-run")
    subprocess.run(command, cwd=project, check=True)


if __name__ == "__main__":
    main()
