# NanoPC-T4 Weston 多窗口验收

使用 Weston 9.0.0 desktop-shell，不使用 Qt 简化合成器。内核、BSP 和组件
以 debug-weston-input-20260924 为基线，集成 repo.yaml 固定本地分支，构建
结束后检查全部仓库 HEAD，防止 Catboy 自动切回其他 master。

## 输入修复

USB evdev 声明 read_user_buffer=1，读取入口必须使用 copy_to_user。
直接 memcpy 用户地址会在鼠标活动后触发 EL1 Memory fault。修复只在
锁内取出一个事件，解锁后执行用户复制，复制失败返回 EFAULT。

回归包含提取生产 C 函数的用户地址守卫、锁外复制、EAGAIN、首次/中途
EFAULT、短长度。旧 tag 可检测出不安全用户地址写入。物理板诊断版已由
人工确认鼠标光标移动；读取探针记录 4230 个事件、1410 个完整报告，
shell inputstat/ps 正常。临时热路径诊断已经删除，清理版需重新验收。

后续停止探针时串口曾再次无回显，尚未取得退出路径现场。不能把光标
恢复等同于全部进程生命周期稳定；本轮多窗口不运行独立长期探针。

## Windows qmake 构建原版示例

使用固定 Qt 5.15.19 上游 analogclock 和 calculator，不修改其 UI 源码。
它们是独立普通窗口；widgets-display 是全屏显示冒烟，不作为多窗口证明。

```powershell
python qt5/scripts/build_window_examples.py `
  --sdk D:/luna-sdk/qt5-5.15.19 `
  --make <Windows-GNU-make路径>/mingw32-make.exe
```

从 graphics 目录运行。源码来自 qt5/upstream，生成文件在
qt5/build/window-examples，产物与 SHA256 清单在
qt5/output/window-examples。构建串行处理两工程，每个最多 -j4。
SDK、GNU make 和交叉工具链是外部工具；脚本只重定位本次生成的 Makefile，
不修改共享 SDK，不使用原 OS 的 Qt/Mesa 源码或旧 staging 产物。

从 graphics 目录部署，上传后回读 SHA256 校验：

```powershell
python qt5/scripts/deploy_window_examples.py --host 192.168.137.11 --sdk D:/luna-sdk/qt5-5.15.19
```

该步骤同时上传示例 ELF、wayland-shell-integration 与
wayland-decoration-client 插件。只有 platforms 插件不足以提供窗口角色
和标题栏；缺少 xdg-shell 时进程可以存活但不会出现桌面窗口。

## 启动环境

进程根为 eMMC，/dev、/tmp 仍按系统全局资源使用。环境只影响新启动的
应用；本轮不自动 saveenv，不覆盖已有用户环境文件。

```text
setenv LD_LIBRARY_PATH /graphics/weston:/graphics:/qt5/lib:/lib
setenv WESTON_MODULE_MAP drm-backend.so=/graphics/weston/drm-backend.so;gl-renderer.so=/graphics/weston/gl-renderer.so
setenv WESTON_DATA_DIR /graphics/weston/share/weston
setenv XDG_RUNTIME_DIR /tmp/weston-runtime
setenv WAYLAND_DISPLAY wayland-0
setenv QT_QPA_PLATFORM wayland
setenv QT_QPA_PLATFORM_PLUGIN_PATH /qt5/plugins/platforms
setenv QT_PLUGIN_PATH /qt5/plugins
spawn /media/mmcblk1p1/graphics/weston/weston.elf --backend=drm-backend.so --shell=/graphics/weston/desktop-shell.so --idle-time=0
spawn /media/mmcblk1p1/qt5/bin/analogclock.elf
spawn /media/mmcblk1p1/qt5/bin/calculator.elf
inputstat
ps
```

## 人工验收规则

1. 同时看见时钟和计算器两个独立窗口，不以两个进程存在代替可见窗口。
2. 移动鼠标和拖动两个窗口的标题栏，观察光标和窗口连续跟随。
3. 两窗口互相覆盖后移开，无遮挡残影、黑块或重绘停滞。
4. 时钟持续更新；点击计算器按钮，结果和按下状态正确刷新。
5. 切换焦点、关闭一个窗口，另一窗口和桌面保持响应。
6. 再启动已关闭的示例，重复拖动和重绘；检查无 panic、usercopy、
   k_free、SG/IOMMU/page-flip 错误。

日志/进程检查与人工画面确认分别记录。2026-10-08 用户确认两个窗口可见、
均可拖动，补齐字体后计算器文字正常。独立时钟最大化正常；最小化后进程
仍存活，原版 shell 的恢复依赖 Super+Tab，无键盘场景恢复入口未实现。
用户已停止该交互项测试。不能据此宣称所有窗口状态与重复回收均已通过。

## 本轮未通过项

初次 Qt 启动日志提示缺少 xdg-shell 等 shell integration。板端只有平台
和图形 integration 目录，没有 wayland-shell-integration；已从同一 Windows
SDK 上传 shell/decoration 插件并逐文件回读 SHA256，增加 QT_PLUGIN_PATH。
不是通过私有合成器或修改窗口映射规则绕过。

重启并发客户端后出现 buddy 未链接候选与重复释放诊断，随后 shell 无回显。
进一步 C 回归确定：旧共享库注册表在最后引用
归零后、段释放完成前允许同一个条目重新分配，旧释放流程会释放新对象资源。
已使用退役状态保留条目并同步元数据引用计数，实际释放在短锁之外执行。
该退役复用回归已从 RED 转 GREEN，随后新镜像启动两个窗口并获人工拖动确认。
固定尺寸的原版 Qt 计算器最大化触发 xdg-shell 尺寸不匹配并退出，协议校验
未被关闭；该限制保留为未修复项，不列为通过。四实例 glmark2 与长期回收
尚待独立验收。

此修改针对已复现的条目复用竞争，不等于共享库所有初始化/查找借用引用
竞争或全部 buddy 调用者均已验收。恢复的图形 tag 仍保留旧自有动态库装载
路径，不能宣称本轮已经完成 ld-linux 全面迁移。
