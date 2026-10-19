# Luna SDK 与图形交付整理

审计日期：2026-10-19。本文以当前工作副本为准，不代表干净机器完整复原验收。
未操作板卡、串口、现有长测或远端服务器；根目录清理由用户执行。

## 搬迁后实际验证（最新状态）

用户已删除 `D:/graphics` 和 `D:/luna-sdk` 兼容链接，当前 SDK 位于
`D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19`。
首次实际 qmake 配置失败，原因是 mkspec 和模块元数据仍引用旧 SDK 路径；
仅查询 qmake 版本不能作为搬迁验收。已备份并重定位175个元数据文件，
备份在 `D:/workspace/codex-workspace/luna-sdk-moved-check/metadata-backup`。

随后直接使用新位置 qmake 编译 analogclock、calculator、dynamicscene、
minimal-cpp，全部退出码0，readelf确认全部为ELF64 AArch64。
四个SHA256均与下表独立SDK验证结果相同。生成的Makefile及扫描的
bin/mkspecs/lib配置文件均未发现 `D:/luna-sdk` 或 `D:/graphics` 引用；
两个旧目录实际不存在，未重建兼容链接。
产物在 `D:/workspace/codex-workspace/luna-sdk-moved-check` 下各示例目录。

此搬迁SDK仍使用外部 `D:/workspace/luna-workspace/tools/toolchains` 和原源码头文件，
不要与下述自带工具链的独立副本混淆。新产物未部署到板卡；保留Wayland上游示例
的赋值条件括号警告。后续各节中的旧目录位置是历史盘点，不是当前默认路径。

## 独立 SDK 副本验证更新

已生成 `D:/workspace/codex-workspace/luna-sdk-standalone-20261019-v2`。
其中包含 Windows qmake 等工具、Qt 目标库、匹配交叉工具链及 sysroot、
Mesa/GBM/libdrm 头文件、示例、plugins/qml/staging。16903 个文件的哈希见
该目录 `sdk-copy-manifest.json`。IDE、安装器和重复 runtime 未纳入。
Windows Python 3.11+、GNU make 及适用 shell 仍是宿主前提。

生成入口（在 graphics 根执行；目标必须不存在）：

```powershell
python qt5/scripts/export_sdk_copy.py --source D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19 --toolchain D:/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu --graphics D:/workspace/codex-workspace/luna-graphics-20261008/os/graphics --output D:/workspace/codex-workspace/luna-sdk-export-new
```

脚本不会覆盖既有目标；`--refresh-metadata` 仅用于已有导出目录，其清单中的
四项源/目标路径必须全部匹配，重新从原SDK生成元数据与哈希清单。
此脚本是从已安装 SDK 导出，不是从上游源码编译 SDK。
导出配置绑定目标位置，不能直接移动后宣称仍有效；换位置应重新导出。

本机直接调用新SDK的qmake和内置交叉工具链，无原示例构建脚本路径修补，
以下四个示例完成编译/链接；测试目录位于
`D:/workspace/codex-workspace/luna-sdk-verification-20261019/v2-*`：

| 示例 | SHA256 |
| --- | --- |
| analogclock | 398aa8e9b80c8a68dbc57256ff81e8854c02ca602f51d4dddfc2c36ab99b53b9 |
| calculator | e748a6e09122ff03668d4b8345a4f6b44c54982dfd9c77f772c779460c928c76 |
| dynamicscene (Quick/QML) | b7da03b4ee9e3511ed2b5b89ffed731f0fbfb4f44582e7b4e3a304f0a3488c24 |
| minimal-cpp (Wayland compositor) | 0eb84b7bbefb09575354cf0373cf1ae3ebdb6795a34b4e5d3e83c17a3705033f |

Wayland 上游示例有一条赋值作为条件的括号警告，未当错误隐藏。
metadata 路径扫描已清除已知旧 SDK/工作区/WSL 路径；这不是禁止原目录访问的
沙箱证明，也不是 CMake 或所有模块的构建验收。未部署新应用到正在长测的板卡。

## D 盘 graphics 清理结论

