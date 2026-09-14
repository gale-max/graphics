# Luna Qt 5 Windows SDK 产品手册

| 项目 | 值 |
| --- | --- |
| 产品名称 | Luna Qt 5 Windows SDK |
| Qt 版本 | 5.15.19（Qt 5 系列最后一个公开源码版本） |
| 目标平台 | Luna ARMv8A / AArch64 用户态（NanoPC-T4 验证平台） |
| 开发主机 | Windows 10/11 x86-64 + WSL2 |
| 默认交付目录 | `D:\luna-sdk\qt5-5.15.19` |
| 配套 IDE | Qt Creator 20.0.1（Windows） |

本手册面向 SDK 的构建者与集成者，描述 SDK 的组成、来源、构建方法和使用
方式。文中“构建通过”仅表示对应阶段的产物检查通过；NanoPC-T4 上的显示、
DRM/GBM 初始化、输入和进程回收属于独立实机验收，不能以编译成功替代。

---

## 1. 产品定义

### 1.1 SDK 是什么，不是什么

Luna Qt 5 Windows SDK 是一套**在 Windows 主机上进行、面向 Luna ARMv8A 目标
的 Qt 交叉开发环境**。它由三部分组成：运行于 Windows 的主机构建工具、
运行于 Luna 板卡的 Qt 目标运行库，以及连接二者的交叉工具链、sysroot 和
qmake 平台配置。

本 SDK **不是**：

- Windows 桌面 Qt —— 不提供可在 Windows 上运行的 Qt 应用运行库；
- 可直接写入板卡的单目录镜像 —— 目标库需按第 7.3 节组织后再部署；
- 完整 Qt 发行版 —— 仅交付已验证的模块（见 2.3）。

### 1.2 架构

```text
                        Windows 开发主机
┌──────────────────────────────────────────────────────────────────┐
│ Qt Creator 20.0.1                                                 │
│   ├─ 调用 Windows PE 工具：qmake.exe / moc.exe / uic.exe / rcc.exe │
│   └─ 读取 Luna ARMv8A Kit：编译器、sysroot、mkspec、目标库路径     │
└───────────────────────────────┬──────────────────────────────────┘
                                │ 生成 Makefile，交叉编译
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ Luna ARMv8A 交叉工具链                                            │
│   aarch64-none-linux-gnu-gcc / g++ / ar / strip / readelf / gdb   │
│   ├─ Luna glibc sysroot                                           │
│   ├─ Qt ARMv8A 头文件与目标库                                     │
│   └─ Mesa / libdrm ARMv8A 图形库                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │ 输出 AArch64 ELF / .so
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ NanoPC-T4 / Luna loader                                           │
│   Qt 应用 → QtCore/Gui/Widgets → EGLFS/KMS → GBM/DRM → 显示驱动    │
└──────────────────────────────────────────────────────────────────┘
```

Qt Creator 只负责工程管理与工具调用。决定目标 ABI 的是交叉工具链、
glibc sysroot、`luna-armv8a` mkspec 和 Qt 目标库这四者，必须始终保持一致。

### 1.3 两类二进制

SDK 内包含两类不可混用的二进制：

| 类型 | 运行位置 | 文件示例 | 约束 |
| --- | --- | --- | --- |
| 主机工具 | Windows x86-64 | `bin\qmake.exe`、`bin\moc.exe`、`bin\uic.exe`、`bin\rcc.exe` | 不得部署到板卡 |
| 目标产物 | Luna ARMv8A | `lib\libQt5Core.so`、`plugins\platforms\libqeglfs.so`、应用 ELF | 不得在 Windows 执行 |

### 1.4 自动化实现状态

SDK 的生产由仓库 `qt5/scripts` 下的脚本驱动。当前实现状态：

| 环节 | 脚本 | 状态 |
| --- | --- | --- |
| 源码准备与校验 | `scripts/prepare.py` | 已交付 |
| 目标库交叉编译（WSL） | `scripts/qt5_build.py` | 已交付 |
| Windows 主机工具构建 | `scripts/build_windows_host_tools.py` | 规划中 |
| 板端运行时打包 | `scripts/package_runtime.py` | 已实现，生成哈希清单 |
| Qt Creator Kit 注册 | `scripts/register_qtcreator_kit.ps1` | 规划中 |

