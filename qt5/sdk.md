# Luna Qt 5 Windows SDK 完整构建与部署

本文描述从空构建目录开始，准备源码、搭建 Windows/WSL 环境、构建 Luna Qt
目标库、构建 Windows 主机工具、组合 SDK、部署 Qt Creator、注册 Kit、构建
示例并检查产物的完整流程。最终所有可交付材料集中在一个目录：

```text
D:\luna-sdk\qt5-5.15.19
```

文中的“构建通过”只表示对应阶段产物检查通过。NanoPC-T4 显示、DRM/GBM、
输入和进程回收属于独立实机验收，不能用编译成功代替。

## 1. SDK 架构

该 SDK 是一个“Windows 主机构建工具 + Luna ARMv8A 目标运行库”的交叉开发
环境，不是 Windows 桌面 Qt，也不是可以直接放到板卡运行的单一目录镜像。

```text
                         Windows 开发主机
┌──────────────────────────────────────────────────────────────────┐
│ Qt Creator 20.0.1                                                │
│        │                                                         │
│        ├─ 调用 Windows PE 工具：qmake/moc/uic/rcc                 │
│        │                                                         │
│        └─ 读取 Luna Kit：编译器、sysroot、mkspec、目标库路径       │
└──────────────────────────────┬───────────────────────────────────┘
                               │ 生成 Makefile 并交叉编译
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ Luna ARMv8A 工具链                                               │
│ aarch64-none-linux-gnu-gcc/g++/ar/strip/readelf/gdb              │
│        │                                                         │
│        ├─ Luna glibc sysroot                                     │
│        ├─ Qt ARMv8A 头文件和目标库                               │
│        └─ Mesa/libdrm ARMv8A 图形库                              │
└──────────────────────────────┬───────────────────────────────────┘
                               │ 输出 AArch64 ELF/so
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ NanoPC-T4 / Luna loader                                          │
│ Qt 应用 -> QtCore/Gui/Widgets -> EGLFS/KMS -> GBM/DRM -> 显示驱动 │
└──────────────────────────────────────────────────────────────────┘
```

必须严格区分两类二进制：

| 类型 | 运行位置 | 文件示例 | 禁止事项 |
| --- | --- | --- | --- |
| 主机工具 | Windows | `qmake.exe`、`moc.exe`、`uic.exe` | 不得部署到 Luna |
| 目标产物 | Luna ARMv8A | `libQt5Core.so`、`libqeglfs.so`、应用 ELF | 不得由 Windows 执行 |

Qt Creator 只负责工程管理和调用工具。真正决定目标 ABI 的是 Luna ARMv8A
工具链、glibc sysroot、`luna-armv8a` mkspec 和目标 Qt 库。

## 2. 组成与来源

SDK 内容不是从一个上游压缩包直接复制而来，而是由以下输入组合生成：

| 组成 | 权威来源 | 构建方式 | SDK 中的位置 |
| --- | --- | --- | --- |
| QtBase 5.15.19 | Qt 官方源码及 `sources.yaml` 固定哈希 | WSL 交叉编译 | `include/`、`lib/`、`plugins/`、`src/` |
| Windows Qt 工具 | 同版本 QtBase/QtDeclarative/QtTools 源码 | Windows WinLibs 原生编译 | `bin/*.exe` |
| Luna 平台配置 | `qt5/mkspecs/luna-armv8a` | 随 SDK 打包 | `mkspecs/luna-armv8a/` |
| C/C++ ABI | Luna ARMv8A 工具链 sysroot | 不复制主机 ABI | 由 Kit 的 sysroot 引用 |
| EGL/GLES/GBM | `graphics/mesa` 的 ARMv8A 产物 | Mesa 独立构建 | `staging/` 及应用运行目录 |
| DRM UAPI/库 | `graphics/libdrm` 的 ARMv8A 产物 | libdrm 独立构建 | `staging/` 及应用运行目录 |
| IDE | Qt 官方 Qt Creator 20.0.1 | 官方安装包解包/安装 | `tools/QtCreator-20.0.1/` |
| Kit 配置 | `qt5/scripts/register_qtcreator_kit.ps1` | 在 Windows 注册 | Qt Creator 用户配置 |
| 示例 | `qt5/examples` | 由 SDK qmake 交叉编译 | `examples/` |

