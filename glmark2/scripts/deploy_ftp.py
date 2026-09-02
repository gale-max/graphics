#!/usr/bin/env python3
"""通过 FTP 部署 glmark2 程序和运行数据。"""

import argparse
from ftplib import FTP, error_perm
from pathlib import Path, PurePosixPath


def ensure_directory(ftp: FTP, directory: PurePosixPath) -> None:
    """递归创建 FTP 目录，目录已存在时继续。"""
    current = PurePosixPath("/")
    for part in directory.parts:
        if part == "/":
            continue
        current /= part
        try:
            ftp.mkd(current.as_posix())
        except error_perm as error:
            if not str(error).startswith("550"):
                raise


def upload_file(ftp: FTP, source: Path, destination: PurePosixPath) -> None:
    """上传单个文件并创建父目录。"""
    ensure_directory(ftp, destination.parent)
    with source.open("rb") as stream:
        ftp.storbinary(f"STOR {destination.as_posix()}", stream, blocksize=65536)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()

    with FTP(args.host, timeout=30) as ftp:
        ftp.login()
        upload_file(ftp, args.elf, PurePosixPath("/glmark2-drm.elf"))
        for source in sorted(args.data.rglob("*")):
            if source.is_file():
                relative = source.relative_to(args.data).as_posix()
                upload_file(ftp, source,
                            PurePosixPath("/graphics/data") / relative)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