标注“规划中”的章节给出该环节的目标流程与命令行接口，作为实现依据；在
脚本交付前，相应步骤需按接口说明手动完成。

---

## 2. SDK 组成

### 2.1 组成与来源

SDK 不是从单一上游压缩包复制而来，而是由下列输入组合生成：

| 组成 | 权威来源 | 生产方式 | SDK 中的位置 |
| --- | --- | --- | --- |
| Qt 目标库、头文件、插件 | Qt 官方 qtbase 5.15.19（`sources.yaml` 固定 SHA-256） | WSL 交叉编译 | `include/`、`lib/`、`plugins/` |
| Windows 主机工具 | 同版本 qtbase / qtdeclarative / qttools | Windows WinLibs MinGW 原生编译 | `bin/*.exe` |
| Luna 平台配置 | `qt5/mkspecs/luna-armv8a` | 随 SDK 打包 | `mkspecs/luna-armv8a/` |
| 交叉工具链 | Arm GNU Toolchain 14.3.Rel1 | 外部提供，Kit 引用 | 不复制进 SDK |
| glibc sysroot | Luna 认可的 ARMv8A glibc sysroot | 外部提供，Kit 引用 | 不复制进 SDK |
| EGL / GLES / GBM / Gallium | `graphics/mesa` 的 ARMv8A 产物 | Mesa 独立构建 | `staging/` |
| DRM UAPI 与库 | `graphics/libdrm` 的 ARMv8A 产物 | libdrm 独立构建 | `staging/` |
| IDE | Qt 官方 Qt Creator 20.0.1 | 官方安装包解包 | `tools/QtCreator-20.0.1/` |
| Kit 注册脚本 | `qt5/scripts/register_qtcreator_kit.ps1` | 随 SDK 打包 | `scripts/` |
| 示例工程 | `qt5/examples` | 由 SDK qmake 交叉编译 | `examples/` |

### 2.2 交付目录结构

```text
qt5-5.15.19/
├── bin/                       # Windows 主机工具：qmake.exe、moc.exe、uic.exe、rcc.exe 等
├── include/                   # Luna ARMv8A Qt 头文件
├── lib/                       # Luna ARMv8A Qt 目标库（.so）
├── mkspecs/
│   └── luna-armv8a/           # Luna qmake 平台配置（qmake.conf、qplatformdefs.h）
├── plugins/                   # Luna Qt 目标插件（platforms、egldeviceintegrations 等）
├── qml/                       # 已构建的目标 QML 模块（如有）
├── staging/                   # Mesa / libdrm 链接材料与 pkg-config
├── tools/
│   └── QtCreator-20.0.1/      # Windows Qt Creator
├── installer/                 # Qt Creator 官方安装包及校验信息
├── scripts/                   # Kit 注册与 SDK 维护脚本
├── examples/                  # 示例工程（eglfs-smoke、widgets-display）
└── README.md                  # 交付说明（本手册的精简副本）
```

交叉工具链和 sysroot 不进入 SDK 目录，由 Kit 通过绝对路径引用（见 3.4）。

### 2.3 支持矩阵

| 项目 | 版本 / 配置 | 说明 |
| --- | --- | --- |
| Qt 模块 | QtCore、QtGui、QtWidgets | 已交付目标库 |
| 平台插件 | `platforms/libqeglfs.so`、EGLFS device integration、EGLFS/KMS 支持 | 已交付 |
| 目标架构 | ARMv8A / AArch64 | Cortex-A53，`-march=armv8-a -mtune=cortex-a53 -ffixed-x18` |
| 目标 C 库 | Luna sysroot 中的 glibc | 与板卡 loader ABI 一致 |
| 图形接口 | DRM、GBM、EGL、OpenGL ES 2 | 复用 Luna libdrm 与 Mesa |
| qmake spec | `luna-armv8a` | 定义目标编译、链接与 sysroot |
| 构建并发 | 建议不超过 4 个任务 | Windows、WSL、Qt Creator 通用 |
| 不在范围 | QtWayland、QtWebEngine、QtDeclarative 运行库 | 未接入目标构建 |

仅当模块已接入 `qt5_build.py`、生成目标库并通过 ELF 检查后，才算进入 SDK。
下载或解压源码不等于支持该模块。

---

## 3. 工具链与 sysroot

### 3.1 交叉工具链

