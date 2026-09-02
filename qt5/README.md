# Qt 5

本工程固定 Qt 5 系列最后一个公开源码版本 5.15.19。第一阶段移植范围为
QtCore、QtGui、EGLFS/KMS 和 evdev，复用 Luna 已有的 libdrm、Mesa GBM/EGL、
glibc 动态进程模型及输入设备接口。QtWebEngine 不在基础移植范围内。

准备源码：

```powershell
D:\workspace\luna-workspace\catboy\catboy.exe build -f build.yaml -p armv8a-user qt5-prepare
```

源码会下载到 `upstream/` 并校验 SHA-256。后续构建目标将按 QtCore、QtGui、
平台插件和示例程序拆分，避免形成不可维护的单体命令。