当前实际交付的 Qt 目标库为 QtCore、QtGui、QtWidgets、EGLFS 设备集成和
EGLFS/KMS 支持；目标插件为 `platforms/libqeglfs.so` 及 EGL device integration
插件。源码清单中存在但尚未进入目标构建脚本的模块，不属于当前可用能力。

构建数据流固定为：

```text
sources.yaml
    │
    ├─ prepare.py ──> qt5/upstream（校验后的上游源码）
    │
    ├─ qt5_build.py ──> WSL target-armv8a-luna（ARMv8A Qt）
    │                         ▲
    │                         ├─ Luna glibc sysroot
    │                         └─ Mesa/libdrm ARMv8A 产物
    │
    ├─ build_windows_host_tools.py ──> Windows PE 主机工具
    │
    └─ package_windows_sdk.py ──> D:\luna-sdk\qt5-5.15.19
```

仓库只提交构建定义和必要源码材料。`build/`、`output/` 以及主机短路径临时
目录都是可再生产物；`D:\luna-sdk\qt5-5.15.19` 是交付结果，也不作为源码
提交到 graphics 仓库。

## 3. 当前支持范围

| 项目 | 版本/配置 | 作用 |
| --- | --- | --- |
| Qt | 5.15.19 | QtCore、QtGui、QtWidgets、EGLFS/KMS |
| Qt Creator | 20.0.1 | Windows IDE，不提供目标 Qt 库 |
| 目标架构 | ARMv8A/AArch64 | Luna 用户态 ELF |
| 目标 C 库 | Luna 工具链 sysroot 中的 glibc | 与 loader ABI 保持一致 |
| 图形接口 | DRM、GBM、EGL、OpenGL ES 2 | 复用 Luna libdrm 和 Mesa |
| qmake spec | `luna-armv8a` | 定义目标编译、链接和 sysroot |
| 构建并发 | 最多 4 个任务 | Windows、WSL 和 Qt Creator 均适用 |

只有已经接入 `qt5_build.py`、生成目标库并通过 ELF 检查的模块才算进入 SDK。
下载或解压了源码不等于已经支持该模块。

## 4. 目录约定

```text
Windows 工作区： D:\workspace\luna-workspace
图形仓库：       D:\workspace\luna-workspace\os\graphics
Qt 工程：        D:\workspace\luna-workspace\os\graphics\qt5
Windows 暂存：   D:\q5w
WSL 构建副本：   /home/surest/nanopc-workspace/graphics/qt5
最终 SDK：       D:\luna-sdk\qt5-5.15.19
```

`D:\q5w` 必须保持短路径，避免 Qt 私有头文件触发 Windows `MAX_PATH` 问题。

### 4.1 `tools` 工具链目录

默认工具链不属于 Qt 源码，也不复制进 SDK。默认布局为：

```text
D:\workspace\luna-workspace\tools\toolchains\
└── aarch64-none-linux-gnu\
    ├── bin\
    │   ├── aarch64-none-linux-gnu-gcc.exe
    │   ├── aarch64-none-linux-gnu-g++.exe
    │   ├── aarch64-none-linux-gnu-ar.exe
    │   ├── aarch64-none-linux-gnu-readelf.exe
    │   └── aarch64-none-linux-gnu-gdb.exe
    └── aarch64-none-linux-gnu\libc\       # Luna glibc sysroot
```

工具链目录可以改变，但编译器和 sysroot 必须成对指定。目标 Qt 构建通过环境变量
定制：

```bash
export LUNA_QT_TOOLCHAIN=/opt/luna/toolchains/aarch64-none-linux-gnu
export LUNA_QT_REFERENCE_SYSROOT=/opt/luna/sysroots/armv8a-glibc
export LUNA_QT_SYSROOT=/opt/luna/sysroots/armv8a-glibc
export QT_MAKE=/usr/bin/make
```

变量含义：

