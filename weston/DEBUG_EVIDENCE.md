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

## 后续退出定位

不运行 FTP 导出，仅启动 Weston 和四个 640x360 Wayland glmark2，
build:duration=15.0。四个客户端均 exit code=0，pstate 显示 state=3
（ZOMBIE），最近 syscall 为 94（exit_group），线程均 TERMINATED，但未回收。
确认后台 spawn 没有 wait 调用者，不能将线程停止等同于资源回收成功。

修复采用现有 create_ex 的暂停创建模式，在 resume 前设置自动回收归属，
仅 shell 后台进程在退出收尾后移交现有系统回收队列；普通父子进程继续 wait。
回调仍检查主线程停止且无调度引用后才删除 TCB、释放地址空间和栈。

另一次独立启动捕获 Weston compositor.c:3637 的 buffer_release_ref 非空断言。
进程随后已为 ZOMBIE，但主线程 READY。源码及可执行生产片段测试确认：
PID 1 退出时把自己当作 init 收养子进程，会反复移动自身链表节点而不结束。
修复禁止自身及非 RUNNING 的 init 收养。此缺陷解释退出循环，不代表缓冲引用
断言的起因已经解决。原进程级信号投递还存在只写 pending 未唤醒目标的路径，
同样未列为修复通过。

6 项专项测试通过，候选镜像全量构建通过，无仓库基线偏移。候选 SHA256：
718d7b39e90c9b712a2c121c2a5ff0ef3904d0346bdcd7d34a4e43425ba7489b。
后台自动回收与 PID 1 退出修复尚待物理板验收，不作为稳定发布依据。

## 自动回收候选的采样结果

候选镜像 CRC32 为 610cf1fb，与 TFTP 回读匹配。第一次四客户端在渲染期间
失去回显，没有 exit 记录，自动回收尚未执行，不能归因于回收修改。
再次复位，禁用 FTP 导出并低频 pstate 采样，得到以下事实：

- PID 4、5、6 首先长期停在 nr=73（ppoll），之后停在 nr=57（close），arg0=5。
- PID 7 正常 exit code=0，后续 pstate 返回 ESRCH，线程数量从 21 减为 20。
  该实例的自动回收已实际执行，但不代表四实例均通过。
- Weston 为 RUNNING，最近 nr=22（epoll_pwait），三客户端仍 RUNNING、SUS|SEM。
- 后续再次发送 ints/pstate 时失去回显；未取得 panic 或明确关闭子阶段。

必须进一步区分 close 的 epoll 移除、fd 锁、VFS/DRM release 和 GPU entity
flush/fini，不能仅凭最近 syscall 就宣布已确定阻塞在某个驱动函数。
源码另发现 sched.h 的 current 是每个翻译单元的静态占位 task_struct，
其 group_leader 未绑定真实任务。这是兼容语义缺口，尚未证明是本次故障根因。

## BO 阶段与取证工具校正

重复采样确认 Weston 长期停留在 ioctl 0x40086409（GEM_CLOSE）；一个客户端
停在 ioctl 0xc0186442（PANFROST_CREATE_BO），其余 ppoll 无限等待。close_stage
均为 0，此次不能归因于 FD 关闭或自动回收。schedstat 实测 SMP ticket 锁
owner=next、count=0、preempt=0，排除该采样时刻锁一直被持有的简单解释。

串口提示符后可紧接异步驱动日志，旧采样器要求提示符位于末尾而误报超时，
已修正并以四个边界用例验证；采样超时不再直接作为整机卡死结论。

只读模块试验加载被拒绝，私有 _k_thread_execute_ptr 未导出。失败模块源码和
分发产物已移除，未用固定地址绕过。改为扩展已有原生诊断命令：

```text
schedstat
schedstat stack
```

stack 子命令在 SMP 保护内复制未运行的图形线程现场和互斥锁持有者，保护外
打印有限原始 PC。运行中目标标记 busy。使用本轮匹配 ELF 的 addr2line 解析。
该诊断仅属于 ThreadX ARMv8 port，不新增 OSAL/arch 公共接口。

栈解码范围、循环终止、IRQ 帧用例已执行通过，集成构建通过。候选镜像 SHA256：
8a6156d58cdfb4b998435d0ce1f45a8ff18632b8a229f72f563ee097b00e65ab。
命令现场采集仍待新镜像启动；当前四窗口稳定性和全部回收未通过。

## 2026-10-09 共享文件引用与四客户端复测

Loader 的 file 可以由 SCM_RIGHTS 跨进程共享，而原引用增减仅持有各进程
自己的 fd_lock。生产函数的确定性交错测试复现引用从 3 错误降到 2，正确值
应为 3。引用增减和零引用判断现由短共享锁保护，驱动关闭和销毁仍在锁外。
Loader 全套测试 158 项通过；一项规则修正为提取真实函数体，避免误匹配
process_reap 的前向声明。该缺陷已复现，但尚不能认定它是 GPU 等待根因。