目标代码固定使用 **Arm GNU Toolchain 14.3.Rel1**（三元组
`aarch64-none-linux-gnu`）。SDK 不携带工具链；构建与 Kit 均通过路径引用。

必需组件：

```text
<toolchain>/bin/aarch64-none-linux-gnu-gcc
<toolchain>/bin/aarch64-none-linux-gnu-g++
<toolchain>/bin/aarch64-none-linux-gnu-ar
<toolchain>/bin/aarch64-none-linux-gnu-strip
<toolchain>/bin/aarch64-none-linux-gnu-readelf
<toolchain>/bin/aarch64-none-linux-gnu-gdb
```

WSL 构建默认路径：

```text
/mnt/d/workspace/luna-workspace/tools/toolchains/arm-gnu-toolchain-14.3.rel1-x86_64-aarch64-none-linux-gnu
```

Windows 侧（Qt Creator 调试器、readelf 校验）使用同工具链的 Windows 版本：

```text
D:\workspace\luna-workspace\tools\toolchains\aarch64-none-linux-gnu\bin\aarch64-none-linux-gnu-*.exe
```

### 3.2 glibc sysroot 与 ABI 契约

目标 glibc/sysroot **不使用工具链自带副本**，统一复用 Luna 认可的 ARMv8A
glibc sysroot，以保证 Qt、Mesa、libdrm、应用与 Luna loader 使用同一套
glibc。默认路径：

```text
/mnt/d/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu/aarch64-none-linux-gnu/libc
```

`qt5_build.py` 在每次 `configure` 前执行 ABI 校验：比较“实际 sysroot”与
“参考 sysroot”中下列文件的 SHA-256，任一不一致立即终止配置，并将结果写入
`build/qt5-armv8a-linux/target-abi.json`。

```text
usr/include/features.h
lib64/libc.so.6
usr/lib64/crt1.o
```

**约束**：不得只替换 GCC 而沿用旧 sysroot；不得让上述组件使用不同 glibc。
即使链接成功，ABI 不一致也可能在动态加载、TLS、异常展开或 C++ 运行时阶段
失败。

### 3.3 环境变量

WSL 构建通过环境变量定制工具链与 sysroot：

| 变量 | 含义 | 约束 |
| --- | --- | --- |
| `LUNA_QT_TOOLCHAIN` | 交叉工具链根目录 | 其下须有 `bin/aarch64-none-linux-gnu-gcc`、`g++` |
| `LUNA_QT_REFERENCE_SYSROOT` | Luna 认可的 ABI 基准 sysroot | 用于校验 glibc 头文件、启动对象与运行库 |
| `LUNA_QT_SYSROOT` | 本次实际使用的 sysroot | 默认等于基准 sysroot，关键文件须一致 |
| `LUNA_QT_BUILD_NAME` | 构建目录名 | 默认 `qt5-armv8a-linux` |
| `QT_MAKE` | 指定 `make` 路径 | 可不设，默认从 `PATH` 查找 |
| `QT_SHELL` | 指定 `configure` 使用的 shell | 可不设，默认自动探测 `bash`/`sh` |

示例：

```bash
export LUNA_QT_TOOLCHAIN=/mnt/d/workspace/luna-workspace/tools/toolchains/arm-gnu-toolchain-14.3.rel1-x86_64-aarch64-none-linux-gnu
export LUNA_QT_REFERENCE_SYSROOT=/mnt/d/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu/aarch64-none-linux-gnu/libc
export LUNA_QT_SYSROOT="$LUNA_QT_REFERENCE_SYSROOT"
```

### 3.4 SDK 与 Kit 对工具链的引用

Kit 注册脚本默认从
`<WorkspaceRoot>\tools\toolchains\aarch64-none-linux-gnu` 推导 C/C++ 编译器、
GDB 和 sysroot。若工具链不在该布局中，须先调整注册脚本参数，**不得**在
Qt Creator 中手动混入另一套编译器。

---

## 4. 目标平台库

### 4.1 Qt 目标库与插件

| 类别 | 文件 | SDK 位置 |
| --- | --- | --- |
| 核心库 | `libQt5Core.so.5.15.19`、`libQt5Gui.so.*`、`libQt5Widgets.so.*` | `lib/` |
| EGLFS 支持 | `libQt5EglFSDeviceIntegration.so.*`、`libQt5EglFsKmsSupport.so.*` | `lib/` |
| 平台插件 | `platforms/libqeglfs.so` | `plugins/` |
| EGL 设备集成 | `egldeviceintegrations/libqeglfs-kms-integration.so` | `plugins/` |
| 头文件 | QtCore / QtGui / QtWidgets 公共头 | `include/` |