| 变量 | 含义 | 约束 |
| --- | --- | --- |
| `LUNA_QT_TOOLCHAIN` | 目标交叉工具链根目录 | 其下必须有 `bin/aarch64-none-linux-gnu-*` |
| `LUNA_QT_REFERENCE_SYSROOT` | Luna 认可的 ABI 基准 sysroot | 用于校验 glibc 头文件、启动对象和运行库 |
| `LUNA_QT_SYSROOT` | 本次实际编译使用的 sysroot | 必须与基准 sysroot 的关键文件一致 |
| `QT_MAKE` | WSL 中使用的 make | 可不设置，默认从 `PATH` 查找 `make` |

不能只替换 GCC 而继续使用旧 sysroot，也不能让 Qt、Mesa、libdrm、应用和 Luna
loader 分别使用不同 glibc。否则即使链接成功，也可能在动态加载、TLS、异常展开
或 C++ 运行时阶段失败。

打包阶段通过参数指定 Windows 工具链和 sysroot，不依赖固定工作区：

```powershell
python qt5\scripts\package_windows_sdk.py `
    --sdk D:\sdk-output\qt5-5.15.19 `
    --toolchain E:\luna-tools\aarch64\bin `
    --sysroot E:\luna-tools\aarch64\sysroot
```

Windows 主机工具不使用 ARM 工具链。WinLibs 和 Perl 单独指定：

```powershell
python qt5\scripts\build_windows_host_tools.py `
    --jobs 4 `
    --stage D:\q5w `
    --winlibs-bin E:\host-tools\winlibs\mingw64\bin `
    --perl-bin E:\host-tools\git\usr\bin
```

Qt Creator Kit 注册时再声明 SDK、Qt Creator 和工作区位置：

```powershell
powershell -ExecutionPolicy Bypass -File `
    D:\sdk-output\qt5-5.15.19\scripts\register_qtcreator_kit.ps1 `
    -SdkRoot D:\sdk-output\qt5-5.15.19 `
    -QtCreatorRoot D:\apps\QtCreator-20.0.1 `
    -WorkspaceRoot E:\luna-workspace
```

当前 Kit 注册脚本从 `WorkspaceRoot\tools\toolchains\aarch64-none-linux-gnu`
推导编译器和 sysroot。若自定义工具链不在该布局中，应先调整注册脚本参数，
不能在 Qt Creator 中手工混用另一套编译器。

最终交付目录结构：

```text
qt5-5.15.19/
├── bin/                         # Windows qmake、moc、uic、rcc 等
├── include/                     # Luna ARMv8A Qt 头文件
├── lib/                         # Luna ARMv8A Qt 目标库
├── mkspecs/luna-armv8a/         # Luna qmake 平台配置
├── plugins/                     # Luna Qt 目标插件
├── qml/                         # 已构建的目标 QML 模块
├── staging/                     # Mesa/libdrm 链接材料
├── tools/QtCreator-20.0.1/      # Windows Qt Creator
├── installer/                   # 官方安装包及校验信息
├── scripts/                     # SDK 生成和 Kit 注册工具
├── examples/widgets-display/    # QtWidgets 显示示例
├── config-temp/                 # Kit 固化临时目录
└── README.md                    # 本文的交付副本
```

## 5. Windows 环境准备

Windows 需要 Git for Windows、原生 Windows Python 3、WSL2、WinLibs
MinGW-w64 POSIX/UCRT、Windows `tar.exe` 和 Qt Creator 20.0.1。检查：

```powershell
git --version
python --version
wsl.exe -l -v
tar.exe --version

$winlibs = Split-Path (Get-Command mingw32-make.exe).Source
& "$winlibs\gcc.exe" --version
& "$winlibs\mingw32-make.exe" --version
Test-Path "C:\Program Files\Git\usr\bin\perl.exe"
```

如果 WinLibs 没有加入 `PATH`，后续通过 `--winlibs-bin` 显式传入。不要假定
不同机器的 WinGet 包目录相同。

ARMv8A 工具链和 sysroot 必须存在：

```text
D:\workspace\luna-workspace\tools\toolchains\aarch64-none-linux-gnu\bin\aarch64-none-linux-gnu-gcc.exe
D:\workspace\luna-workspace\tools\toolchains\aarch64-none-linux-gnu\bin\aarch64-none-linux-gnu-g++.exe
D:\workspace\luna-workspace\tools\toolchains\aarch64-none-linux-gnu\bin\aarch64-none-linux-gnu-gdb.exe
D:\workspace\luna-workspace\tools\toolchains\aarch64-none-linux-gnu\aarch64-none-linux-gnu\libc
```

Qt、应用和 Luna loader 必须使用同一 sysroot。构建脚本会比较关键 glibc
头文件、运行库和启动对象的 SHA-256，任一不一致都会终止配置。

## 6. WSL 环境准备

```powershell
wsl.exe -d ubuntu20.04
```

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential python3 python3-yaml perl pkg-config rsync \
    git curl ca-certificates xz-utils tar gperf bison flex

python3 --version
gcc --version
make --version
perl --version
pkg-config --version
rsync --version
```

