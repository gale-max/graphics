# Luna 用户态图形资产

## 当前能力与验收边界（2026-10-20）

| 能力 | 当前证据 | 边界 |
| --- | --- | --- |
| RK3399 Panfrost / DRM / GBM / EGL / GLES | NanoPC-T4 上 Weston 与 glmark2 运行 | 不代表其他 GPU 或 BSP 已验收 |
| Weston 桌面、鼠标、16 窗口 | 用户确认 4×4 独立可见、模型运动和鼠标正常 | 不将客户端数量或 ioctl 返回当作视觉证据 |
| RT / ThreadX 后端图形运行 | 两个后端分别完成 16 客户端 10 分钟测试，人工确认 4×4 运动及鼠标正常，16 PID 均回收 | 可选后端，不表示双内核同时运行，也不替代长测 |
| Qt 应用构建 / SDK 搬迁 | 新位置 SDK 与独立副本构建证据见 SDK_HANDOFF | 不等同于干净机器从零构建完整 SDK |
| timerfd 与资源回收 | 常数时间推进、读后重装及定向主机/板测回归 | 保留真实错误，不能声称所有定时器场景无故障 |
| 日志和 ps | 内核日志带时间/级别；ps 显示 TID、当前 CPU、允许核范围 | shell 回执和应用 stdout 不强加内核日志头 |

最新部署组合、图形模块哈希和可视验收见
[4×4 与 ps 上板记录](docs/GRID16_VALIDATION_20261020.md)。
本轮 RT / ThreadX 镜像哈希、glibc 测试和短测结束证据见
[双后端验收](docs/GLIBC_RT_MIGRATION_20261020.md)，对应代码提交见
[跨仓库提交清单](docs/DUAL_BACKEND_COMMITS_20261020.md)。
日志接口和已移除阶段探针见
[日志清理说明](docs/LOGGING_CLEANUP_20261020.md)。
硬件 WDT 默认不启用；主机压测 guardian 默认保留 85°C 温度保护。
硬件 WDT 复位或未复位都不能单独判定故障属于硬件还是软件。

## 仓库与发布

图形源码由本仓库维护，内核/BSP/兼容层分别位于相邻组件仓库。
`integrated/repo.yaml` 是多仓库构建入口；本机 `os/` 不是可推送的总仓库。
Git remote 名称 `upstream` 在本工作区表示项目的 GitHub 镜像，
不等同于各组件目录中 `upstream/` 的开源来源。不要将移植后的源码声称为
未经修改的上游发行版，也不要把 rootfs、SDK、采集日志混入普通源码提交。

2026-10-20 去除停机排查 trace 的功能版及四小时回归说明见
[图形功能版回归](docs/FUNCTIONAL_RELEASE_20261020.md)。

## 交付与复原入口（2026-10-19）

当前 SDK、源码副本、运行包并不是一个可直接搬迁的自包含发行版。
请先阅读 [SDK 与图形交付整理](docs/SDK_HANDOFF.md)，其中区分已验证编译、
物理板验收、待补依赖和远端上传清单。当前 SDK 位于
`D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19`；旧根目录已由用户删除。
完整运行目录说明见 [RELEASE.md](RELEASE.md)。下面的组件表和命令仅为基础 DRM 路径，
不覆盖全部 Qt/Wayland/Weston 交付流程。

图形资产按组件拆分，每个目录都是独立 Catboy 工程：

| 目录 | 资产 | 输出 |
| --- | --- | --- |
| `libdrm` | libdrm、modetest | `libdrm.a`、`modetest.elf` |
| `mesa` | Mesa 25.2.8、Panfrost、GBM、EGL、GLES2 | 图形运行库 |
| `kmscube` | KMS/GBM/EGL 冒烟测试 | `kmscube.elf` |
| `glmark2` | DRM/EGL/GLES2 性能测试 | `glmark2-drm.elf` |

依赖顺序为：

```text
libdrm -> Mesa Panfrost/GBM/EGL/GLES2 -> kmscube
                                      -> glmark2
```

## Catboy 构建

```powershell
Push-Location graphics/libdrm
D:\workspace\luna-workspace\catboy\catboy.exe rebuild libdrm modetest
Pop-Location
python graphics/mesa/scripts/build_windows.py
Push-Location graphics/kmscube
D:\workspace\luna-workspace\catboy\catboy.exe rebuild kmscube
Pop-Location
Push-Location graphics/glmark2
D:\workspace\luna-workspace\catboy\catboy.exe rebuild glmark2-drm
Pop-Location
python -m pytest graphics/tests -q
```

必须按上述顺序构建。kmscube 和 glmark2 直接链接前序工程的 libdrm 与 Mesa
产物，不能与 libdrm 的 `rebuild` 并发执行。

各工程的 `build/` 仅保存中间文件，不纳入版本管理。完成构建后运行：

```powershell
python graphics/scripts/package_artifacts.py
```

脚本将 Mesa 运行库、glmark2、modetest 和 kmscube 收集到
`artifacts/armv8a-user/`，并生成包含源码 revision、文件大小和 SHA256 的
`manifest.json`。Mesa 的 Panfrost 主机生成材料和目标 lexer 分别固化在
`mesa/generated/panfrost/25.2.8/` 与 `mesa/generated/lexers/25.2.8/`，常规
Windows 构建不依赖 WSL，也不依赖开发者本机的 WinFlexBison 安装路径。

## 固化存储

SD 和 eMMC 的前 200 MiB 作为启动保护区。数据分区起始 LBA 必须不小于
`409600`（512 字节扇区），禁止对整盘设备执行 `mkfs`。图形资产统一部署到
数据分区的 `/graphics` 目录，glmark2 的 `data` 目录必须一并部署。
