# Luna Qt 5 Windows SDK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 WSL 中生成可由 Windows Qt Creator 直接使用的 Qt 5.15.19 qmake SDK，并支持 Luna ARMv8A 的常用桌面与嵌入式 Qt 模块、完整网络、输入、串口和 Wayland Client/Compositor。

**Architecture:** 构建流水线分别生成 Linux 配置工具、MinGW Windows 主机工具和 AArch64 Luna 目标库，最后通过清单组装可移动 SDK。Windows SDK 内的 qmake 使用相对路径 mkspec 调用随包交付的 AArch64 工具链，板端插件和动态库由统一部署清单管理。

**Tech Stack:** Qt 5.15.19、OpenSSL 3.0.18、qmake、Python 3、MinGW-w64、Arm GNU Toolchain 14.3.Rel1、Wayland、libinput、Mesa/EGL/GBM、libdrm、SQLite、Luna loader/POSIX。

## Global Constraints

- Qt 固定为 5.15.19，所有 Qt 子模块版本必须一致；TLS 固定 OpenSSL 3.0.18。
- SDK 应用开发阶段只支持 qmake，不支持 CMake Kit。
- SDK 必须在 Windows 原生运行，不调用 WSL ELF 工具。
- SDK 内不得写入 WSL、Windows 工作区或用户名绝对路径。
- 目标 ABI 必须与 Catboy Windows 工具链 glibc sysroot 一致。
- 注释和文档使用 UTF-8 中文，代码遵循现有 graphics 仓库风格。
- 不通过修改 Qt 绕过 Luna 缺失的标准系统调用。

---

### Task 1: 固化 Qt 子模块和第三方依赖清单

**Files:**
- Modify: `qt5/sources.yaml`
- Create: `qt5/scripts/source_manifest.py`
- Create: `qt5/tests/test_source_manifest.py`
- Modify: `qt5/scripts/prepare.py`

**Interfaces:**
- Produces: `load_manifest(path: Path) -> list[SourceEntry]`
- Produces: 固定版本的 qtbase、qtserialport、qtwayland、wayland、wayland-protocols、libinput、libevdev 和 xkbcommon 源码目录。

- [ ] **Step 1: 编写失败测试，要求每项含名称、版本、URL、SHA-256 和解包目录**

```python
def test_manifest_contains_complete_sdk_sources():
    entries = {item.name: item for item in load_manifest(ROOT / "sources.yaml")}
    required = {"qtbase", "qtdeclarative", "qtsvg", "qtserialport",
                "qtserialbus", "qtwebsockets", "qtnetworkauth", "qtwayland",
                "wayland", "wayland-protocols", "libinput", "libevdev",
                "xkbcommon", "openssl"}
    assert required <= entries.keys()
    assert all(len(entries[name].sha256) == 64 for name in required)
```

- [ ] **Step 2: 运行测试并确认因清单不完整失败**

Run: `python3 -m pytest qt5/tests/test_source_manifest.py -q`
Expected: FAIL，报告缺少 Qt 扩展模块、OpenSSL、Wayland 或输入依赖。

- [ ] **Step 3: 实现结构化清单解析、下载、哈希校验和幂等解包**

```python
@dataclass(frozen=True)
class SourceEntry:
    name: str
    version: str
    url: str
    sha256: str
    directory: str
```

- [ ] **Step 4: 验证清单和准备流程**

Run: `python3 -m pytest qt5/tests/test_source_manifest.py -q`
Expected: PASS。

- [ ] **Step 5: 提交依赖清单**

```bash
git add qt5/sources.yaml qt5/scripts/source_manifest.py qt5/scripts/prepare.py qt5/tests/test_source_manifest.py
git commit -m "qt5: 固化 Windows SDK 源码依赖"
```

### Task 2: 重构多工具链构建目录和 ABI 契约

**Files:**
- Modify: `qt5/scripts/qt5_build.py`
- Create: `qt5/scripts/sdk_paths.py`
- Modify: `qt5/tests/test_build_contract.py`
- Create: `qt5/tests/test_sdk_paths.py`

**Interfaces:**
- Produces: `SdkPaths`，分别暴露 `host_linux`、`host_windows`、`target`、`package_root`。
- Produces: `verify_target_abi() -> dict[str, str]`。

- [ ] **Step 1: 编写失败测试，禁止三个产物集合共享 bin/lib 目录**

