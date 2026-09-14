# Luna Weston Desktop Shell 移植设计

## 1. 目标

在现有 Luna DRM/KMS、Mesa Panfrost、GBM/EGL 和 Wayland 运行时基础上，
引入 Weston 9.0.0 的 `desktop-shell`，替代自定义 Qt 示例承担正式窗口管理。
现有 Qt Wayland compositor 更名并收敛为 smoke 工具，只验证客户端连接、
缓冲提交、双窗口显示和基础输入，不继续扩展桌面策略。

在 Weston 之前先完成 Linux Runtime 原子操作边界重构：Linux 兼容头只表达
Linux 原子语义，所有目标原子操作通过 OSAL 进入 Luna 原子基础设施，目标代码
不得直接依赖 GCC `__atomic_*` 内建函数。

## 2. 边界

### 2.1 Linux Runtime 原子操作

`components/linux-runtime/include/linux/atomic.h` 保留 Linux 5.10 风格的
`atomic_t`、`atomic_long_t`、`atomic64_t` 及其操作，但实现只调用
`linux_osal_atomic*` 接口。

`components/linux-runtime/include/linux/runtime_osal.h` 定义 32 位、机器字和
64 位原子读写、交换、比较交换、加减接口。Luna 适配实现调用
`luna/atomic.h` 提供的标准操作；架构组件只负责实现对应宽度的原子指令。
Linux Runtime 不直接包含架构头，也不直接调用 `arch_*`。

主机测试使用测试 OSAL 实现。编译器内建函数可以存在于测试适配层，但不得出现于
Linux Runtime 的公共 Linux 兼容头和 Luna 目标适配层。

### 2.2 Qt Wayland smoke compositor

现有 `qwindow-compositor` 源码保留在 Qt 测试资产中，产物明确命名为
`qt-wayland-smoke-compositor`。默认布局改为双列，保证两个顶层窗口不会完全
遮挡。它只承担以下回归：

- Wayland socket 创建和客户端连接；
- 两个顶层 surface 同时显示；
- 鼠标移动、窗口拖动和基础缩放；
- 客户端退出、资源释放和再次连接。

### 2.3 Weston 产品 compositor

在 `graphics/weston` 固定 Weston 9.0.0 源码、SHA-256、Luna 补丁、配置材料、
Catboy 工程和部署说明。启用：

- `desktop-shell`；
- DRM backend；
- GL renderer；
- xdg-shell、wl-shell、shared-memory 和 Linux dmabuf 路径；
- 多窗口移动、缩放、焦点、层级和客户端生命周期；
- 无输入设备启动选项及后续 evdev 输入接入。

首版关闭 XWayland、RDP、PipeWire、systemd/logind、FreeRDP、VAAPI、LCMS、
Remoting、VNC 和测试套件，避免把 Linux 桌面服务带入 Luna。

## 3. 构建模型

源码准备和配置生成沿用 Qt/Mesa 的两阶段模型：

1. Windows 脚本下载并校验 Weston 9.0.0 源码。
2. Ubuntu 20.04 WSL 使用 Meson 生成配置头、协议源文件和精确源文件清单。
3. 生成材料写入 `graphics/weston/generated` 并接受一致性测试。
4. Windows Catboy 使用现有 ARMv8A glibc 工具链编译目标对象并链接 ELF/共享库。
5. Catboy 构建不得调用 WSL，也不得读取 WSL 构建目录。

生成材料中不得固化用户名、WSL 绝对路径或 Windows 工作区绝对路径。Weston、
Wayland、Mesa、libdrm 和 Qt 客户端必须使用同一目标 sysroot 与 glibc ABI。

## 4. Luna 平台适配

优先复用 Weston 核心，不修改窗口状态机。Luna 差异集中在以下适配边界：

- 事件循环：映射到现有 `poll/epoll`、timer 和 AF_UNIX；
- 进程环境：通过 loader 的环境和根路径模型查找模块、配置与资源；
- DRM：使用 `/dev/dri/card0`、page flip、dmabuf 和现有 IOMMU/SG 实现；
- GBM/EGL：复用已验收的 Mesa Panfrost 运行库；
- 输入：首轮允许无输入启动，随后接入 Luna evdev 兼容设备；
- 日志：命令输出使用无时间戳打印，诊断日志保留 Weston scope 信息。

不在 Weston 内新增 Luna 私有窗口协议，不复制 DRM、GBM、EGL 或输入驱动。

## 5. 验收

### 5.1 原子层

- Linux Runtime 公共代码中不存在 GCC `__atomic_*`；
- 32 位、机器字和 64 位原子语义测试通过；
- Linux Runtime 全部单元测试通过；
- NanoPC-T4 集成镜像完成构建，现有 DRM glmark2 回归无退化。

### 5.2 Qt smoke

- 同时启动两个 Qt Wayland 客户端，两个窗口均清晰可见；
- 窗口可移动，客户端退出后窗口消失；
- 重复连接不残留线程、FD、socket、GEM、BO 或映射。

### 5.3 Weston desktop-shell

- Weston 使用 DRM backend 与 GL renderer启动；
- Qt 多窗口可以显示、移动、缩放、切换焦点并正常退出；
- `glmark2-wayland` 全场景完成且无 SG、IOMMU、page-flip 或 surface 生命周期错误；
- compositor 和客户端可连续重复启动；
- 板端日志无 panic、内存越界、资源泄漏和持续关中断超时；
- 源码准备、WSL 配置生成、Windows Catboy 构建和部署步骤可按文档复现。

## 6. 提交策略

原子层、Qt smoke 和 Weston 分别形成独立提交。每阶段通过对应测试后提交；最终
上板验收通过后，更新 graphics 父仓库说明并推送所有受影响仓库。
