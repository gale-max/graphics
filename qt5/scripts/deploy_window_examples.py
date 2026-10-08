"""上传两个窗口示例到 eMMC，并通过 FTP 回读校验内容。"""

import argparse
from ftplib import FTP
from ftplib import error_perm
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.137.11")
    parser.add_argument("--directory", default="qt5/bin")
    parser.add_argument("--sdk", type=Path, default=Path("D:/luna-sdk/qt5-5.15.19"))
    parser.add_argument("--font-directory", type=Path,
                        help="将指定目录中的 TTF 字体部署到 qt5/lib/fonts")
    parser.add_argument("--fonts-only", action="store_true",
                        help="仅部署字体，不覆盖正在运行的应用和插件")
    args = parser.parse_args()
    if args.fonts_only and args.font_directory is None:
        parser.error("--fonts-only 需要 --font-directory")
    ftp = FTP()
    try:
        ftp.connect(args.host, 21, timeout=15)
        ftp.login()
        artifacts = [] if args.fonts_only else [(ROOT / "output/window-examples" / name,
                      args.directory.rstrip("/") + "/" + name)
                     for name in ("analogclock.elf", "calculator.elf")]
        for group in (() if args.fonts_only else
                      ("wayland-shell-integration", "wayland-decoration-client")):
            plugins = sorted((args.sdk / "plugins" / group).glob("*.so"))
            if not plugins:
                raise RuntimeError(f"SDK 缺少 Wayland 插件：{group}")
            directory = "qt5/plugins/" + group
            try:
                ftp.mkd(directory)
            except error_perm:
                ftp.cwd(directory)
                ftp.cwd("/")
            artifacts.extend((file, directory + "/" + file.name) for file in plugins)
        if args.font_directory is not None:
            fonts = sorted(args.font_directory.glob("*.ttf"))
            if not fonts:
                raise RuntimeError(f"字体目录没有 TTF 文件：{args.font_directory}")
            directory = "qt5/lib/fonts"
            try:
                ftp.mkd(directory)
            except error_perm:
                ftp.cwd(directory)
                ftp.cwd("/")
            artifacts.extend((file, directory + "/" + file.name) for file in fonts)
        for artifact, remote in artifacts:
            expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
            with artifact.open("rb") as file:
                ftp.storbinary("STOR " + remote, file)
            received = hashlib.sha256()
            ftp.retrbinary("RETR " + remote, received.update)
            if received.hexdigest() != expected:
                raise RuntimeError(f"板端文件内容不匹配：{remote}")
            print(f"DEPLOY_VERIFIED {remote} bytes={artifact.stat().st_size} sha256={expected}", flush=True)
        ftp.quit()
    finally:
        ftp.close()


if __name__ == "__main__":
    main()