所有目标库必须为 AArch64 ELF64，动态依赖仅来自目标 Qt、Mesa 图形栈、
libdrm、glibc 与 libstdc++。

### 4.2 图形栈（staging）

`configure` 阶段将 Mesa 与 libdrm 的 ARMv8A 产物整理到
`build/qt5-armv8a-linux/staging/lib`，并生成 `gbm.pc`。所需上游产物：

```text
mesa/upstream/include/
mesa/upstream/src/gbm/main/
mesa/build/mesa-25.2.8/src/egl/libEGL.so.*
mesa/build/mesa-25.2.8/src/mapi/es2api/libGLESv2.so.*
mesa/build/mesa-25.2.8/src/gbm/libgbm.so.*
mesa/build/mesa-25.2.8/src/gallium/targets/dri/libgallium-25.2.8.so
mesa/build/mesa-25.2.8/subprojects/expat-2.5.0/libexpat.so.*
libdrm/upstream/include/drm/
libdrm/build/libdrm/armv8a-user/libdrm.a
```

`graphics/qt5`、`graphics/mesa`、`graphics/libdrm` 必须并列于同一工作区。
缺少产物时先按 Mesa、libdrm 仓库说明构建，不得用主机图形库替代。

### 4.3 mkspec

`mkspecs/luna-armv8a/` 定义目标平台：`MAKEFILE_GENERATOR = UNIX`、
`QMAKE_PLATFORM = linux unix posix`，编译器指向交叉工具链，
`QMAKE_SYSROOT` 指向 Luna sysroot，OpenGL ES2 / EGL / GBM / DRM 的头文件与
库目录指向 staging。打包时 mkspec 中的路径占位符按 SDK 布局重写。

### 4.4 ABI 清单

`build/qt5-armv8a-linux/target-abi.json` 记录 ABI 校验涉及文件的 SHA-256、
实际 sysroot 与参考 sysroot 路径。它是目标库“使用了正确 glibc”的凭证，
应随构建记录留存。

---

## 5. 主机工具（Windows PE 格式）

> 本节对应“规划中”的 `build_windows_host_tools.py`。脚本交付前，须按此接口
> 手动完成主机工具构建。

### 5.1 工具清单

SDK `bin/` 目录交付以下 Windows PE 可执行文件，全部为 x86-64、无 ARM 代码：

```text
qmake.exe            moc.exe             uic.exe            rcc.exe
qmlcachegen.exe      qmlimportscanner.exe
lrelease.exe         lupdate.exe
```

以及 `bin/` 下配套的 `mkspecs/`、`.prf` 与 qmake 元数据。

### 5.2 构建方式

主机工具使用 **WinLibs MinGW-w64（POSIX/UCRT）** 以 `win32-g++` 规格编译
**静态主机 Qt**，再从中提取上述工具。构建输入：

- qtbase / qtdeclarative / qttools 源码（同版本 5.15.19，见 6.2）；
- WinLibs `mingw32-make.exe`、`gcc.exe` 所在目录；
- Perl（Git for Windows 自带 `usr\bin\perl.exe` 可用）。

主机工具**不使用**交叉工具链。源码在短路径暂存目录（`D:\q5w`）展开，
避免 Qt 私有头文件触发 Windows `MAX_PATH` 限制。

命令行接口：

```powershell
python qt5\scripts\build_windows_host_tools.py `
    --jobs 4 `
    --stage D:\q5w `
    --winlibs-bin "<WinLibs mingw64\bin>" `
    --perl-bin "C:\Program Files\Git\usr\bin"
```

输出：

```text
qt5\build\host-windows\sdk-bin      # 主机工具
qt5\build\host-windows\mkspecs      # 配套 mkspec
```

### 5.3 校验

```powershell
qt5\build\host-windows\sdk-bin\qmake.exe -v
```

必须报告 Qt 5.15.19。每个 `.exe` 须通过 PE 头检查（x86-64、无缺失依赖）。

### 5.4 与目标工具链的界线

主机工具只做工程解析、元对象编译和资源打包，产出的仍是交给交叉编译器的
中间文件。任何情况下 `bin/*.exe` 都不得进入板卡运行目录。