```python
def test_build_outputs_are_isolated(tmp_path):
    paths = SdkPaths(tmp_path)
    assert len({paths.host_linux, paths.host_windows, paths.target}) == 3
    assert paths.package_root not in {paths.host_linux, paths.host_windows,
                                      paths.target}
```

- [ ] **Step 2: 运行测试并确认 `SdkPaths` 尚不存在**

Run: `python3 -m pytest qt5/tests/test_sdk_paths.py -q`
Expected: FAIL with import error。

- [ ] **Step 3: 实现目录模型并扩展 ABI 清单**

ABI 清单必须覆盖 `features.h`、`libc.so.6`、`libpthread.so.0`、`libdl.so.2`、
`crt1.o`、`crti.o` 和 `crtn.o`，不一致时打印双方路径及哈希后退出。

- [ ] **Step 4: 运行 Qt 构建契约测试**

Run: `python3 -m pytest qt5/tests/test_sdk_paths.py qt5/tests/test_build_contract.py -q`
Expected: PASS。

- [ ] **Step 5: 提交构建目录重构**

```bash
git add qt5/scripts/qt5_build.py qt5/scripts/sdk_paths.py qt5/tests
git commit -m "qt5: 隔离主机工具和目标库构建"
```

### Task 3: 在 WSL 交叉生成 Windows Qt 主机工具

**Files:**
- Create: `qt5/scripts/build_windows_host_tools.py`
- Create: `qt5/mkspecs/win32-g++-wsl-cross/qmake.conf`
- Create: `qt5/tests/test_windows_host_tools.py`
- Modify: `qt5/scripts/qt5_build.py`

**Interfaces:**
- Consumes: Task 2 的 `SdkPaths.host_windows`。
- Produces: `qmake.exe`、`moc.exe`、`uic.exe`、`rcc.exe` 和对应 Qt 配置文件。

- [ ] **Step 1: 编写 PE 与工具完整性失败测试**

```python
def test_required_windows_tools_are_pe(sdk_root):
    for name in ("qmake.exe", "moc.exe", "uic.exe", "rcc.exe"):
        data = (sdk_root / "bin" / name).read_bytes()
        assert data[:2] == b"MZ"
```

- [ ] **Step 2: 运行测试并确认工具缺失**

Run: `python3 -m pytest qt5/tests/test_windows_host_tools.py -q`
Expected: FAIL with missing `qmake.exe`。

- [ ] **Step 3: 使用 `x86_64-w64-mingw32-g++` 构建同版本主机工具**

构建脚本必须检查 MinGW 编译器，使用独立 shadow build，不修改目标 Qt 构建目录；
完成后执行 `file` 并要求结果包含 `PE32+ executable`。

- [ ] **Step 4: 使用 Wine 做可选自检并校验版本**

Run: `wine build/host-windows/bin/qmake.exe -query QT_VERSION`
Expected: `5.15.19`。没有 Wine 时仅跳过执行测试，PE 格式测试仍为强制项。

- [ ] **Step 5: 提交 Windows 主机工具流水线**

```bash
git add qt5/scripts/build_windows_host_tools.py qt5/scripts/qt5_build.py qt5/mkspecs/win32-g++-wsl-cross qt5/tests/test_windows_host_tools.py
git commit -m "qt5: 增加 Windows qmake 主机工具构建"
```

### Task 4: 构建完整 QtBase 目标模块和可移动 Luna mkspec

**Files:**
- Modify: `qt5/mkspecs/luna-armv8a/qmake.conf`
- Modify: `qt5/scripts/qt5_build.py`
- Create: `qt5/scripts/relocate_mkspec.py`
- Create: `qt5/tests/test_relocatable_mkspec.py`

**Interfaces:**
- Produces: QtCore、QtConcurrent、QtNetwork、QtXml、QtGui、QtWidgets、QtOpenGL。
- Produces: Windows qmake 可读取的 `mkspecs/luna-armv8a/qmake.conf`。

- [ ] **Step 1: 编写失败测试，扫描 SDK mkspec 中的绝对路径**

```python
def test_sdk_mkspec_contains_no_build_host_paths(rendered_spec):
    text = rendered_spec.read_text(encoding="utf-8")
    assert "/home/" not in text
    assert "/mnt/" not in text
    assert "D:/workspace" not in text
    assert "$$[QT_HOST_PREFIX]" in text
```

