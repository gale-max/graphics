#!/usr/bin/env python3
"""准备 Catboy 链接 Panfrost DRI 所需的 Meson 产物和响应文件。"""

import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "mesa-25.2.8"
TARGET = "src/gallium/targets/dri/libgallium_dri.so"
RESPONSE = BUILD / "panfrost_dri.rsp"


def run(*args):
    return subprocess.run(args, cwd=BUILD, check=True, text=True,
                          capture_output=True).stdout


def windows_path(argument):
    workspace = "/mnt/d/workspace/"
    if argument.startswith(workspace):
        return "D:/workspace/" + argument[len(workspace):]
    if workspace in argument:
        return argument.replace(workspace, "D:/workspace/")
    return argument


def main():
    commands = run("ninja", "-t", "commands", TARGET).splitlines()
    link_args = shlex.split(commands[-1])
    ninja_targets = set(run("ninja", "-t", "targets", "all").split("\n"))
    ninja_targets = {line.split(":", 1)[0] for line in ninja_targets if line}

    inputs = []
    response = []
    skip_next = False
    for argument in link_args[1:]:
        if skip_next:
            skip_next = False
            continue
        if argument == "-o":
            skip_next = True
            continue
        if argument in ("-shared", "-fPIC"):
            continue
        if argument in ninja_targets and argument != TARGET:
            inputs.append(argument)
        if not argument.startswith("-") and not Path(argument).is_absolute():
            argument = f"build/mesa-25.2.8/{argument}"
        response.append(windows_path(argument))

    subprocess.run(["ninja", "-j", "8", *inputs], cwd=BUILD, check=True)
    RESPONSE.write_text("\n".join(shlex.quote(arg) for arg in response) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"prepared {len(inputs)} link inputs: {RESPONSE}")


if __name__ == "__main__":
    main()
