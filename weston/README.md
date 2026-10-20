# Weston desktop-shell

本目录固定 Weston `9.0.0` 及其 desktop-shell 所需依赖源码，用于在 Luna
ARMv8 用户态运行标准 Weston DRM 合成器。Qt 自定义合成器仅作为基础显示
冒烟工具，不属于最终桌面环境。

## 目录

- `upstream/`：校验到 `sources.yaml` 指定提交的 Weston 源码。
- `dependencies/`：校验到 `dependencies.yaml` 指定提交的依赖源码。
- `generated/`：Ubuntu 20.04 上由 Meson 和 wayland-scanner 生成的配置、协议
  代码、目标源文件闭包及 XKB rules；最终 Windows 构建不调用 WSL。
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

可用 `LUNA_GRAPHICS_SDK` 指向 SDK 的 `staging` 目录、
`LUNA_GRAPHICS_TOOLCHAIN` 指向匹配工具链的 `bin` 目录。
默认 SDK 路径为同级工作区 `os/luna-sdk/qt5-5.15.19/staging`，
不再依赖已删除的 `D:/luna-sdk` 链接；在没有 SDK 副本的检出目录中必须
显式设置路径。新位置下本轮 Weston 产品已完成重新构建。

入口产品为 `weston.elf`、`desktop-shell.so`、`weston-desktop-shell.elf`、
`weston-keyboard.elf`、`drm-backend.so` 和 `gl-renderer.so`。目标运行时前缀
固定为 `/graphics/weston`，构建产物不会嵌入 Windows 主机路径。输出目录还会
包含 `libexec_weston.so.0`、`libweston-9.so.0` 和
`libweston-desktop-9.so.0`，它们是入口产品运行时必需的 Weston 私有库。
`output/share/weston` 保存 desktop-shell 图片，`output/share/libinput` 保存
输入设备 quirks，`output/share/X11/xkb` 保存固定版本的 XKB 键盘数据；部署
时必须保留这些目录。所有 ELF 的运行时搜索路径在
打包阶段统一为 `$ORIGIN`，禁止把 Windows SDK 或工作空间路径带到目标机。
Mesa、Wayland、Cairo 等公共图形库由统一图形 SDK 和目标 rootfs 提供。构建
入口会先检查完整源码闭包和图形 SDK，缺少依赖时直接失败，不生成占位文件。

Luna 启动入口在 `XDG_RUNTIME_DIR` 未设置时使用
`/tmp/weston-runtime`，并确保目录权限为 `0700`；libinput quirks 默认从
`/graphics/weston/share/libinput` 读取，XKB 数据默认从
`/graphics/weston/share/X11/xkb` 读取。无需再手工创建运行目录或设置主机构建路径。

## 验收范围

### glmark2 observation grid

`weston-grid.ini` enables a glmark2-only four-column grid. The supported row
counts are 2, 3 and 4; the current configuration uses 4 rows for 16 distinct
positions. Windows are scaled without changing client rendering buffer sizes.
Slots wrap only after the configured capacity, so workloads exceeding 16 clients
need a different layout rather than assuming every client remains visible.

The geometry regression checks bounds and pairwise non-overlap for 8, 12 and 16
slots. Physical acceptance still requires checking all 16 visible windows and
mouse input on the deployed desktop-shell and configuration.

完成状态以物理板结果为准：desktop-shell 正常启动；至少两个 Qt 窗口可见、
可移动、可缩放、可切换焦点并能退出重连；Wayland glmark2 全场景无 SG、
IOMMU、page-flip 和资源回收错误。当前源码、生成材料及 Windows ARMv8
交叉构建链路已经固化；物理板 desktop-shell 多窗口与输入验收仍在推进中。
