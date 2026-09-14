# Weston desktop-shell

本目录固定 Weston `9.0.0` 及其 desktop-shell 所需依赖源码，用于在 Luna
ARMv8 用户态运行标准 Weston DRM 合成器。Qt 自定义合成器仅作为基础显示
冒烟工具，不属于最终桌面环境。

## 目录

- `upstream/`：校验到 `sources.yaml` 指定提交的 Weston 源码。
- `dependencies/`：校验到 `dependencies.yaml` 指定提交的依赖源码。
- `generated/`：Ubuntu 20.04 上由 Meson 和 wayland-scanner 生成的配置、协议
  代码及目标源文件闭包；最终 Windows 构建不调用 WSL。
- `scripts/`：源码获取、材料生成和 Windows 构建入口。
- `weston.ini`：Luna DRM、GL renderer 和 desktop-shell 的运行配置。

源码目录不保留上游 `.git`，来源、tag 和完整提交号由 YAML 清单记录。

## 获取与校验源码

```powershell
python scripts/fetch_sources.py
python scripts/fetch_dependencies.py
python -m pytest --import-mode=importlib tests -q
```

重新生成协议和 Meson 目标材料时，可在 Ubuntu 20.04 中运行：

```bash
python3 scripts/generate_wsl_materials.py \
  --source upstream \
  --build /tmp/luna-weston-build \
  --output generated
```

## Windows 构建

产品构建只从 Catboy 进入：

```powershell
D:\workspace\luna-workspace\catboy\catboy.exe build `
  -f build.yaml -p armv8a-user weston-desktop
```

目标产品为 `weston.elf`、`desktop-shell.so`、
`weston-desktop-shell.elf`、`drm-backend.so` 和 `gl-renderer.so`。构建入口会
先检查完整源码闭包和图形 SDK，缺少依赖时直接失败，不生成占位文件。

## 验收范围

完成状态以物理板结果为准：desktop-shell 正常启动；至少两个 Qt 窗口可见、
可移动、可缩放、可切换焦点并能退出重连；Wayland glmark2 全场景无 SG、
IOMMU、page-flip 和资源回收错误。当前源码和生成材料已经固化，Windows
依赖交叉编译及 Weston 上板验收仍在推进中。

