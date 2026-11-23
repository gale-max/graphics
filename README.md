# Luna™ 图形与人机交互子系统 (Graphics & Display Subsystem)

> **硬件加速图形渲染栈、DRM/KMS 显示框架与现代化 HMI 运行环境。**

---

## 📌 产品定位与核心价值

本仓库是 Luna OS 面向嵌入式显示与现代人机交互（HMI）的图形子系统工程。

集成 DRM/KMS 显示核心、libdrm 用户态接口、Mesa 3D GPU 硬件加速渲染驱动、Weston/Wayland 窗口合成器与 Qt5 应用程序框架，为智能座舱仪表盘、工业人机终端与边缘可视化大屏提供高帧率、低延迟的硬件加速图形渲染支撑。

---

## 🌲 分支体系与当前分支定位

**当前检出分支**：`dev-linux-runtime` · **Linux 原生图形应用与驱动兼容分支**

> **本分支定位**：通过 linux-runtime 原生运行 Linux 用户态图形中间件与 Wayland/Qt 应用程序。
> 
> **适用场景与目标**：无虚拟化环境下的原生 Linux 图形栈跑通

### 仓库分支规划矩阵 (Branch Matrix)

| 分支名称 (Branch) | 分支角色 (Role) | 核心职责与说明 (Description) | 稳定性 (Stability) |
| :--- | :--- | :--- | :--- |
| `master` | 主线图形集成工程 | 维护与 Luna DRM 组件的接口对齐与图形验证套件（kmscube, glmark2）。 | `Production Stable` |
| `dev-linux-runtime` **(当前分支)** | Linux 原生图形应用与驱动兼容分支 | 通过 linux-runtime 原生运行 Linux 用户态图形中间件与 Wayland/Qt 应用程序。 | `Active Development` |

---

## 🚀 核心能力与关键技术

* **DRM/KMS 现代显示驱动**：基于直接渲染管理器（DRM）与内核模式设置（KMS）实现显存缓冲与多图层硬件混叠。
* **3D GPU 硬件加速**：集成开源 Mesa 图形栈，为 Panfrost 等嵌入式 GPU 提供 OpenGL ES 加速能力。
* **Wayland 窗口管理**：集成 Weston 窗口合成器，支持多窗口隔离与现代触摸交互。
* **Qt5 应用程序框架**：支持标准 Qt Quick / QML 工业图形界面免修改直接运行。

---

## 🛠️ 快速开始与构建指南

本仓库由专为多仓库系统设计的构建工具 **Catboy** 进行依赖管理与自动化构建：

```sh
# 在集成工程中构建包含图形栈的固件：
catboy integrated build -t nanopc-t4-user
```

---

## 📂 目录与架构布局

```text
.
├── libdrm/	# DRM 用户态接口抽象库
├── mesa/	# OpenGL ES / Vulkan 3D 渲染加速库
├── weston/	# Wayland 窗口合成器核心
├── kmscube/ & glmark2/	# 图形性能基准测试与功能验证用例
```

---

## 📄 授权与合规 (License)

复制、分发、修改或以其他方式使用本软件的权利，仅可依据适用的 **Luna™ 软件源代码授权条款 (LSLA)** 获得许可。
授权协议详见仓库根目录下的 `License_zh_CN.txt` 或 `License.txt` 文件。