实际目录为 `D:/graphics`，37文件，1334367字节（约1.27 MiB）。相关两份图形仓库
及SDK配置扫描未发现其显式路径引用，但这不是全盘所有程序依赖扫描。
4个Weston二进制未在所查同名产物中找到同哈希副本，因此不能声称全是重复文件。
完整副本已保存在 `D:/workspace/codex-workspace/luna-sdk-recovery-20261019/d-root-graphics`，
37文件逐项SHA256验证一致，清单位于同级 `d-root-graphics.manifest.json`。
保留此备份后，原目录可作为清理候选；本次没有执行删除。
注意板端 `/graphics` 是另外的路径，不能删除板端运行目录。

## 历史盘点与目录职责

| 位置 | 实际用途 | 处理 |
| --- | --- | --- |
| `D:/luna-sdk/qt5-5.15.19` | Windows 主机工具、ARM64 Qt 库、插件、示例、SDK 脚本 | 保留；当前不是可任意搬迁 SDK |
| `D:/luna-sdk/build`、`demo-build`、`header-test` | 历史构建/验证目录 | 待核对唯一文件后才可清理 |
| `D:/graphics/weston` | Weston 模块及 share 数据，非完整源码仓库 | 保留；未证明与分发包逐文件相同 |
| `D:/workspace/luna-workspace/os/graphics` | 原工作仓库 | 不覆盖其未提交修改 |
| `D:/workspace/codex-workspace/luna-graphics-20261008/os/graphics` | 当前板测图形工作副本 | 本次文档和复原材料保存处 |
| 当前副本 `output/rootfs` | 目标运行目录快照 | 发布前重新验证清单覆盖范围 |

SDK 主要体积：IDE tools 825.8 MiB、安装器 380.9 MiB、runtime 254.7 MiB、
目标 lib 196.0 MiB、src 118.3 MiB、bin 68.8 MiB。这是文件长度合计，
不是可释放空间或重复文件证明。IDE/安装器可作为可选包，不应与最小 SDK 混装。
不要清理 D 盘虚拟磁盘、Qt、WSL 或其他无关项目。

## 已验证的 Qt 应用编译

在本目录的上级 graphics 根目录执行：

```powershell
$make = (Get-Command mingw32-make).Source
python qt5/scripts/build_window_examples.py --sdk D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19 --make $make
```

2026-10-19 本机重编译退出码 0：

| 应用 | 字节数 | SHA256 |
| --- | ---: | --- |
| analogclock.elf | 85080 | a47f1a208bc757d11ba03595e5e3c9e7816f9d2508e3c3487d1be8ded4a44a4c |
| calculator.elf | 89824 | 7d91ee215354f0fee72c7091cdb1d91bca574eadfb008394eaaef2c4d9266912 |

输出在 `qt5/output/window-examples`，附构建 manifest；readelf 确认 analogclock 为
ELF64 AArch64 EXEC。此次没有部署这两个新产物或验收其板端运行。

SDK 的 `bin/qt.conf`、`mkspecs/luna-armv8a/qmake.conf` 引用了
`D:/luna-sdk/qt5-5.15.19`、外部 `tools/toolchains/aarch64-none-linux-gnu`、
其 libc sysroot，以及原图形源码头文件路径。仅复制 SDK 文件夹不能保证换机编译。
现有示例构建脚本会修正生成 Makefile 中的历史路径，但这不是通用 SDK 重定位方案。

## 从源码复原的依赖顺序

1. 固定 graphics、OS/loader、Catboy 和 Windows/WSL 交叉工具链版本；保存本地补丁。
2. 按 `libdrm/README.md` 和 `mesa/README.md` 构建 libdrm、Mesa/GBM/EGL/GLES。
3. 按 `weston/README.md` 构建 Weston 及全部模块、协议生成材料、输入和键盘数据。
4. Qt 目标库按 `qt5/scripts/prepare.py`、`sources.yaml`、`qt5/scripts/qt5_build.py`
   的阶段接口在 WSL 构建；glibc、动态加载器、crt 和头文件必须与目标 ABI 同批。
5. Windows qmake/moc/uic/rcc 等主机工具与 ARM64 目标安装树组合 SDK。
6. 编译 Qt 示例，按 glmark2 文档/build.yaml 区分 DRM 与 Wayland 产品。
7. 按 `RELEASE.md` 组织完整运行目录、字体许可证、场景数据和动态库依赖，再验收。