目标编译器由 Windows 工作区提供，不使用 WSL 自带的 AArch64 sysroot：

```bash
export LUNA_QT_TOOLCHAIN=/mnt/d/workspace/luna-workspace/tools/toolchains/arm-gnu-toolchain-14.3.rel1-x86_64-aarch64-none-linux-gnu
export LUNA_QT_REFERENCE_SYSROOT=/mnt/d/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu/aarch64-none-linux-gnu/libc
export LUNA_QT_SYSROOT="$LUNA_QT_REFERENCE_SYSROOT"
```

## 7. 源码与依赖准备

`graphics/qt5`、`graphics/mesa` 和 `graphics/libdrm` 必须位于同一工作区。Qt
配置会读取 Mesa 的 GBM/EGL/GLES/Gallium 产物和 libdrm 头文件、目标库。
构建 Qt 前至少检查：

```text
mesa/build/mesa-25.2.8/src/egl/libEGL.so.*
mesa/build/mesa-25.2.8/src/mapi/es2api/libGLESv2.so.*
mesa/build/mesa-25.2.8/src/gbm/libgbm.so.*
mesa/build/mesa-25.2.8/src/gallium/targets/dri/libgallium-25.2.8.so
libdrm/build/libdrm/armv8a-user/libdrm.a
```

缺少时先按 Mesa、libdrm 仓库说明构建，不能用主机图形库替代。

在 Windows 准备固定版本源码：

```powershell
cd D:\workspace\luna-workspace\os\graphics
python qt5\scripts\prepare.py
```

`prepare.py` 读取 `sources.yaml`，通过 HTTPS 下载、校验 SHA-256，并展开到
`qt5\upstream`。只准备主机工具所需源码可执行：

```powershell
python qt5\scripts\prepare.py qtbase qtdeclarative qttools
```

成功判据是每项打印 `source ready`，不能通过修改清单哈希绕过校验失败。

同步到 WSL：

```bash
mkdir -p /home/surest/nanopc-workspace/graphics
rsync -a --delete \
    --exclude build/ \
    --exclude output/ \
    /mnt/d/workspace/luna-workspace/os/graphics/qt5/ \
    /home/surest/nanopc-workspace/graphics/qt5/

ln -sfn /mnt/d/workspace/luna-workspace/os/graphics/mesa \
    /home/surest/nanopc-workspace/graphics/mesa
ln -sfn /mnt/d/workspace/luna-workspace/os/graphics/libdrm \
    /home/surest/nanopc-workspace/graphics/libdrm
```

`--exclude build/` 保留 WSL 增量结果。真正从零构建时，只清理已确认的
`/home/surest/nanopc-workspace/graphics/qt5/build/target-armv8a-luna`。

## 8. 构建 Luna ARMv8A 目标 Qt

以下命令全部在 WSL 执行，固定最多 4 个任务：

```bash
cd /home/surest/nanopc-workspace/graphics/qt5

python3 scripts/qt5_build.py --stage configure
python3 scripts/qt5_build.py --stage core --jobs 4
python3 scripts/qt5_build.py --stage gui-eglfs --jobs 4
python3 scripts/qt5_build.py --stage kms --jobs 4
python3 scripts/qt5_build.py --stage widgets --jobs 4
python3 scripts/qt5_build.py --stage smoke --jobs 4
python3 scripts/qt5_build.py --stage widgets-display --jobs 4
```

阶段作用：

1. `configure`：清理配置缓存，核对 glibc ABI，整理 Mesa/libdrm staging，
   生成 `luna-armv8a` mkspec并配置 Qt。