- [ ] **Step 2: 运行测试并确认当前模板不满足可移动性**

Run: `python3 -m pytest qt5/tests/test_relocatable_mkspec.py -q`
Expected: FAIL。

- [ ] **Step 3: 分离构建 mkspec 与交付 mkspec**

交付 mkspec 使用 qmake 属性定位 SDK 根目录，并引用 `tools/aarch64/bin`、目标
sysroot、Mesa 和 libdrm；保留 `-ffixed-x18`、ARMv8A 和 Luna 目标链接参数。

- [ ] **Step 4: 构建 QtBase 并检查目标库**

Run: `python3 qt5/scripts/qt5_build.py --stage target-qtbase --jobs "$(nproc)"`
Expected: 七个目标模块均生成 AArch64 shared object，且无未解析的构建机路径。

- [ ] **Step 5: 提交 QtBase SDK 模块**

```bash
git add qt5/mkspecs qt5/scripts/qt5_build.py qt5/scripts/relocate_mkspec.py qt5/tests/test_relocatable_mkspec.py
git commit -m "qt5: 完善 Luna QtBase SDK 模块"
```

### Task 5: 构建 evdev/libinput 输入插件和 QtSerialPort

**Files:**
- Create: `qt5/scripts/build_input_stack.py`
- Create: `qt5/scripts/build_qtserialport.py`
- Create: `qt5/examples/input-events/input-events.pro`
- Create: `qt5/examples/input-events/main.cpp`
- Create: `qt5/examples/serial-loopback/serial-loopback.pro`
- Create: `qt5/examples/serial-loopback/main.cpp`
- Create: `qt5/tests/test_input_serial_contract.py`

**Interfaces:**
- Produces: evdev keyboard/mouse/touch、libinput generic plugin 和 Qt5SerialPort。
- Consumes: Luna `/dev/input/event*`、`/dev/tty*`、termios 和 poll。

- [ ] **Step 1: 编写失败测试，要求插件、模块元数据和验收工程齐备**

```python
def test_input_and_serial_deliverables_exist(output):
    assert (output / "plugins/generic/libqevdevkeyboardplugin.so").is_file()
    assert (output / "plugins/generic/libqevdevmouseplugin.so").is_file()
    assert (output / "lib/libQt5SerialPort.so.5").is_file()
```

- [ ] **Step 2: 运行测试并确认目标产物缺失**

Run: `python3 -m pytest qt5/tests/test_input_serial_contract.py -q`
Expected: FAIL。

- [ ] **Step 3: 构建输入依赖、插件和 QtSerialPort**

禁用 udev 枚举后必须保留显式设备路径；SerialPort 的 Unix 实现不得在 Qt 内伪造
termios 成功，缺失语义应由 Luna POSIX 层实现。

- [ ] **Step 4: 交叉构建输入和串口验收程序**

Run: `python3 qt5/scripts/qt5_build.py --stage target-input-plugins --jobs "$(nproc)" && python3 qt5/scripts/qt5_build.py --stage target-qtserialport --jobs "$(nproc)"`
Expected: PASS，产物全部为 AArch64 ELF。

- [ ] **Step 5: 提交输入和串口支持**

```bash
git add qt5/scripts qt5/examples/input-events qt5/examples/serial-loopback qt5/tests/test_input_serial_contract.py
git commit -m "qt5: 增加输入插件和串口模块"
```

### Task 6: 构建 Wayland Client 和 Compositor

**Files:**
- Create: `qt5/scripts/build_wayland_stack.py`
- Create: `qt5/examples/wayland-compositor/wayland-compositor.pro`
- Create: `qt5/examples/wayland-compositor/main.cpp`
- Create: `qt5/examples/wayland-client/wayland-client.pro`
- Create: `qt5/examples/wayland-client/main.cpp`
- Create: `qt5/tests/test_wayland_contract.py`
- Modify: `../components/loader/src/process_syscall.c`
- Modify: `../components/loader/src/socket_syscall.c`
- Modify: `../components/loader/include/process.h`
- Create: `../components/loader/tests/test_wayland_syscall_contract.py`

**Interfaces:**
- Produces: Qt5WaylandClient、Qt5WaylandCompositor、Wayland QPA 和 Wayland EGL 插件。
- Consumes: AF_UNIX、socketpair、poll、mmap、shared memory and process cleanup semantics。

