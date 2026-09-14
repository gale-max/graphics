# Luna Weston Desktop Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Luna OSAL 原子接口替换 Linux Runtime 的 GCC/架构直连实现，并交付可由 Windows Catboy 复现构建的 Weston 9.0.0 desktop-shell。

**Architecture:** Linux 兼容头只保留 Linux API，目标操作通过 Runtime OSAL 进入 Luna 原子层。Weston 上游窗口状态机保持不变，WSL 只生成配置与协议材料，Windows Catboy 编译固定源文件清单；现有 Qt compositor 仅作为双窗口 smoke 工具。

**Tech Stack:** Luna OSAL、ARMv8A 原子指令、Python/pytest、Weston 9.0.0、Wayland、DRM/KMS、GBM/EGL、Mesa Panfrost、Meson、Catboy、Qt 5.15.19。

## Global Constraints

- 目标 Linux Runtime 公共代码不得调用 GCC `__atomic_*` 或 `arch_*`。
- Weston 固定为 9.0.0，启用 desktop-shell、DRM backend 和 GL renderer。
- WSL Ubuntu 20.04 只生成材料；Windows Catboy 最终构建不调用 WSL。
- 所有目标产物使用现有 ARMv8A glibc sysroot。
- 不提交 build、output、串口日志、clangd 缓存和绝对路径。

---

### Task 1: 建立 OSAL 原子契约

**Files:**
- Modify: `components/linux-runtime/tests/test_luna_atomic_codegen.py`
- Create: `components/linux-runtime/tests/test_atomic_osal_contract.py`
- Modify: `components/linux-runtime/include/linux/runtime_osal.h`
- Modify: `components/linux-runtime/include/linux/atomic.h`
- Modify: `components/linux-runtime/src/osal/luna_runtime_osal.c`

**Interfaces:**
- Produces: `linux_osal_atomic32_*`、`linux_osal_atomic_long_*`、`linux_osal_atomic64_*`。

- [x] 编写失败测试，要求公共原子头只调用 OSAL 且不存在 GCC/arch 原子调用。
- [x] 运行专项测试并确认因 OSAL API 缺失失败。
- [x] 定义带明确旧值/新值返回语义的 OSAL 原子接口。
- [x] 用 OSAL 调用重写 Linux 原子兼容函数。
- [x] Luna 强实现调用 `luna/atomic.h` 和 Luna 按宽度交换接口。
- [x] 运行专项及 Linux Runtime 全套测试。

### Task 2: 集成回归原子重构

**Files:**
- Modify only when required by build failures: `luna/include/luna/atomic.h`
- Modify only when required by build failures: `luna/include/luna/arch/atomic.h`
- Modify only when required by build failures: `components/arch-armv8a/src/atomic.c`

**Interfaces:**
- Consumes: Task 1 的 Runtime OSAL 原子契约。
- Produces: 不依赖编译器原子运行库的 NanoPC-T4 镜像。

- [x] 使用 `.catboy_lock` 协调集成构建。
- [x] 清理并完整构建 NanoPC-T4 user 目标。
- [x] 检查 ELF 未引入 `__atomic_*` 未解析符号。
- [ ] COM5 启动并运行 DRM glmark2 smoke。
- [ ] 独立提交 Linux Runtime/Luna/arch 的原子改动。

### Task 3: 收敛 Qt smoke compositor

**Files:**
- Modify: `graphics/qt5/examples/qwindow-compositor/compositor.cpp`
- Modify: `graphics/qt5/examples/qwindow-compositor/qwindow-compositor.pro`
- Create: `graphics/qt5/tests/test_smoke_compositor_layout.py`
- Modify: `graphics/qt5/README.md`

**Interfaces:**
- Produces: `qt-wayland-smoke-compositor`。

- [x] 编写失败测试，要求 smoke 命名和不重叠双列布局。
- [x] 实现双列窗口布局并保留拖动、缩放和全屏状态处理。
- [x] 在 WSL 中构建 compositor，在 Windows 侧打包部署材料。
- [ ] COM5 同时启动两个 Qt 客户端并验证显示、移动、退出和重连。
- [ ] 提交 Qt smoke 资产。

### Task 4: 固定 Weston 源码与生成材料

**Files:**
- Create: `graphics/weston/sources.yaml`
- Create: `graphics/weston/scripts/fetch_sources.py`
- Create: `graphics/weston/scripts/generate_wsl_materials.py`
- Create: `graphics/weston/tests/test_source_manifest.py`
- Create: `graphics/weston/tests/test_generated_materials.py`
- Create: `graphics/weston/generated/`

**Interfaces:**
- Produces: 校验过的 Weston 9.0.0 源码和不含绝对路径的生成材料。

- [x] 编写来源清单和生成材料失败测试。
- [x] 下载并校验官方 Weston 9.0.0 源码。
- [x] 在 Ubuntu 20.04 WSL 关闭非目标功能并生成配置头、协议代码和源清单。
- [x] 将生成材料同步回 Windows 并运行可复现性检查。

### Task 5: Windows Catboy 构建 Weston

**Files:**
- Create: `graphics/weston/build.yaml`
- Create: `graphics/weston/include/luna_weston_config.h`
- Create: `graphics/weston/platform/luna/`
- Create: `graphics/weston/tests/test_build_contract.py`

**Interfaces:**
- Consumes: Task 4 的生成材料、现有 Wayland/libdrm/Mesa 产物。
- Produces: `weston.elf`、`desktop-shell.so`、DRM backend 和 GL renderer 模块。

- [ ] 编写 Catboy 目标、依赖和产物契约失败测试。
- [ ] 实现 Luna 事件、环境和进程适配边界。
- [ ] 按生成源清单建立 Weston core、desktop-shell、DRM backend 和 GL renderer 目标。
- [ ] 在 Windows 执行 Catboy 构建并检查 ELF ABI 与动态依赖。

### Task 6: Weston 上板验收与产品文档

**Files:**
- Create: `graphics/weston/README.md`
- Create: `graphics/weston/weston.ini`
- Modify: `graphics/README.md`
- Modify: `graphics/qt5/sdk.md`

**Interfaces:**
- Consumes: Task 5 的 Weston 产物。
- Produces: 可部署 desktop-shell 和完整复现说明。

- [ ] 部署 Weston、shell、Mesa、Wayland 和 Qt 客户端到 eMMC。
- [ ] 验证两个 Qt 窗口显示、移动、缩放、焦点、退出和重连。
- [ ] 运行 Wayland glmark2 全场景并检查 SG/IOMMU/page-flip 日志。
- [ ] 重复 compositor/client 生命周期测试并核对资源回收。
- [ ] 更新构建、部署和验收文档。
- [ ] 清理临时文件，逐仓库运行 `diff --check` 和测试后提交、推送。
