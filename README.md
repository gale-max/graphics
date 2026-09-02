# Luna 用户态图形资产

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
