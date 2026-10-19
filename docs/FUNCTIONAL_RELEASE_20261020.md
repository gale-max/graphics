# 图形功能版回归

基线 tag：`graphics-stable-20261020`，图形工作副本33个仓库已逐项固定。
tag 保留了 timerfd 修复后的八小时续测版本及当时的诊断代码。

本轮删除停机排查加入的 Runtime 自旋锁记录、SMP 等待探针、tick 分段
记录、IRQ PC/PSTATE 快照、观察器周期心跳及 IRQ 窗口统计、DRM ioctl
阶段表与事件计数、AS 锁记录、OHCI 阶段记录、timerfd 诊断表、进程
syscall/close 阶段记录。MMU 成功慢操作不再打印；真正的超时错误及
释放 AS 锁后提交恢复工作的功能保留。

timerfd 常数时间推进和读取时重装、FIFO 票据锁、进程引用与回收修复
保持不变。硬件 WDT 在 probe 时不启用，本轮不执行 `wdt run confirm`，
也不启用观察线程。主机 guardian 默认启用85摄氏度温度保护；本轮不带
`--diagnostics`，因此没有周期性 DRM/pstate/ticktrace 查询。

全量集成构建及32项功能回归通过。主机测试包括实际 timerfd 回调的
边界压力、票据回绕/并发、MMU 错误传播/恢复边界、DRM 文件桥返回值
保持、WDT 默认关闭。已删除只检查旧 trace 存在的测试；功能测试保留。

候选镜像哈希、板端 CRC、完整启动命令和回执保存在工作副本根目录
`functional-release-deploy-20261020.json`。未经裁剪的启动串口原始字节与
文本分别为 `functional-release-startup-20261020.bin`、
`functional-release-startup-20261020.log`；持续原始流由唯一 COM5 collector
每秒 fsync。启动日志中的前置 WDT trial 是换镜像时的受控复位，不是
新镜像运行期间自行复位。

四小时全场景16窗口验收须单独核对 guardian 结束原因、全部客户端
ESRCH、Weston/shell 响应、温度和用户画面。新版本删除了 DRM 提交计数，
串口字节或网络可达不能证明画面继续运动。当前文件不声明四小时已通过。

远端尚未推送；日志与构建产物不加入源码 Git。
