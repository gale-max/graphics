# Mesa Panfrost

本目录固定 Mesa `25.2.8`、Luna 补丁、Meson 选项和 Panfrost 构建阶段。
Windows 入口统一为 Catboy，配置脚本使用 Windows Python，不依赖固定 WSL 路径。

```powershell
D:\workspace\luna-workspace\catboy\catboy.exe build -f build.yaml -p armv8a-user mesa-panfrost
```
