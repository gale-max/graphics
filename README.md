# Luna 嵌入式图形显示与人机交互栈

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-ARMv7--A%20%7C%20ARMv7--M%20%7C%20ARMv8--A-orange.svg)]()
[![Real-Time](https://img.shields.io/badge/Determinism-Sub--2%C2%B5s-brightgreen.svg)]()
[![Build Status](https://img.shields.io/badge/Build-Passing-success.svg)]()

**集成 Framebuffer 硬件驱动、LVGL 8.x 图形引擎与 DRM 适配的工业人机交互方案**

</div>

---

## 1. 概述与产品定位

Luna 是一款面向严苛工业控制与边缘计算场景的下一代硬实时操作系统，采用统一的双模式系统架构设计。本仓库（`graphics`）作为 Luna 操作系统的核心组成部分，承担着关键的系统职能。

### 双模式系统架构中的定位

```
+-------------------------------------------------------------------------------+
|                             Luna 操作系统双模式架构                            |
+-------------------------------------------------------+-----------------------+
|  模式一：非虚拟化（Native）—— 兼容 Linux 的 SMP 硬实时  |  模式二：虚拟化（Hyp）|
|  • 亚微秒级中断与任务调度确定性                        |  • ARMv8-A EL2 裸机   |
|  • AArch64 Linux 5.10 ABI 原生执行（EL0 捕获）         |  • Stage-2 物理强隔离 |
|  • 统一 VFS、POSIX PSE52、lwIP 协议栈                  |  • 多 Guest 混合部署  |
+-------------------------------------------------------+-----------------------+
```

- **在模式一（非虚拟化 Native SMP）中**：
  为 Native 模式提供低延迟图形渲染后端，支持双缓冲、页面翻转与触摸输入，直接驱动工业触摸屏与显示器。
- **在模式二（虚拟化 Type-1 Hypervisor）中**：
  为虚拟化系统提供图形中介（Mediated Display）或独占显示直通，允许特定 Guest Linux 接管物理显示输出。

---

## 2. 分支定位与生命周期矩阵

为了保障工业交付的高稳定性与前沿特性的敏捷演进，本仓库采用规范的分支生命周期管理策略：

| 分支名称 | 角色定位 | 适用场景 | 核心重点 |
| :--- | :--- | :--- | :--- |
| `dev-linux-runtime` | 活跃开发分支 (Active Development) | 面向双模式特性演进、Linux ABI 兼容层迭代与新外设适配 | 紧跟最新的 Linux 5.10 ABI 增强、系统调用转发优化及双模式运行环境扩展。 |
| `master` **(当前分支)** | 生产就绪主线 (Production Mainline) | 面向商用产品交付、主线特性集成与持续回归验证 | 包含稳定成熟的双模式架构、完整的组件协议栈与全部官方支持硬件板级支持包。 |

> **当前分支指引 (`master`)**：本分支的开发与维护严格遵循上述矩阵中 `master` 的定位与工程约束，所有提交均需通过自动化契约测试与无回归验证。

---

## 3. 核心能力与技术规格

- 图形框架：集成 LVGL 8.3 工业图形库与基础 2D 绘图引擎
- 显示后端：Framebuffer (/dev/fb0) 与 DRM/KMS 现代显示驱动
- 输入设备：支持多点电容触摸屏、标准 USB 鼠标与键盘事件输入

---

## 4. 目录架构与模块设计

本仓库遵循高内聚、低耦合的模块化设计，核心代码结构如下：

```
├── lvgl/               # LVGL 8.3 核心引擎与内置组件
├── drivers/            # Framebuffer 驱动与 DRM 硬件接口
└── demo/               # 工业仪表盘与设备控制 UI 演示样例
```

---

## 5. 快速起步与使用指南

### 环境准备与编译构建

# 构建图形演示应用
make TARGET=graphics_demo

---

## 6. 质量工程与测试契约

本仓库代码受 Luna 严格的质量工程体系保护：
- **静态代码检查**：遵循 MISRA C 规范子集与 Google C++ 编码风格，消除未定义行为与隐式转换。
- **自动化测试门禁**：纳入 Luna 统一持续集成（CI）流水线，通过单元测试、POSIX 接口契约与性能延迟回归压测。
- **文档契约保证**：本产品文档与 Sphinx 官方技术文档中心保持 100% 交叉引用一致性。

---
<div align="center">
  <sub>Luna Operating System Project • 工业级双模式硬实时操作系统</sub>
</div>