---

## 6. 构建 SDK（从零）

### 6.1 环境准备

**Windows** 需要：Git for Windows、原生 Windows Python 3、WSL2、
WinLibs MinGW-w64（POSIX/UCRT）、Windows `tar.exe`、Qt Creator 20.0.1。

```powershell
git --version
python --version
wsl.exe -l -v
tar.exe --version
$winlibs = Split-Path (Get-Command mingw32-make.exe).Source
& "$winlibs\gcc.exe" --version
Test-Path "C:\Program Files\Git\usr\bin\perl.exe"
```

**WSL**（`ubuntu20.04`）需要：

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential python3 python3-yaml perl pkg-config rsync \
    git curl ca-certificates xz-utils tar gperf bison flex
```

**交叉工具链与 sysroot** 须按第 3 节就位并通过存在性检查。

### 6.2 准备源码

在 Windows PowerShell：

```powershell
cd D:\workspace\luna-workspace\os\graphics
python qt5\scripts\prepare.py
```

`prepare.py` 读取 `qt5\sources.yaml`，经 HTTPS 下载归档、校验 SHA-256、解包
到 `qt5\upstream\`。成功判据为打印 `... source ready`。校验失败会终止，
不得通过修改清单哈希绕过。

> 当前 `sources.yaml` 仅含 qtbase。构建 Windows 主机工具（第 5 节）需要额外
> 的 qtdeclarative、qttools 条目；接入 `build_windows_host_tools.py` 时一并
> 补充。

### 6.3 构建目标库（WSL）

先将源码同步到 WSL 构建副本：

```bash
mkdir -p /home/surest/nanopc-workspace/graphics
rsync -a --delete --exclude build/ --exclude output/ \
    /mnt/d/workspace/luna-workspace/os/graphics/qt5/ \
    /home/surest/nanopc-workspace/graphics/qt5/
ln -sfn /mnt/d/workspace/luna-workspace/os/graphics/mesa \
    /home/surest/nanopc-workspace/graphics/mesa
ln -sfn /mnt/d/workspace/luna-workspace/os/graphics/libdrm \
    /home/surest/nanopc-workspace/graphics/libdrm
```

`--exclude build/` 保留增量结果；每次 Windows 源码变化后重跑此 `rsync`。
真正从零重建时，只删除
`/home/surest/nanopc-workspace/graphics/qt5/build/qt5-armv8a-linux`。

逐阶段构建（`--jobs` 按机器核数，建议不超过 4）：

```bash
cd /home/surest/nanopc-workspace/graphics/qt5
python3 scripts/qt5_build.py --stage configure
python3 scripts/qt5_build.py --stage core            --jobs 4
python3 scripts/qt5_build.py --stage gui-eglfs       --jobs 4
python3 scripts/qt5_build.py --stage kms             --jobs 4
python3 scripts/qt5_build.py --stage widgets         --jobs 4
python3 scripts/qt5_build.py --stage smoke           --jobs 4
python3 scripts/qt5_build.py --stage widgets-display --jobs 4
```

| 阶段 | 作用 | make 目标 |
| --- | --- | --- |
| `configure` | 清理配置缓存、ABI 校验、整理 staging、生成 mkspec、运行 Qt `configure` | — |
| `core` | QtCore | `sub-corelib` |
| `gui-eglfs` | QtGui | `sub-gui` |
| `kms` | 平台支持与 EGLFS/KMS 插件 | `sub-platformsupport`、`sub-eglfs` |
| `widgets` | QtWidgets | `sub-widgets` |
| `smoke` | 交叉编译 `examples/eglfs-smoke` | — |
| `widgets-display` | 交叉编译 `examples/widgets-display` | — |

`configure` 使用 `-platform linux-g++ -xplatform luna-armv8a`，关键开关
`-opengl es2 -eglfs -kms`，关闭 `xcb`/`linuxfb`/`dbus`/`openssl`/`icu`/`pch`，
`-nomake examples/tests`、`-skip qtwebengine`。构建目录固定
`build/qt5-armv8a-linux`。

产物检查：

```bash
file build/qt5-armv8a-linux/lib/libQt5Core.so.5.15.19
cat  build/qt5-armv8a-linux/target-abi.json
```

### 6.4 构建主机工具（Windows）

见第 5 节。命令：

```powershell
cd D:\workspace\luna-workspace\os\graphics
$winlibs = Split-Path (Get-Command mingw32-make.exe).Source
python qt5\scripts\build_windows_host_tools.py `
    --jobs 4 --stage D:\q5w `
    --winlibs-bin "$winlibs" `
    --perl-bin "C:\Program Files\Git\usr\bin"
```

