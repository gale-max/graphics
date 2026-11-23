# Luna ARM64 用户态图形组件

版本分支为 `master`。本工程提供 DRM 用户态库、Mesa EGL、GBM 和 OpenGL ES 运行库，以及 Weston Wayland 合成器。RK3399 图形配置使用 Panfrost，应用和合成器通过 Luna DRM/KMS 使用显示设备。另提供独立的 QEMU Mesa 配置，选择 VirGL 和 Softpipe。VirGL 依赖相匹配的 VirtIO GPU 及宿主渲染器。

## 产品构建

Windows 交叉构建使用 Catboy、ARM64 GNU/Linux 工具链、匹配应用 ABI 的 glibc SDK 和各工程的 `armv8a-user` 配置。Mesa 构建还使用 Python、Meson、Ninja 及已生成的 Panfrost 和 lexer 材料。先构建 libdrm，再构建 Mesa，随后构建需要图形运行库的应用或合成器。

| 工作目录 | Catboy 命令 | 产物 |
| --- | --- | --- |
| libdrm 工程根目录 | `catboy build libdrm modetest -p armv8a-user` | `libdrm.a`、`modetest.elf` |
| Mesa 工程根目录 | `catboy build mesa-panfrost -p armv8a-user` | `libgbm.so.1.0.0`、`libEGL.so.1.0.0`、`libGLESv2.so.2.0.0`、`libgallium-25.2.8.so`、`dri_gbm.so` |
| Weston 工程根目录 | `catboy build weston-desktop -p armv8a-user` | `weston.elf`、`desktop-shell.so`、`weston-desktop-shell.elf`、`weston-keyboard.elf`、`drm-backend.so`、`gl-renderer.so` |

`modetest` 是 libdrm 的 KMS 资源枚举与模式设置工具。Mesa 的 Panfrost 配置启用 Wayland、GBM、EGL 和 GLES2。从 Mesa 工程根目录运行 `catboy build mesa-qemu -p armv8a-user` 可构建独立的 QEMU 运行库。执行前设定 `LUNA_MESA_QEMU_OUTPUT` 指定源码树外的输出位置。该配置生成 ARM64 运行库、SONAME 别名和清单，打包实现见 `build_windows.py:317` 的 `package_qemu`。

## Weston 和 Qt

Weston 以 DRM backend 管理显示输出，GL renderer 负责合成，desktop-shell 管理窗口。运行时需一同部署 Weston 私有库、Shell 资源、libinput 设备规则和 XKB 键盘数据，并由同一图形 SDK 和目标系统提供 Mesa、Wayland、Cairo 等公共库。可以用 `LUNA_GRAPHICS_SDK` 选择 Weston 构建使用的 SDK。 Weston 构建入口见 `build_windows.py:74` 的 Weston `main`。

Qt 固定使用 qtbase 5.15.19，交叉构建独立于 Catboy。先按 Qt 工程配置准备同一 glibc sysroot、libdrm 和 Mesa SDK，再在 WSL 中 Qt 构建脚本所在的工作目录启动 Python 构建。按顺序选择 `configure`、`core`、`gui-eglfs`、`kms` 和 `widgets`。其产物供 QtCore、QtGui、QtWidgets 及 EGLFS/KMS 应用使用。

```sh
python3 qt5_build.py --stage configure
python3 qt5_build.py --stage core
python3 qt5_build.py --stage gui-eglfs
python3 qt5_build.py --stage kms
python3 qt5_build.py --stage widgets
```

## 资产交付

从打包脚本所在的工作目录运行 `python package_artifacts.py --output-root OUTPUT --ar aarch64-none-linux-gnu-ar.exe`。将 `OUTPUT` 换成源码树外且为空的输出位置，确保命令能找到目标 GNU ar。打包时将 thin archive 展开为普通归档，并记录上游版本、文件格式、大小和 SHA-256。实现见 `package_artifacts.py:58`。 保留同一构建的库、插件、应用和运行资源，部署时按产品预置的运行前缀配置目标系统。使用 SD 或 eMMC 时保留前 200 MiB 启动区域。对 512 字节扇区，数据分区起始 LBA 不小于 409600。

## 上游来源

组件基线为 libdrm 2.4.125、Mesa 25.2.8、Weston 9.0.0、qtbase 5.15.19、glmark2 2023.01，以及 kmscube 提交 `60be8e4bd4eb27b5b7c68b4c609304edb87bde8d`。Luna 集成保留各项目的原版权及随附许可。
