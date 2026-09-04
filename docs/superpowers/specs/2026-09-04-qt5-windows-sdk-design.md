# Luna Qt 5 Windows SDK 设计

## 目标

在 WSL 中完成全部 SDK 生产流程，输出可在 Windows Qt Creator 中直接使用的
Qt 5.15.19 qmake 交叉编译 SDK。应用开发阶段不得依赖 WSL，生成程序运行于
Luna ARMv8A 用户态进程模型。

SDK 支持 QtCore、QtConcurrent、QtNetwork、QtXml、QtTest、QtGui、QtWidgets、
QtOpenGL、QtSvg、QtPrintSupport、QtQml、QtQuick、QtQuickWidgets、QtSql、
QtSerialPort、QtSerialBus、QtWebSockets、QtNetworkAuth、EGLFS/KMS、常用输入
插件、QtWayland Client 和 Qt Wayland Compositor。QtWebEngine、QtMultimedia、
QtBluetooth、QtNfc、QtLocation、Qt3D、QtCharts 和 CMake Kit 不属于本阶段范围。

## 构建模型

构建使用同一份 Qt 5.15.19 源码，生成三类彼此隔离的产物：

1. WSL 本机工具用于配置和构建目标 Qt。
2. MinGW-w64 在 WSL 中交叉生成 Windows PE 主机工具，包括 `qmake.exe`、
   `moc.exe`、`uic.exe` 和 `rcc.exe`。
3. AArch64 GNU 工具链生成 Luna 目标库、插件和示例程序。

Windows 主机工具不能由 Linux ELF 文件重命名得到。SDK 打包阶段必须用
`file` 或 PE 解析器验证主机工具为 Windows PE，并用 `readelf` 验证目标库为
AArch64 ELF。

目标代码继续使用 Catboy Windows 工具链的 glibc sysroot。构建程序必须校验
`features.h`、`libc.so.6`、启动对象及关键 ABI 文件的 SHA-256，防止 WSL 目标
工具链自带 sysroot 混入 SDK。

## SDK 布局

最终归档使用可移动的相对路径：

```text
qt5-luna-armv8a-5.15.19/
├── bin/
│   ├── qmake.exe
│   ├── moc.exe
│   ├── uic.exe
│   └── rcc.exe
├── tools/
│   ├── bin/mingw32-make.exe
│   └── aarch64/bin/aarch64-none-linux-gnu-*.exe
├── include/
├── lib/
├── mkspecs/luna-armv8a/
├── plugins/
│   ├── platforms/
│   ├── egldeviceintegrations/
│   ├── generic/
│   ├── inputmethods/
│   └── wayland-graphics-integration-client/
├── qml/
├── examples/
├── qt.conf
├── qtcreator-kit.json
└── sdk-manifest.json
```

`qt.conf` 和 qmake 配置必须以 SDK 根目录为基准定位头文件、库、插件、mkspec
及工具链。任何生成文件都不得固化 WSL 路径、Windows工作区路径或个人用户名。

## Qt 模块

### QtBase

QtBase 构建以下模块：

- QtCore、QtConcurrent、QtNetwork 和 QtXml。
- QtGui、QtWidgets 和 QtOpenGL。
- OpenGL ES 2、EGL、GBM、DRM/KMS 和 EGLFS。
- imageformats、platforms、egldeviceintegrations、generic 和 inputmethods 中实际
  可用的插件。
- QtSql 使用随 SDK 构建的 SQLite 插件；不默认引入外部数据库客户端。

EGLFS 保留为 Luna 直接显示的基础 QPA。XCB、LinuxFB、D-Bus 和 ICU 继续按
当前移植约束关闭。

### 网络与安全

QtNetwork 必须覆盖 TCP、UDP、DNS、IPv4/IPv6、HTTP、HTTPS 和代理。SDK 固定
交付 OpenSSL 3.0.18 LTS 目标动态库并构建 Qt 的运行时 OpenSSL 后端，不依赖板端
偶然存在的 TLS 库。QtWebSockets 同时验证 `ws` 和 `wss`，QtNetworkAuth 验证其
HTTP 回调和令牌请求基础路径。Unix domain socket 是 Wayland 和本机进程通信的
共同基础能力。

### 常用扩展模块

- QtSvg 支持 SVG 解码与 Widgets 绘制。
- QtQml、QtQuick 和 QtQuickWidgets 支持声明式界面及 OpenGL ES 场景图。
- QtSql 固定 SQLite 后端并验证建表、事务和并发读取。
- QtSerialBus 构建通用库；具体 CAN 后端仅在 Luna 存在对应设备接口时启用。
- Windows 主机工具还包括 `qmlcachegen.exe`、`qmlimportscanner.exe`、
  `lrelease.exe` 和 `lupdate.exe`。

