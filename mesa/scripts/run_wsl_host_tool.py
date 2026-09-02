#!/usr/bin/env python3
"""在 Windows 构建中调用 WSL 内的 Mesa 宿主生成工具。"""

import re
import subprocess
import sys


WSL_DISTRIBUTION = "ubuntu20.04"
WSL_TOOL_DIRECTORY = "/home/surest/mesa-25.2.8-host-tools/bin"
WSL_LIBRARY_PATH = "/home/surest/toolchain-prefix/lib"
WINDOWS_PATH = re.compile(
    r"^(?P<prefix>.*?)(?P<drive>[A-Za-z]):[\\/](?P<tail>.*)$"
)


def to_wsl_argument(argument: str) -> str:
    """将参数中的 Windows 绝对路径转换为 WSL 挂载路径。"""
    match = WINDOWS_PATH.match(argument)
    if match is None:
        return argument
    tail = match.group("tail").replace("\\", "/")
    return (
        f"{match.group('prefix')}/mnt/{match.group('drive').lower()}/{tail}"
    )


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("缺少 Mesa 宿主工具名称")
    tool = sys.argv[1]
    arguments = [to_wsl_argument(argument) for argument in sys.argv[2:]]
    command = [
        "wsl.exe", "-d", WSL_DISTRIBUTION, "--exec", "env",
        f"LD_LIBRARY_PATH={WSL_LIBRARY_PATH}",
        f"{WSL_TOOL_DIRECTORY}/{tool}", *arguments,
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