### 6.5 固化目标机运行时

第 6.3、6.4 均通过后，从 Qt SDK、图形 staging 与同一个 Ubuntu 目标 rootfs
生成板端运行时。编译 sysroot 决定头文件和链接 ABI；目标 rootfs 提供实际执行
时的动态加载器和 glibc，二者用途不同。脚本会复制 Qt、插件、字体、示例、
Wayland 库，以及 rootfs 中配套的
`ld-linux-aarch64.so.1`、glibc、libm、libdl、libpthread、librt、libgcc 和
libstdc++，并生成每个文件的 SHA-256 清单：

```powershell
python qt5\scripts\package_runtime.py `
    --qt-root D:\luna-sdk\qt5-5.15.19 `
    --graphics-root D:\luna-sdk\qt5-5.15.19\staging `
    --runtime-root \\wsl.localhost\ubuntu20.04\home\surest\nanopc-workspace\ubuntu-rootfs `
    --output D:\luna-sdk\qt5-5.15.19\runtime
```

输出中的 `runtime-manifest.json` 记录 Qt、图形 staging、目标 rootfs 输入目录、
文件大小和哈希。部署时必须整体
更新 `runtime/`，禁止只替换 libc 或动态加载器。板端曾出现的 MTE/`LDG`
异常就是新 libc 与旧 `ld-linux` 混用导致的 ABI 失配。

Windows SDK 的主机工具、mkspec、头文件与目标库仍保存在
`D:\luna-sdk\qt5-5.15.19`。目标机运行时是其中可独立部署的 `runtime/` 子树。
SDK 组合须满足：

1. 通过 WSL `rsync -aL` 解引用目标树中的 `.so` 符号链接；
2. 合并主机工具 (`bin/`) 与目标树 (`include/`、`lib/`、`plugins/`、`staging/`)；
3. 将 mkspec 与 qmake 元数据中的 WSL / 短路径重写为 SDK 内相对布局；
4. 复制 `mkspecs/luna-armv8a/`、`scripts/`、`examples/` 与 `README.md`。

验收：

```powershell
D:\luna-sdk\qt5-5.15.19\bin\qmake.exe -query
```

必须满足：`QT_INSTALL_PREFIX`、`QT_HOST_PREFIX` 指向交付目录；`QMAKE_XSPEC`
为 `luna-armv8a`；输出中不出现 `/home/surest`、`/mnt/d` 或 `D:/q5w`。

### 6.6 放入 Qt Creator 并注册 Kit

> Kit 注册对应“规划中”的 `register_qtcreator_kit.ps1`。

将 Qt Creator 与官方安装包放入 SDK：

```text
D:\luna-sdk\qt5-5.15.19\tools\QtCreator-20.0.1
D:\luna-sdk\qt5-5.15.19\installer\qt-creator-opensource-windows-x86_64-20.0.1.exe
```

安装包 MD5：`94052A4D2179D28DCB52EA3EFB9C95D0`

关闭 Qt Creator 后注册 Kit：

```powershell
powershell -ExecutionPolicy Bypass -File `
    D:\luna-sdk\qt5-5.15.19\scripts\register_qtcreator_kit.ps1 `
    -SdkRoot D:\luna-sdk\qt5-5.15.19 `
    -QtCreatorRoot D:\luna-sdk\qt5-5.15.19\tools\QtCreator-20.0.1 `
    -WorkspaceRoot D:\workspace\luna-workspace
```

注册脚本依次登记 C/C++ 编译器、GDB、Qt 版本和 `Luna ARMv8A` Kit，写入
sysroot、`luna-armv8a` 与 `MAKEFLAGS=-j4`，并固化 Kit 以防 Qt Creator
重启时清理。在“首选项 → Kits”核对：

```text
Kit:         Luna ARMv8A
Qt:          Luna Qt 5.15.19 ARMv8A
C / C++:     Luna ARMv8A GCC / G++
Debugger:    Luna ARMv8A GDB
Mkspec:      luna-armv8a
Sysroot:     ...\aarch64-none-linux-gnu\libc
Environment: MAKEFLAGS=-j4
```

