# Qt 5

本工程固定使用 Qt 5.15.19。Qt 不通过 Catboy 构建，也不在 Windows 文件系统上
直接编译：源码在 Windows 工作区准备，构建统一在 WSL 的
`/home/surest/nanopc-workspace/graphics/qt5` 中进行，以避免 WSL 访问 Windows
目录时大量小文件操作造成的性能问题。

第一阶段范围为 QtCore、QtGui、QtWidgets、EGLFS/KMS 和 evdev，复用 Luna 已有的
libdrm、Mesa GBM/EGL 和 glibc。QtWayland 与 QtWebEngine 不在基础移植范围内。

SDK 的完整定义、组成、工具链与 sysroot 约束、主机工具（Windows PE 格式）、
目标平台库、SDK 组合方法、Qt Creator 集成与故障排查见
**[`sdk.md`](sdk.md)**（Luna Qt 5 Windows SDK 产品手册）。本文只给出方向和
最短命令序列。

## 关键约定

- 源码复现以 `sources.yaml`、仓库内官方源码归档及其 SHA-256 为准。
  `upstream/qtbase-everywhere-src-*` 是可重新展开的工作树；Luna 平台
  mkspec 的权威模板位于 `mkspecs/luna-armv8a`，构建时由
  `scripts/qt5_build.py` 写入工作树。工作树中的绝对路径不是 SDK 输入。

- 交叉工具链：Arm GNU Toolchain 14.3.Rel1（`aarch64-none-linux-gnu`）。
- 目标 glibc/sysroot 不用工具链自带副本，统一复用 Luna 认可的目标 sysroot；
  `scripts/qt5_build.py` 每次 `configure` 前校验 `features.h`、动态加载器、
  `libc.so.6`、`crt1.o` 的 SHA-256，写入
  `build/qt5-armv8a-linux/target-abi.json`。动态加载器与 libc 禁止拆分替换。
- 构建目录固定 `build/qt5-armv8a-linux`；`upstream/` 存放校验过的源码。
- 板端运行目录固定 `/media/mmcblk1p1/qt5`。

## 快速开始

```powershell
# Windows：下载并校验 qtbase 源码
cd D:\workspace\luna-workspace\os\graphics
python qt5\scripts\prepare.py
```

```bash
# WSL：同步源码（保留增量 build/），并链接 mesa / libdrm
rsync -a --delete --exclude build/ --exclude output/ \
    /mnt/d/workspace/luna-workspace/os/graphics/qt5/ \
    /home/surest/nanopc-workspace/graphics/qt5/
ln -sfn /mnt/d/workspace/luna-workspace/os/graphics/mesa \
    /home/surest/nanopc-workspace/graphics/mesa
ln -sfn /mnt/d/workspace/luna-workspace/os/graphics/libdrm \
    /home/surest/nanopc-workspace/graphics/libdrm

# WSL：逐阶段交叉编译
cd /home/surest/nanopc-workspace/graphics/qt5
python3 scripts/qt5_build.py --stage configure
for s in core gui-eglfs kms widgets smoke widgets-display; do
    python3 scripts/qt5_build.py --stage "$s" --jobs "$(nproc)"
done

# Windows：从同一 sysroot 固化板端 Qt/Wayland 运行时
python qt5\scripts\package_runtime.py `
    --qt-root D:\luna-sdk\qt5-5.15.19 `
    --graphics-root D:\luna-sdk\qt5-5.15.19\staging `
    --runtime-root \\wsl.localhost\ubuntu20.04\home\surest\nanopc-workspace\ubuntu-rootfs `
    --output D:\luna-sdk\qt5-5.15.19\runtime
```

每次 Windows 仓库源码变化后重新执行上面的 `rsync`。不要同步或删除 WSL 侧的
`build/`，否则丢失增量构建结果。

## 验收

- 用 `file` 和目标工具链的 `readelf -d` 确认 `build/qt5-armv8a-linux/lib`
  下的库与 `examples/` 下的 ELF 均为 AArch64，动态依赖只来自目标 sysroot 和
  明确配置的 Luna 图形库。
- `eglfs-smoke.elf` 与 `widgets-display.elf` 在 NanoPC-T4 上的显示、DRM/GBM
  初始化和退出回收为独立实机验收，部署方法见 `sdk.md`。