集成目标 nanopc-t4-user 全量构建成功，118.53 秒，33 个警告、零错误。
BIN 为 1801920 字节，SHA256 为
ae5a1ba72870fc174dcf7be4339b780f3db245bc7586ad26611a21a5be742a84。
板端 TFTP 字节数匹配，CRC32 为 8d9f18aa，六核启动，鼠标与触摸屏枚举。

Weston 配置环境后启用 HDMI 1920x1080。四个 glmark2 build:duration=30.0
实例 PID 5–8 全部记录 exit code=0，随后 pstate 均返回 ESRCH，shell 响应。
但本轮不通过：释放 BO 时大量 slub_free 报错，指针如 0x1c020fc0 的
slab_meta 为异常值 0x1a251101。匹配 ELF 的调用栈如下：

```text
drm_gem_shmem_page_free -> luna_shmem_free_pages -> drm_gem_shmem_put_pages
-> drm_gem_shmem_free_object -> drm_gem_handle_delete -> drm_ioctl
```

alloc_pages_node 分别从 kzalloc 获取 struct page 描述符、从 Luna buddy
获取页数据；__free_pages 先归还页数据再 kfree 描述符。需要追查描述符
所在 slab 的元数据失效原因，不以绕过 kfree 或屏蔽诊断作为修复。
日志同时出现约 20–26ms irqoff，caller 指向 dump_stack；该打印路径会
放大观测时延，不能据此认定原始 GPU 等待由同样长度的关中断导致。
fatal trace 是 dump_stack 的输出等级，本轮没有据此确认整机 panic。

此前永久运行四实例中，鼠标移动新增 579 个事件且读取计数同步增加，
四客户端原生栈均停在 luna_syncobj_wait。仅此不能证明 USB 已完整正常，
也不能证明四窗口可见。本轮尚未取得四窗口同时可见及拖动的人工验收。
证据位于副本父目录 com5-shared-ref-four-build-1009 与
com5-shared-ref-four-after-1009 的有界日志。原 OS 未改动，新改动尚未提交。

## 基线

## 2026-10-09 页表描述符泄漏修复与并发回读

执行生产 io-pgtable 分配/释放函数的宿主测试确认，原先六次成功分配和
释放后残留六个兼容层 struct page 描述符。Linux 原生页描述符是持久元数据，
本兼容层却为每次 alloc_pages_node 单独 kzalloc；页表只保留页数据地址，
正常 free_pages 因而无法归还描述符。该路径改为原始页地址分配/释放配对，
并在 linux510_get_free_pages 补齐 __GFP_ZERO。宿主泄漏测试及实际 Mali
LPAE 映射测试通过，Runtime/DRM 合计 187 项通过。未认定它就是 SLUB 损坏根因。

修复版 BIN SHA256：
d5bf7a3b30b7b5ac0e85a8b80124ace6e0701f4eff34a7d5d01db996f32cf514。
板端 CRC32 d7e52989，集成全量构建 140.49 秒，零错误、33 个警告。
四客户端 build 30 秒：PID 4–7 全部退出码 0、随后 ESRCH、线程数回到 17，
本轮没有 SLUB 释放报错。人工明确确认多窗口、旋转、拖动和关闭全部正常。
单场景并发得分为 79/64/63/64，不可与单实例全场景 Linux 得分直接比较。

第二轮四客户端 texture 30 秒：三个完成，得分 101/88/94；PID 10 因
crate-base.png 的 libpng incorrect data check 未运行场景，得分 0，仍返回
退出码 0。四个进程均回收，本轮未出现 SLUB 错误，但场景验收不通过。
两轮均有 syscall 232 警告；本地 luna/syscall.h 确认其为 mincore，尚未补齐。

为区分固化文件损坏与读取竞争，只读 FTP 独立回读同一个 PNG 八次，均为
500819 字节，SHA256 与仓库源文件一致，PNG chunk CRC 与 IDAT 解压全部通过。
参考 SHA256：bf76ecdbab16091fbe63581cf209baf9cb3b8921f94da84b42689c43c6c02102。
随后四路并发回读的 32 次请求全部超时，COM5 inputstat/ps 也无回显。
当时 glmark2 已全部结束，Weston 仍驻留；不能据此排除图形后台影响，
也不能把故障直接归因于 FTP/ext4/eMMC。下一轮需不启动 Weston 做控制实验。
客户端测试已结束，COM5 已释放，请求物理复位。日志保存有界证据，不覆盖资产。

## 图形副本基线

## 2026-10-09 复位后的控制实验

相同页表修复版镜像再次校验 CRC32 d7e52989 后启动。未启动 Weston 时，
四路独立 FTP PNG 回读先 4 次、再 32 次，全部逐字节匹配源文件，PNG 校验
通过，shell 响应，线程数 15。不能把前一轮超时直接归因为存储或 FTP 并发。