- [ ] **Step 1: 编写失败测试，检查客户端、合成器和主机协议工具**

```python
def test_wayland_sdk_surface(output):
    assert (output / "lib/libQt5WaylandClient.so.5").is_file()
    assert (output / "lib/libQt5WaylandCompositor.so.5").is_file()
    assert (output / "plugins/platforms/libqwayland-egl.so").is_file()
```

- [ ] **Step 2: 运行测试并确认 Wayland 产物缺失**

Run: `python3 -m pytest qt5/tests/test_wayland_contract.py -q`
Expected: FAIL。

- [ ] **Step 3: 构建 Wayland 主机扫描器、目标库和 QtWayland**

主机扫描器进入 host-linux 构建目录，目标 Wayland 库进入 target；QtWayland Client
和 Compositor 使用同一协议生成版本。

- [ ] **Step 4: 在 Luna loader 中实现 Wayland 所需的标准调用并上板验证**

在 `socket_syscall.c` 增加 AF_UNIX `socketpair` 及文件描述符关闭语义，在
`process_syscall.c` 接入 syscall 199，并复用现有 poll waiter 和匿名 mmap 生命周期；
在 `process.h` 中保存进程拥有的本地 socket 对象。先执行
`python -m pytest ../components/loader/tests/test_wayland_syscall_contract.py -q`，
再运行 `load /media/mmcblk1p1/qt5/bin/wayland-compositor.elf` 并启动两个
`wayland-client.elf`。Expected: 两客户端显示、退出、重新连接均成功；无
`unhandled syscall`、内核 panic 或资源泄漏。

- [ ] **Step 5: 分仓库提交 Wayland 支持和 Luna 标准语义修复**

```bash
git add qt5/scripts/build_wayland_stack.py qt5/examples/wayland-* qt5/tests/test_wayland_contract.py
git commit -m "qt5: 增加 Wayland 客户端和合成器"
```

Luna/loader 修改必须在其各自仓库独立提交，不能混入 graphics 提交。

### Task 7: 构建完整网络和常用 Qt 扩展模块

**Files:**
- Create: `qt5/scripts/build_common_modules.py`
- Create: `qt5/examples/network-suite/network-suite.pro`
- Create: `qt5/examples/network-suite/main.cpp`
- Create: `qt5/examples/common-modules/common-modules.pro`
- Create: `qt5/examples/common-modules/main.cpp`
- Create: `qt5/tests/test_common_modules_contract.py`

**Interfaces:**
- Produces: QtSvg、QtQml、QtQuick、QtQuickWidgets、QtSql/SQLite、QtSerialBus、QtWebSockets、QtNetworkAuth 和 OpenSSL 3.0.18 运行库。
- Consumes: QtBase、Luna socket/poll/mmap/clock/file APIs。

- [ ] **Step 1: 编写失败测试，检查模块、插件和 OpenSSL 版本**

```python
def test_common_sdk_modules(output):
    required = ("libQt5Svg.so.5", "libQt5Qml.so.5", "libQt5Quick.so.5",
                "libQt5Sql.so.5", "libQt5SerialBus.so.5",
                "libQt5WebSockets.so.5", "libQt5NetworkAuth.so.5")
    assert all((output / "lib" / name).is_file() for name in required)
    assert (output / "lib/libssl.so.3").is_file()
```

- [ ] **Step 2: 运行测试并确认扩展模块尚未构建**

Run: `python3 -m pytest qt5/tests/test_common_modules_contract.py -q`
Expected: FAIL。

- [ ] **Step 3: 构建 OpenSSL、Qt 网络后端和扩展模块**

QtNetwork 启用运行时 OpenSSL；QtSql 构建 SQLite 插件；QML 主机工具进入 Windows
工具目录，目标 QML/Quick 库和 import 插件进入目标目录。

- [ ] **Step 4: 构建网络和常用模块验收程序**

Run: `python3 qt5/scripts/qt5_build.py --stage target-common-modules --jobs "$(nproc)"`
Expected: 网络程序覆盖 HTTP/HTTPS、TCP/UDP、DNS、代理、WebSocket/WSS；公共模块
程序加载 SVG、QML/Quick、SQLite 和 SerialBus API。

- [ ] **Step 5: 提交常用模块**

