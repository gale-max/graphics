# 图形调试关键证据

本记录不保存冗长过程日志，不替代硬件验收。

## 修复

- evdev 的 read_user_buffer 路径直接 memcpy 用户地址，鼠标事件触发内核
  Memory fault，FAR 为 0x3fffffac7。修复为锁内取出事件、锁外标准 usercopy。
  人工确认光标移动，独立探针记录 4230 个输入事件。
- 共享库最后引用归零后，在旧资源释放完成前允许注册表条目复用。
  确定性 C 测试复现旧释放器释放新库页面；增加退役状态与短元数据锁后
  回归通过。仍未证明初始化发布及借用查找引用的所有竞争均已消除。
- Qt Wayland shell integration 与字体未部署，补齐同批次插件和字体后，
  人工确认两个窗口可拖动、计算器字体正常。

## 保留缺陷

- 原版计算器布局固定大小，最大化要求 1920x1048，提交 324x338，
  Weston 报 xdg_wm_base error 4，客户端因 Protocol error 退出 code=256。
  未取消协议校验或篡改示例约束。可调整大小的时钟最大化人工确认正常。
- 两个时钟最小化后线程仍为 SUS|SEM，Weston 正常隐藏窗口；无键盘时
  缺鼠标恢复入口。用户停止该功能测试。
- 本轮末串口命令无回显且 FTP 超时，未取得故障原因；不能称长期稳定。

## 四实例预检与分发失败

清理版镜像 SHA256 为 4b51fefc4c1f8ffa66a3aec990ec9ca8723b3952da4c0131b5d3cfaa36809e61。
启动四个 640x360 Wayland glmark2，build:duration=30.0。PID 4、5 正常
exit code=0，单场景分数 64、57，不是完整 glmark2 评分。PID 6、7 仍存活，
SIGTERM 已送达后未观察到退出。用户报告移动时崩溃，但串口 ps 仍响应，
Weston 与部分客户端仍活跃；现有证据未确认整机 panic。回收验收失败。

FTP 回读 graphics/libgallium-25.2.8.so 两次均 21755216 字节，SHA256 分别为：

```text
525f64052b7c3f122d89a781e2fb34038d0182050f7c00254df80be5229e2cbc
344628809029843fa56ffe4679eadac1944c4b2d07b47d2555fb361f5eb1d99d
```

没有并发上传，不能发布完整图形分发包。原因可能涉及读取/传输/缓存或
内存破坏，当前未完成分层定位，不能直接判定 ext4 或物理 eMMC 故障。
Qt 示例、运行库、字体、插件另行双读校验共 63 个文件一致；仅是该子集校验。

## 基线

副本路径为 D:/workspace/codex-workspace/luna-graphics-20261008/os。
33 个仓库基于 debug-weston-input-20260924，20 个 master 与该 tag 相同。
其余仓库的较新 master 含 Linux-native Runtime 改动，不得静默混合。
最初未经 pin 的集成构建切换了仓库分支，相关早期实验不计入图形基线验收。
后续构建逐仓库检查 HEAD，记录零基线偏移。