---

## 7. 使用 SDK

### 7.1 构建示例应用

Qt Creator 打开
`D:\luna-sdk\qt5-5.15.19\examples\widgets-display\widgets-display.pro`，
选择 `Luna ARMv8A` Kit，运行 qmake 后构建。命令行等价：

```powershell
New-Item -ItemType Directory -Force D:\luna-sdk\build\widgets-display
Set-Location D:\luna-sdk\build\widgets-display
D:\luna-sdk\qt5-5.15.19\bin\qmake.exe `
    D:\luna-sdk\qt5-5.15.19\examples\widgets-display\widgets-display.pro
mingw32-make.exe -j4
```

### 7.2 产物检查

```powershell
$readelf = "D:\workspace\luna-workspace\tools\toolchains\aarch64-none-linux-gnu\bin\aarch64-none-linux-gnu-readelf.exe"
& $readelf -h .\widgets-display.elf
& $readelf -d .\widgets-display.elf
```

要求 ELF64、AArch64；动态依赖来自目标 Qt、EGL/GLES、GBM、Gallium、glibc、
libstdc++；不得出现 Windows DLL、x86-64 库或主机构建目录路径。

### 7.3 NanoPC-T4 部署

板端运行目录固定 `/media/mmcblk1p1/qt5`：

```text
qt5/
├── bin/eglfs-smoke.elf
├── bin/widgets-display.elf
├── bin/ld-linux-aarch64.so.1
├── lib/libQt5Core.so.5
├── lib/libQt5Gui.so.5
├── lib/libQt5Widgets.so.5
├── lib/libQt5EglFSDeviceIntegration.so.5
├── lib/libQt5EglFsKmsSupport.so.5
├── fonts/DejaVuSans.ttf
├── plugins/platforms/libqeglfs.so
└── plugins/egldeviceintegrations/libqeglfs-kms-integration.so
```

Mesa 的 `libEGL.so.1`、`libGLESv2.so.2`、`libgbm.so.1`、
`libgallium-25.2.8.so` 放在 `/media/mmcblk1p1/graphics`，DRI 后端放在
`/media/mmcblk1p1/graphics/dri`。Luna 启动时创建权限为 `01777` 的 `/tmp`，
Wayland socket 不再依赖人工建目录。启动环境：

```text
setenv GLIBC_TUNABLES glibc.mem.tagging=0
setenv LD_LIBRARY_PATH /media/mmcblk1p1/qt5/lib:/media/mmcblk1p1/graphics
setenv QT_PLUGIN_PATH /media/mmcblk1p1/qt5/plugins
setenv QT_QPA_PLATFORM eglfs
setenv QT_QPA_EGLFS_INTEGRATION eglfs_kms
setenv QT_QPA_EGLFS_DISABLE_INPUT 1
setenv QT_QPA_FONTDIR /media/mmcblk1p1/qt5/fonts
setenv GBM_BACKENDS_PATH /media/mmcblk1p1/graphics
setenv LIBGL_DRIVERS_PATH /media/mmcblk1p1/graphics/dri
setenv GBM_BACKEND dri
load /media/mmcblk1p1/qt5/bin/widgets-display.elf
```

Wayland 多窗口验收先启动 compositor，再切换客户端平台插件：

```text
setenv XDG_RUNTIME_DIR /tmp
setenv WAYLAND_DISPLAY wayland-0
spawn /media/mmcblk1p1/qt5/bin/wayland-compositor.elf
setenv QT_QPA_PLATFORM wayland
load /media/mmcblk1p1/qt5/bin/widgets-display.elf
load /media/mmcblk1p1/qt5/bin/qt-analogclock.elf
```

验收日志必须出现 `/tmp/wayland-0` 的 bind/listen 和
`libqwayland-generic.so` 成功装载；不得出现 MTE、`LDG` 或解释器 ABI 异常。

`QT_DEBUG_PLUGINS=1` 仅用于定位插件装载问题。实机验收要求：EGLFS 与
`eglfs_kms` 插件均加载成功、DRM/GBM 初始化成功、画面稳定显示，并能通过
`Ctrl+C` 终止后返回 Luna shell。

`widgets-display.elf` 为无输入显示验收程序，画面含标题、只读文本框和默认
勾选的复选框，用于验证 QtWidgets、字体与控件绘制路径。

---

## 8. 验收清单

1. Windows、WSL、WinLibs、Git/Perl、Python 环境检查通过。
2. 交叉工具链与 Luna glibc sysroot 完整。
3. Mesa、libdrm 的 ARMv8A 依赖产物完整。
4. `prepare.py` 下载、SHA-256 校验、解包通过。
5. 源码同步到 WSL，`mesa`/`libdrm` 软链接就位。
6. 七个目标阶段通过，`target-abi.json` 生成且哈希一致。
7. Windows 主机工具生成并通过 PE 检查。
8. SDK 组合到交付目录，`qmake.exe -query` 检查通过。
9. Qt Creator 与安装包放入同一 SDK 根目录。
10. Kit 注册后重启 Qt Creator 仍存在。
11. 示例由 Qt Creator / qmake 构建为 AArch64 ELF。
12. NanoPC-T4 显示与退出回收单独验收。

---

## 9. 故障排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `qmake -query` 出现 WSL 路径或 `D:\q5w` | SDK 主机工具元数据路径未重写 | 重新生成 Windows 主机工具 |
| glibc 启动时发生 MTE/`LDG` 异常 | `ld-linux` 与 libc 来自不同 sysroot | 整体部署 `package_runtime.py` 的输出并核对清单 |
| Wayland 客户端缺少 cursor 库 | 运行时被拆分部署 | 核对 `libwayland-cursor.so.0` 和运行时清单 |
| 找不到 `spec_pre.prf` | 主机 mkspec 打包不完整 | 检查主机工具 `mkspecs/` 是否随 `bin/` 一并打包 |
| `.so` 符号链接缺失 | 未用 `rsync -aL` 解引用目标树 | 组合 SDK 时启用 `-aL` |
| `target ABI mismatch` | Qt 与 loader 使用了不同 sysroot | 核对 `LUNA_QT_SYSROOT`，重跑 `configure` |
| Qt Creator 重启后 Kit 消失 | Kit 固化步骤未完成 | 重跑 Kit 注册脚本 |
| 生成 PE / x86-64 文件 | Qt Creator 选择了错误 Kit | 切换到 `Luna ARMv8A` Kit |
| 链接到 Windows Qt DLL | mkspec、sysroot 或库搜索路径错误 | 检查 `luna-armv8a/qmake.conf` 与 staging 路径 |
| 新构建仍读取旧结果 | 增量缓存未清理 | 删除 `build/qt5-armv8a-linux` 后从 `configure` 重建 |
| `missing ... source library`（EGL/GLES/gbm/gallium/expat/libdrm.a） | Mesa/libdrm ARMv8A 产物缺失 | 先按各仓库说明构建依赖 |
| `Qt configuration requires bash.exe or sh.exe` | 在 Windows 上运行了 `qt5_build.py` | 目标库构建须在 WSL 中执行 |

---

## 附录 A：目录约定

```text
Windows 工作区：   D:\workspace\luna-workspace
图形仓库：         D:\workspace\luna-workspace\os\graphics
Qt 工程：          D:\workspace\luna-workspace\os\graphics\qt5
Windows 短路径暂存：D:\q5w                （主机工具展开，须保持短路径）
WSL 构建副本：     /home/surest/nanopc-workspace/graphics/qt5
WSL 构建目录：     .../qt5/build/qt5-armv8a-linux
最终 SDK：         D:\luna-sdk\qt5-5.15.19
板端运行目录：     /media/mmcblk1p1/qt5
```

`build/`、`output/`、`D:\q5w` 与最终 SDK 目录均为可再生产物，不作为源码提交
到 graphics 仓库。

## 附录 B：环境变量索引

| 变量 | 使用环节 | 见 |
| --- | --- | --- |
| `LUNA_QT_TOOLCHAIN` | 目标库构建 | 3.3 |
| `LUNA_QT_REFERENCE_SYSROOT` | 目标库构建 / ABI 校验 | 3.2、3.3 |
| `LUNA_QT_SYSROOT` | 目标库构建 | 3.2、3.3 |
| `LUNA_QT_BUILD_NAME` | 目标库构建目录名 | 3.3 |
| `QT_MAKE` | 目标库构建 | 3.3 |
| `QT_SHELL` | 目标库 `configure` | 3.3 |