### 输入

第一组输入后端为 evdev keyboard、mouse 和 touch。第二组为 libinput；如果 Luna
缺少 udev，则使用明确的设备节点或平台配置，不引入伪 udev 实现。每个插件必须
能在运行时被 Qt 插件加载器枚举，并具有独立输入事件验收程序。

### QtSerialPort

QtSerialPort 使用 Luna 的 POSIX 字符设备、`termios`、`poll` 和文件描述符语义。
串口枚举不依赖 sysfs/udev；允许应用通过显式 `/dev/tty*` 路径打开设备。读写、
波特率、超时和关闭回收均需单独验证。

### QtWayland

同时构建 QtWayland Client 和 Qt Wayland Compositor：

- Client 生成 Wayland QPA、Wayland EGL 及必要的客户端图形集成插件。
- Compositor 提供 QtWaylandCompositor 库、协议生成代码和最小合成器示例。
- Wayland、wayland-protocols 和协议扫描器版本固定并写入来源清单。
- 协议扫描器属于主机工具；目标运行库和插件属于 AArch64 SDK。

最小合成器运行在 EGLFS/KMS 上，客户端通过 Luna Unix domain socket 与其通信。
因此 Luna 必须具备 Qt/Wayland 实际使用的 `socketpair`、AF_UNIX、`poll`、`mmap`
和共享内存生命周期语义。缺失系统调用应在 Luna 进程模型中正向实现，不在 Qt
源码中用空函数规避。

## Qt Creator 集成

SDK 只提供 qmake Kit。`qtcreator-kit.json` 记录建议的 Qt Creator 配置，包括：

- Windows `qmake.exe` 路径。
- AArch64 C/C++ 编译器路径。
- `mingw32-make.exe` 路径。
- ABI 名称、sysroot 和目标设备类型。

该文件作为导入材料和人工配置依据，不修改用户 Qt Creator 的全局配置。普通
`.pro` 工程只需声明 `QT += widgets opengl serialport waylandclient` 等模块，不应
包含 Luna 仓库绝对路径。

## 构建与打包

统一 Python 入口提供以下阶段：

1. `host-linux-tools`
2. `host-windows-tools`
3. `target-qtbase`
4. `target-qtserialport`
5. `target-qtwayland`
6. `target-input-plugins`
7. `sdk-package`
8. `sdk-windows-smoke`

每个阶段具有输入清单、产物清单和失败即停止行为。`sdk-package` 只复制清单中的
文件，生成 SHA-256 manifest 和 ZIP，不携带构建目录、对象文件或上游嵌套 Git
元数据。

## 验收

### Windows SDK 验收

在未安装 WSL Qt 的 Windows PowerShell 中执行 SDK 的 `qmake.exe` 和
`mingw32-make.exe`，分别构建以下 qmake 工程：

- QtCore/QtNetwork 基础程序。
- QtWidgets 控件程序。
- QtOpenGL ES 程序。
- QtSerialPort 程序。
- QtNetwork HTTP/HTTPS、TCP/UDP、DNS、代理和 WebSocket 程序。
- QtSvg、QtQml/Quick、QtSql/SQLite 和 QtSerialBus 程序。
- evdev 输入程序。
- Wayland Client 程序。
- Wayland Compositor 程序。

所有输出必须为 AArch64 ELF，动态依赖必须全部由 SDK 或 Luna sysroot 满足。

### Luna 运行验收

在 NanoPC-T4 上依次验证：

- EGLFS/KMS 持续显示和 `Ctrl+C` 完整回收。
- Widgets 字体、文本框、复选框及布局正确。
- OpenGL 连续渲染无黑帧、内存故障或资源泄漏。
- 键盘、鼠标和触摸输入事件可达 Qt 事件循环。
- QtSerialPort 完成双向收发、超时和重复打开关闭。
- HTTP/HTTPS、TCP/UDP、DNS、代理、WebSocket/WSS 均完成连接、收发和断开。
- SVG、QML/Quick、SQLite 和 SerialBus 公共 API 可加载运行。
- Wayland Compositor 启动后至少两个客户端可显示、退出并重新连接。
- 每类程序连续运行和退出 20 次，系统保持可响应且无残留进程、文件描述符、
  DRM/GEM 对象或 socket。

原始构建日志、Windows 编译日志、目标 ELF 元数据和板端串口日志纳入测试结果，
不得以进程仍存活或单次画面出现代替验收标志。
