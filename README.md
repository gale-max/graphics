# Luna Graphics

嵌入式图形显示与人机交互栈，集成 Framebuffer 硬件驱动、DRM 接口适配以及 LVGL 工业图形库。

## 双模式架构定位

Luna 采用统一的双模式系统架构设计：
- **模式一（非虚拟化 Native SMP）**：为 Native 模式提供低延迟图形渲染后端，支持双缓冲、页面翻转与触摸输入，直接驱动工业触摸屏与显示器。
- **模式二（虚拟化 Type-1 Hypervisor）**：为虚拟化系统提供图形中介（Mediated Display）或独占显示直通，允许特定 Guest Linux 接管物理显示输出。

## 分支说明

| 分支 | 角色 | 说明 |
| :--- | :--- | :--- |
| `dev-linux-runtime` | 活跃演进分支 | 包含双模式特性演进、Linux ABI 兼容层迭代与新外设适配。 |
| `master` **(当前分支)** | 生产稳定主线 | 面向商用产品交付与主线特性集成的稳定版本。 |

> **当前分支 (`master`)**：面向商用产品交付与主线特性集成的稳定版本。

## 核心特性

- **图形框架**：集成 LVGL 8.3 工业图形库与基础 2D 绘图引擎
- **显示后端**：Framebuffer (/dev/fb0) 与 DRM/KMS 显示驱动
- **输入设备**：支持多点电容触摸屏、标准 USB 鼠标与键盘事件输入

## 目录结构

- `mesa/`: Mesa 图形渲染驱动适配
- `libdrm/`: DRM 用户态显示控制接口库
- `kmscube/`: DRM/KMS 3D 旋转立方体渲染测试目标
- `glmark2/`: OpenGL ES 基准性能测试套件

## 快速使用

```bash
# 独立构建 KMS/DRM 显示测试组件
catboy build kmscube

# 独立构建 OpenGL ES 渲染测试组件
catboy build glmark2
```
