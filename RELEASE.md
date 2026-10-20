# 图形分发与复现

## 分发目录

`output/rootfs` 对应板端应用根 `/media/mmcblk1p1`，不是宿主全局 `/`。
保持目录关系，不将所有动态库打散到一个目录：

```text
output/
  manifest.json
  rootfs/
    graphics/            Mesa、glmark2、kmscube、modetest、Weston 和场景数据
    qt5/bin/             Qt 示例程序
    qt5/lib/             同批次 Qt 库和 fonts
    qt5/plugins/         平台、装饰、shell integration 等插件
    lib/                 应用使用的 C/C++ 运行库和解释器
```

`output` 保留测试产物但默认不提交二进制到源码 Git。分发时将完整 output
与对应源码提交清单一起打包。现有 `artifacts` 为历史资产，不代表本轮已验证。
清单中的校验一致只说明文件一致，不代表所有应用已通过运行验收。

## 构建

各工程的来源、生成材料、构建命令分别见 `mesa/README.md`、
`libdrm/README.md`、`glmark2/README.md`、`weston/README.md` 和 `qt5/sdk.md`。
Qt 示例使用同版本 Windows SDK 的 qmake 构建：

```powershell
python qt5/scripts/build_window_examples.py --sdk D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19 --make <mingw32-make.exe的绝对路径>
python qt5/scripts/deploy_window_examples.py --sdk D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19
python qt5/scripts/deploy_window_examples.py --fonts-only --font-directory <TTF字体目录>
```

字体部署必须保留对应许可证；Source Code Pro 可验证数字及英文，不代表中文
字体覆盖完成。SDK 不得混用 Qt、Wayland 插件或 Mesa 构建批次。

## 保存板端已测试资产

板端执行 `ftpd start /media/mmcblk1p1`，Windows 执行：

```powershell
python scripts/package_board_assets.py --host 192.168.137.11
```

默认保存 graphics 和 Qt 目录，不递归打包板端 Ubuntu 的整个 lib 系统目录。
解释器和 C/C++ 库需核对应用实际解析路径，再选取相应文件，不混用别名库。
脚本仅读取指定目录，不更改板端文件。每个文件独立读取两次校验，写入
output/rootfs 并记录 SHA256。板端正在修改文件时不要生成分发包。
清单 complete=false 或导出失败时禁止作为完整产品分发。
运行镜像单独放在 output/firmware，记录集成目标、源码提交号和镜像 SHA256。

## 环境和验收

应用根下配置 LD_LIBRARY_PATH 为 `/graphics/weston:/graphics:/qt5/lib:/lib`，
Qt 插件路径为 `/qt5/plugins`，平台为 wayland，显示名为 wayland-0。
Weston 模块、图片、libinput quirks 与 XKB 数据保持其 share 子目录。
完整启动命令及人工验收见 `weston/VALIDATION.md`。

四实例并发渲染使用 Wayland glmark2；DRM 直出独占显示，不能用四个 DRM
master 实例作为多窗口测试。必须检查场景结束、进程回收、重复启动与错误日志，
不能只依据 spawn 成功或线程存在判断通过。
