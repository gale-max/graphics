"""保存板端测试资产，目录与应用根一致；输出校验清单，不收集日志。"""

import argparse
from ftplib import FTP, error_perm
import hashlib
import json
from pathlib import Path, PurePosixPath


def safe_name(name):
    """FTP 返回的文件名只能是单个路径分量，防止输出目录逃逸。"""
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"非法文件名：{name!r}")
    return name


def capture(ftp, remote, output, rows):
    """遍历指定板端目录，逐文件回读两次并校验 SHA256。"""
    ftp.cwd("/" + remote)
    names = ftp.nlst()
    for entry in names:
        name = safe_name(PurePosixPath(entry).name)
        if name.endswith((".old", ".bak", ".partial", ".tmp", ".log")):
            continue
        child = remote.rstrip("/") + "/" + name
        try:
            ftp.cwd("/" + child)
        except error_perm as error:
            if not str(error).startswith("550"):
                raise
        else:
            capture(ftp, child, output, rows)
            continue
        destination = output / child
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".partial")
        try:
            with temporary.open("wb") as stream:
                ftp.retrbinary("RETR /" + child, stream.write)
            first = hashlib.sha256(temporary.read_bytes()).hexdigest()
            second = hashlib.sha256()
            received = 0

            def update(chunk):
                nonlocal received
                received += len(chunk)
                second.update(chunk)

            ftp.retrbinary("RETR /" + child, update)
            if first != second.hexdigest():
                raise RuntimeError(
                    f"板端文件两次读取不同：{child} "
                    f"first_bytes={temporary.stat().st_size} first_sha256={first} "
                    f"second_bytes={received} second_sha256={second.hexdigest()}")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        rows.append({"path": child, "bytes": destination.stat().st_size,
                     "sha256": first, "source": "board-ftp-readback"})
        if len(rows) % 25 == 0 or destination.stat().st_size >= 1024 * 1024:
            print(f"VERIFIED files={len(rows)} last={child} "
                  f"bytes={destination.stat().st_size}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="192.168.137.11")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "output/rootfs")
    parser.add_argument("--directory", action="append",
                        help="相对于 ftpd 根的目录，可重复指定")
    args = parser.parse_args()
    directories = args.directory or ["graphics", "qt5/bin", "qt5/lib", "qt5/plugins"]
    for directory in directories:
        if not directory or any(part in ("", ".", "..")
                                for part in directory.split("/")):
            parser.error("--directory 必须为不含 . 或 .. 的相对路径")
    rows = []
    complete = False
    try:
        with FTP() as ftp:
            ftp.connect(args.host, timeout=20)
            ftp.login()
            for directory in directories:
                capture(ftp, directory, args.output, rows)
        complete = True
    finally:
        manifest = {"root": "/media/mmcblk1p1", "host": args.host,
                    "complete": complete, "directories": directories,
                    "verification": "two independent FTP reads agree",
                    "files": rows}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        (args.output.parent / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PACKAGE_COMPLETE files={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