```bash
git add qt5/scripts/build_common_modules.py qt5/examples/network-suite qt5/examples/common-modules qt5/tests/test_common_modules_contract.py
git commit -m "qt5: 增加完整网络和常用扩展模块"
```

### Task 8: 组装可移动 Windows SDK 和 Qt Creator Kit 材料

**Files:**
- Create: `qt5/scripts/package_windows_sdk.py`
- Create: `qt5/sdk/qt.conf.in`
- Create: `qt5/sdk/qtcreator-kit.json.in`
- Create: `qt5/sdk/README.md`
- Create: `qt5/tests/test_sdk_package.py`

**Interfaces:**
- Consumes: Tasks 3-6 的 Windows 工具和 AArch64 产物。
- Produces: `qt5-luna-armv8a-5.15.19.zip` 和 `sdk-manifest.json`。

- [ ] **Step 1: 编写失败测试，检查布局、哈希及绝对路径污染**

```python
def test_packaged_sdk_is_relocatable(package_root):
    assert (package_root / "bin/qmake.exe").read_bytes()[:2] == b"MZ"
    assert (package_root / "lib/libQt5Core.so.5").is_file()
    for path in package_root.rglob("*"):
        if path.is_file() and path.suffix in {".conf", ".prf", ".pri", ".pc"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "/home/" not in text and "/mnt/" not in text
```

- [ ] **Step 2: 运行测试并确认 SDK 尚未组装**

Run: `python3 -m pytest qt5/tests/test_sdk_package.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现清单式复制、相对路径重写、哈希和 ZIP 打包**

`sdk-manifest.json` 记录 Qt/依赖版本、目标 triple、glibc ABI 哈希和每个交付文件
SHA-256。上游 `.git`、对象文件、测试缓存和构建目录不得进入 ZIP。

- [ ] **Step 4: 解压到不同目录并重新运行可移动性测试**

Run: `python3 qt5/scripts/package_windows_sdk.py --verify-relocation`
Expected: 两个不同临时目录中的 qmake 查询结果一致。

- [ ] **Step 5: 提交 SDK 打包器**

```bash
git add qt5/scripts/package_windows_sdk.py qt5/sdk qt5/tests/test_sdk_package.py
git commit -m "qt5: 打包可移动 Windows Qt Creator SDK"
```

### Task 9: Windows qmake 和 NanoPC-T4 全功能验收

**Files:**
- Create: `qt5/scripts/test_windows_sdk.ps1`
- Create: `qt5/tests/runtime/acceptance.yaml`
- Modify: `qt5/README.md`
- Create: `qt5/docs/qtcreator-kit.md`

**Interfaces:**
- Consumes: Task 8 的 ZIP。
- Produces: Windows 构建报告和 NanoPC-T4 串口验收日志。

- [ ] **Step 1: 在 Windows 无 WSL 进程参与的环境执行全部 `.pro` 验收工程**

Run: `powershell -ExecutionPolicy Bypass -File qt5/scripts/test_windows_sdk.ps1 -SdkPath D:\workspace\luna-workspace\sdk-test\qt5-luna-armv8a-5.15.19`
Expected: Core、Widgets、OpenGL、SerialPort、SerialBus、Input、HTTP/HTTPS、
TCP/UDP、DNS、代理、WebSocket/WSS、SVG、QML/Quick、SQLite、Wayland Client 和
Compositor 全部编译，`readelf -h` 均报告 AArch64。

- [ ] **Step 2: 部署目标库、插件、字体和示例到 NanoPC-T4 固化存储**

部署脚本须根据 manifest 校验板端文件大小和 SHA-256，不允许混用旧版库。

- [ ] **Step 3: 运行显示、输入、串口、网络、常用模块和 Wayland 验收**

每项保存原始 COM5 日志，使用明确启动标志、运行标志和退出标志；每个应用通过
`Ctrl+C` 返回 shell。

- [ ] **Step 4: 执行 20 轮重复启动退出并检查资源**

Expected: 无 panic、内存故障、残留进程、FD、DRM/GEM 对象或 socket；Wayland
合成器每轮可接纳两个客户端重连。

- [ ] **Step 5: 更新中文文档并提交验收材料**

```bash
git add qt5/README.md qt5/docs/qtcreator-kit.md qt5/scripts/test_windows_sdk.ps1 qt5/tests/runtime/acceptance.yaml
git commit -m "qt5: 完成 Windows SDK 与板端验收流程"
```