2. `core`：构建 QtCore。
3. `gui-eglfs`：构建 QtGui。
4. `kms`：构建平台支持及 EGLFS/KMS 插件。
5. `widgets`：构建 QtWidgets。
6. `smoke`：构建 EGLFS 冒烟程序。
7. `widgets-display`：构建 QtWidgets 显示程序。

新构建目录固定为：

```text
/home/surest/nanopc-workspace/graphics/qt5/build/target-armv8a-luna
```

所有构建和打包步骤只使用 `target-armv8a-luna`。检查：

```bash
file build/target-armv8a-luna/lib/libQt5Core.so.5.15.19
cat build/target-armv8a-luna/target-abi.json
```

产物必须是 AArch64 ELF，ABI 清单必须来自指定 Luna sysroot。

## 9. 构建 Windows 主机工具

返回 Windows PowerShell：

```powershell
cd D:\workspace\luna-workspace\os\graphics
$winlibs = Split-Path (Get-Command mingw32-make.exe).Source
$perl = "C:\Program Files\Git\usr\bin"

python qt5\scripts\build_windows_host_tools.py `
    --jobs 4 `
    --stage D:\q5w `
    --winlibs-bin "$winlibs" `
    --perl-bin "$perl"
```

脚本会在短路径展开 QtBase、QtDeclarative、QtTools，使用 `win32-g++` 构建
静态主机 Qt，再生成 qmake、moc、uic、rcc、qmlcachegen、qmlimportscanner、
lrelease、lupdate，并验证每个文件的 PE 签名。输出：

```text
qt5\build\host-windows\sdk-bin
qt5\build\host-windows\mkspecs
```

检查：

```powershell
qt5\build\host-windows\sdk-bin\qmake.exe -v
```

必须报告 Qt 5.15.19。这些是 Windows 主机工具，不部署到板卡。

## 10. 组合为一个 SDK 目录

第 8、9 节均通过后执行：

```powershell
python qt5\scripts\package_windows_sdk.py `
    --sdk D:\luna-sdk\qt5-5.15.19
```

默认目标输入为：

```text
\\wsl.localhost\ubuntu20.04\home\surest\nanopc-workspace\graphics\qt5\build\target-armv8a-luna
```

脚本通过 WSL `rsync -aL` 解引用 `.so` 链接，合并主机工具和目标树，重写
WSL 绝对路径，并复制生成脚本、示例和本文。非默认输入要显式传入：

```powershell
python qt5\scripts\package_windows_sdk.py `
    --sdk D:\luna-sdk\qt5-5.15.19 `
    --target "\\wsl.localhost\ubuntu20.04\home\surest\nanopc-workspace\graphics\qt5\build\target-armv8a-luna"
```

检查：

```powershell
D:\luna-sdk\qt5-5.15.19\bin\qmake.exe -query
```

必须满足：`QT_INSTALL_PREFIX`、`QT_HOST_PREFIX` 指向最终目录，`QMAKE_XSPEC`
为 `luna-armv8a`，且不出现 `/home/surest`、`/mnt/d` 或 `D:/q5w`。

## 11. 放入 Qt Creator 并注册 Kit

SDK 脚本不会下载或覆盖 Qt Creator。Qt Creator 和官方安装包分别放到：

```text
D:\luna-sdk\qt5-5.15.19\tools\QtCreator-20.0.1
D:\luna-sdk\qt5-5.15.19\installer\qt-creator-opensource-windows-x86_64-20.0.1.exe
```

当前安装包 MD5：

```text
94052A4D2179D28DCB52EA3EFB9C95D0
```

关闭 Qt Creator 后注册 Kit：

```powershell
powershell -ExecutionPolicy Bypass -File `
    D:\luna-sdk\qt5-5.15.19\scripts\register_qtcreator_kit.ps1
```

非默认工作区通过 `-SdkRoot`、`-WorkspaceRoot` 参数指定。注册过程检查输入，
依次注册 C/C++ 编译器、GDB、Qt 和 `Luna ARMv8A` Kit，写入 sysroot、
`luna-armv8a` 和 `MAKEFLAGS=-j4`，并固化 Kit，防止 Qt Creator 重启时清理。

在 Qt Creator“首选项 -> Kits”核对：

