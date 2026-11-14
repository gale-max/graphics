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

Windows SDK 的 Widgets 示例构建使用独立产物目录：

```powershell
$make = (Get-Command mingw32-make).Source
python graphics/qt5/scripts/build_window_examples.py `
    --sdk D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19 `
    --make $make `
    --output-root D:/workspace/codex-workspace/qt-validation
```

`build/` 和 `output/manifest.json` 位于指定目录，禁止输出到 graphics 源码或
共享 SDK 中。清单同时记录 SDK 的调用路径与解析后的真实路径，支持 Windows
目录联接。示例编译不代表 QEMU 显示、输入、进程回收或 GPU 加速验收通过。

独立键鼠/定时器探针使用同一脚本构建，加 `--example input-smoke` 并指定新的
输出目录。它只接收真实 QPA 输入：按 A、B，点击窗口，再按 Enter；成功输出
`qt input pass keys=2 mouse=1 timer=...` 并正常退出，90 秒没有完成则失败退出。
探针不注入 Qt 内部事件。Calculator 上游示例没有数字键快捷键，计算验收应使用
鼠标点击，不能将数字键没有改变显示误判为键盘驱动错误。

QEMU `virtio-gpu-device` 的软件渲染验收使用 EGLFS/KMS：

```text
QT_QPA_PLATFORM=eglfs
QT_QPA_EGLFS_INTEGRATION=eglfs_kms
QT_QPA_EGLFS_KMS_CONFIG=/media/vdap1/kms.json
QT_PLUGIN_PATH=/media/vdap1/plugins
QT_QPA_FONTDIR=/media/vdap1/fonts
LD_LIBRARY_PATH=/media/vdap1
GCONV_PATH=/media/vdap1/gconv
GBM_BACKENDS_PATH=/media/vdap1
GBM_ALWAYS_SOFTWARE=1
LIBGL_ALWAYS_SOFTWARE=1
GALLIUM_DRIVER=softpipe
QT_QPA_EGLFS_NO_LIBINPUT=1
QT_QPA_EVDEV_MOUSE_PARAMETERS=/dev/input/event1:abs
```

`kms.json` 为 `{"device":"/dev/dri/card0","hwcursor":false}`。这里的 event1
对应先添加 USB Keyboard、再添加 USB Tablet 的测试拓扑；运行前确认实际节点。
Tablet 的 `:abs` 参数负责把绝对坐标按设备范围缩放到屏幕。没有 udev 热插拔
支持的静态发现构建，应先等待 `/dev/input` 节点注册，再启动 Qt。

该配置已覆盖 analogclock、calculator 的 1280×800 显示、三轮 `12+3=15`、
USB 键鼠、Qt 定时器、SIGTERM 与正常退出。验收记录必须另外绑定内核 ELF、
应用、运行库和磁盘镜像哈希，并检查进程已不存在、输入客户端成对关闭、
线程数回归基线。以上是 QEMU 软件渲染范围，不代表 virgl/硬件 3D 或实机验收。
`package_runtime.py --gconv-root <与目标libc同源的gconv目录>` 会打包基础配置及
它引用的模块到 `lib/gconv`；测试盘将该目录部署为 `/media/vdap1/gconv`。
这些模块由 glibc 动态打开，不在普通 ELF `DT_NEEDED` 闭包中，遗漏会导致
Qt 报告 iconv 转换回退。基础模块已覆盖 UTF-8/UTF-16 中文数据往返测试；
完整 locale、额外字符集及中文字体显示仍需各自的数据文件和独立验收。

- 用 `file` 和目标工具链的 `readelf -d` 确认 `build/qt5-armv8a-linux/lib`
  下的库与 `examples/` 下的 ELF 均为 AArch64，动态依赖只来自目标 sysroot 和
  明确配置的 Luna 图形库。
- `eglfs-smoke.elf` 与 `widgets-display.elf` 在 NanoPC-T4 上的显示、DRM/GBM
  初始化和退出回收为独立实机验收，部署方法见 `sdk.md`。