现有 `qt5/sdk.md` 仍将部分 Windows 脚本标记为规划中，而已安装 SDK 内存在实现。
这些独有文件已原样保存到 `qt5/sdk-recovery/scripts`，安装版说明保存为
`qt5/sdk-recovery/installed-sdk-guide.md`，另有 SHA256 清单。
这是防丢失快照，不是已集成构建入口：脚本 ROOT 使用自身目录推导，不能直接在
sdk-recovery 内执行并期待找到 upstream/build。必须先审查并集成到 qt5/scripts，
校验与 sources.yaml、目标构建脚本和实际模块版本一致，再进行空目录复原。

## 图形能力与边界

| 层 | 当前材料/证据 | 不应推导的结论 |
| --- | --- | --- |
| Mesa 25.2.8/Panfrost | GBM、EGL、GLES2 运行库及构建材料 | 不等于 Vulkan、完整桌面 OpenGL 或所有 GPU 支持 |
| glmark2 | DRM 直出与当前板测 Wayland 多窗口 | DRM master 不能当多个普通窗口并发 |
| Weston 9 | DRM backend、GL renderer、desktop-shell、输入/XKB数据 | 不能只交 weston.elf 丢掉模块和 share |
| Qt 5.15.19 | Widgets 示例本机重编译通过；SDK含QML、Quick、Wayland库 | 库文件存在不等于每个模块/应用实机验收 |
| 内核与长测 | timerfd修复镜像16窗口90秒短测，用户确认正常；8小时进行中 | 未完成长测、未证明所有历史冻结根因相同 |

当前短测内核 BIN SHA256：
`5eb1cf6d9e979b3f06f44e85f094f38ca0f4b5fdd0fba67f750e6a18d5e6cad2`。
QtWebEngine、中文字体覆盖和全模块兼容性不列为已验收能力。

## 远端应该上传什么

源码与大产物分开管理，先归档再清理，未执行任何 push/upload。

- **源码 Git**：graphics 源码、补丁、generated 材料、sources/dependencies YAML、
  构建/打包/验证脚本、README、测试、SDK recovery 文件；依赖的 OS 各子仓库和
  Catboy 各自保存提交号与未提交补丁。不能只上传 HEAD 丢掉工作树修改。
- **SDK 发布仓库/文件服务器**：主机工具、目标头/库/plugins/qml/mkspecs/staging、
  对应交叉工具链与匹配 sysroot、版本清单、许可证和 SHA256；IDE/安装器独立可选包。
- **运行产物仓库**：rootfs 下 graphics、Weston模块/share、glmark2 data、qt5/bin/lib/
  plugins/qml/fonts、实际需要的解释器与 C/C++ 库，以及 firmware 和验收报告。
- **重建离线材料**：上游归档和校验值、工具链包、必要 host 依赖与生成工具版本。
  分发第三方代码、字体、Qt和工具链前检查各自许可证及源码提供要求。
- **不要上传**：凭据、SSH私钥、个人QtCreator配置、无关虚拟磁盘、临时build/cache、
  全部历史串口日志。故障日志只选取对应镜像/轮次必要证据，原始日志另作受控归档。

当前 graphics origin 为 `ssh://git@192.168.31.6:2222/luna/graphics.git`；
该地址仅是本地配置，不证明远端可达或拥有上传权限。
原工作仓库 HEAD `66c1ff75f2f92c963b7ccefcf2a7d23cf9793fcb`，
当前副本 HEAD `a6a83823d81ef717ff8f61e039fac690d48c7fb7`，两处都有未提交改动。
必须审查差异后选择发布基线，不互相覆盖。

## 发布阻断项

- 未完成独立机器/空工作区全流程 SDK 复原，尚不能保证别人从源码完整重建。
- `output/manifest.json` 的 complete=true 只声明 qt5/bin、qt5/lib、qt5/plugins
  三个导出目录完成，不能当 graphics、firmware、所有依赖齐全的证明。
- 还需统一 SDK 主机脚本、消除绝对路径、固定完整工具链/依赖哈希并做依赖闭包检查。
- 用户已删除 D:/graphics；独有 Weston 文件保存在上述 recovery 备份中，发布前应决定是否纳入运行产物，不能丢弃备份。历史 build 目录仍需逐文件核对。