```text
Kit:         Luna ARMv8A
Qt:          Luna Qt 5.15.19 ARMv8A
C:           Luna ARMv8A GCC
C++:         Luna ARMv8A G++
Debugger:    Luna ARMv8A GDB
Mkspec:      luna-armv8a
Sysroot:     ...\aarch64-none-linux-gnu\libc
Environment: MAKEFLAGS=-j4
```

## 12. 构建和检查应用

Qt Creator 打开：

```text
D:\luna-sdk\qt5-5.15.19\examples\widgets-display\widgets-display.pro
```

选择 `Luna ARMv8A` Kit，运行 qmake 后构建。命令行等价过程：

```powershell
New-Item -ItemType Directory -Force D:\luna-sdk\build\widgets-display
Set-Location D:\luna-sdk\build\widgets-display
D:\luna-sdk\qt5-5.15.19\bin\qmake.exe `
    D:\luna-sdk\qt5-5.15.19\examples\widgets-display\widgets-display.pro
mingw32-make.exe -j4
```

检查 ELF：

```powershell
$readelf = "D:\workspace\luna-workspace\tools\toolchains\aarch64-none-linux-gnu\bin\aarch64-none-linux-gnu-readelf.exe"
& $readelf -h .\widgets-display.elf
& $readelf -d .\widgets-display.elf
```

要求 ELF64、AArch64，动态依赖来自目标 Qt、EGL/GLES、GBM、Gallium、glibc
和 libstdc++，不能出现 Windows DLL、x86_64 库或主机构建目录。

## 13. NanoPC-T4 部署

板端运行目录固定为 `/media/mmcblk1p1/qt5`，至少包含应用、动态加载器、
QtCore/QtGui/QtWidgets、EGLFS/KMS 插件和字体。环境：

```text
setenv LD_LIBRARY_PATH /media/mmcblk1p1/qt5/lib:/media/mmcblk1p1
setenv QT_PLUGIN_PATH /media/mmcblk1p1/qt5/plugins
setenv QT_QPA_PLATFORM eglfs
setenv QT_QPA_EGLFS_INTEGRATION eglfs_kms
setenv QT_QPA_EGLFS_DISABLE_INPUT 1
setenv QT_QPA_FONTDIR /media/mmcblk1p1/qt5/fonts
setenv GBM_BACKENDS_PATH /media/mmcblk1p1
setenv GBM_BACKEND dri
load /media/mmcblk1p1/qt5/bin/widgets-display.elf
```

实机要求 EGLFS/KMS 插件加载、DRM/GBM 初始化、画面稳定显示，并能通过
`Ctrl+C` 终止后返回 Luna shell。

## 14. 完整检查顺序

1. Windows、WSL、WinLibs、Git/Perl、Python 环境通过。
2. ARMv8A 工具链和 Luna glibc sysroot 完整。
3. Mesa、libdrm ARMv8A 依赖产物完整。
4. `prepare.py` 下载、SHA-256 校验、解包通过。
5. Qt 源码同步到 WSL，依赖路径正确。
6. WSL 七个目标阶段通过，输出 AArch64 ELF。
7. Windows 主机工具生成并通过 PE 检查。
8. SDK 组合到 `D:\luna-sdk\qt5-5.15.19`，qmake 路径检查通过。
9. Qt Creator 与安装包放入同一 SDK 根目录。
10. Kit 注册后重启 Qt Creator 仍然存在。
11. 示例由 Qt Creator/qmake 构建为 AArch64 ELF。
12. 实机显示和退出回收单独验收。

## 15. 常见故障

- `qmake -query` 出现 WSL 或 `D:\q5w`：元数据迁移失败。
- 找不到 `spec_pre.prf`：Windows 主机 mkspec 打包不完整。
- `.so` 链接缺失：未使用 `rsync -aL` 解引用目标树。
- `target ABI mismatch`：Qt 与 Luna loader 使用了不同 sysroot。
- Qt Creator 重启后 Kit 消失：Kit 固化步骤未完成。
- 生成 PE/x86_64 文件：选择了错误 Kit。
- 链接 Windows Qt DLL：mkspec、sysroot 或库搜索路径错误。
- 新构建仍读取旧结果：清理 WSL 的 `target-armv8a-luna` 后从 configure 重建。