随后首次启动 Weston，在桌面子进程提交 surface 时断言退出：
weston_surface_commit_state 的 state->buffer_release_ref.buffer_release
并非 NULL（compositor.c:3637）。退出码 6，子进程退出，shell 保持响应。
没有禁用或修改该断言。第二次启动 Weston 正常，空闲驻留状态下四路回读
4 次及 32 次全部正确。故该启动异常也不是每次稳定复现。

同一启动周期再运行四个 texture:duration=15.0 客户端，PID 7–10 均完成
场景，得分 102/68/67/71，退出码均为 0，随后 pstate 均为 ESRCH。
有界日志未出现 PNG 解码、SLUB 释放或 fatal 错误；mincore 警告仍待补齐。
之后四路回读 4 次及 32 次全部正确，Weston 仍在 epoll 等待，shell 正常。
本轮未请求新的画面人工确认，不能将串口结果扩展为视觉/拖动验收。

证据：副本父目录 com5-storage-only-after32-1009b、
com5-storage-idle-weston-1009b、com5-storage-weston-idle-after32-1009b、
com5-storage-weston-texture-round-1009b、com5-storage-texture-after32-1009b。
既有偶发 surface 断言、PNG 解码失败与失去回显仍未闭环，不作长期稳定结论。

## 副本仓库记录

## 2026-10-09 信号返回与回收链路验证

新增执行生产函数的测试复现了进程信号未唤醒阻塞主线程、动态 glibc 分支
未准备信号返回入口。已将进程 pending 纳入主线程唤醒判断；poll 系列在
未屏蔽信号到来时返回 EINTR。动态 glibc 进程只增加独立用户 RX 返回页，
执行 rt_sigreturn，不初始化旧 TLS 或替代 ld-linux；exec 清除旧入口。
缺少返回入口的错误路径也先释放已分配的信号帧。

软件检查：Loader 161 项、Runtime/DRM/原生栈解码 188 项，共 349 项通过。
集成全量构建 147.32 秒，零错误、33 个警告；BIN 1806032 字节，SHA256：
dd96a7de3148c85ab802f17e5303fdd5ffc669dcd90eeda809e85222798cd4b7。
板端 CRC32 7feca9a5 匹配。

单实例 build:duration=30.0 --run-forever：SIGTERM 后正常退出码 0，PID 4
随后 ESRCH，线程数回到 17。继续同次启动，四实例同样单场景周期（PID 5–8）
全部 SIGTERM 正常退出码 0，全部 ESRCH，shell 正常，线程数回到 17。
这些是串口和生命周期检查，不新增四窗口视觉验收结论。

随后在同次启动重开四实例，恢复 build:duration=5.0 --run-forever，持续
20 秒后发送 SIGTERM，再次失败。PID 9 停在 PANFROST_CREATE_BO，pending
0x8000；PID 10–12 信号已清除，但重新进入 Wayland ppoll。close_stage
均为 0，说明尚未进入 FD 回收。不能认定系统回收线程是此次阻塞根因。
之前另一次短周期实验也复现同类 BO 创建/帧等待阻塞；没有关闭协议断言、
绕过驱动等待或强制释放对象。整体短周期稳定性与完成标签仍不通过。

证据在副本父目录 com5-signal-single-stop-1009、
com5-signal-four-long-scene-stop-1009、com5-signal-four-short-stop-1009、
com5-signal-short-loop-failure-state-1009 的有界日志。

## 完成标签发布门禁：未通过

本次整理前执行 Loader、Runtime、DRM 和原生栈解码回归，合计 346 项通过。
进一步强制退出验收使用四个 glmark2 --run-forever 实例 PID 4–7，再发送
kill <pid> 15。PID 4 报 signal: no executable sigreturn trampoline，进入
退出流程后 close_stage=7 尚未完成回收；PID 5–7 保持 pending=0x8000，
停在 ppoll，线程数仍为 21。shell 可响应，但不符合全部进程可回收要求。

源码对应：k_process_signal 仅设置进程 pending，不唤醒阻塞线程；
process_prepare_initial_thread 的 PROC_FLAG_LINUX_DYNAMIC 分支跳过现有
compat trampoline 初始化。需要正规信号返回映射和可中断等待语义，不能
强制释放仍在驱动路径内的对象，也不能把发送成功作为终止成功。

因此尚不发布 ThreadX/glibc 图形化完成标签，也不推送声称完成的版本。
本地检查点提交保留已有修复和失败证据，后续修复必须重新构建并上板验收。

副本路径为 D:/workspace/codex-workspace/luna-graphics-20261008/os。
33 个仓库基于 debug-weston-input-20260924，20 个 master 与该 tag 相同。
其余仓库的较新 master 含 Linux-native Runtime 改动，不得静默混合。
最初未经 pin 的集成构建切换了仓库分支，相关早期实验不计入图形基线验收。
后续构建逐仓库检查 HEAD，记录零基线偏移。
