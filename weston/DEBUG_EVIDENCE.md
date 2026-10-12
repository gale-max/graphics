# 图形调试关键证据

本记录不保存冗长过程日志，不替代硬件验收。

## 2026-10-10 DDR1600 后的回收对照

- 无 JTAG 条件下复用只读 schedstat stack；运行中图形线程 busy，不读取其栈。
  软件取证轮自动捕获 CREATE_BO 阶段504与 GEM_CLOSE 阶段403 超500ms，
  指向页/MMU映射及映射释放；之后 ps 无回显，未发送暂停命令。普通 Runtime
  spin_lock 无抢占保护、preempt_disable 仅 barrier，属于待审计契约差异，不能
  直接用全局 SMP 保护替换或认定它就是根因。
- AS 锁所有权临时版 CRC `8d4e5f05` 已构建校验上板，固定四槽位记录取锁线程、
  调用点、时间和等待者，保持原自旋/IRQ语义；不解引用日志中的锁/线程地址。
  五项覆盖/回归检查通过。取锁调用点非实时 PC，记录为并发近似快照。
  六客户端首段被动采集未报告超限，本轮视觉状态待确认，不作为通过依据。

- 自动监控初版在 stop/join 后残留 COMPLETED，立即重启 EAGAIN。发现 OSAL
  join 收到完成 semaphore 后忽略线程删除失败，仍释放栈/impl；完成通知可早于
  线程入口真正返回。修改为先 terminate/delete 成功再释放，失败保留资源与令牌。
  可执行回归通过；修复版 CRC `5375b72d` 上板监控 start/stop/restart 成功，
  线程基线 15->14->15，未再残留 COMPLETED。未证明内核控制块物理内存完全回收。
- 同版六客户端人工确认冻结。最初 shell 正常、FPS 约44，监控任务 SLEEP，未
  报告超500ms调用；后续查询无正常回显，收到少量异常字节。不能由没有自动
  报告推断无长调用：调度/IRQ停转也会使监控失效。该 join 修复不等同图形根因闭环。

- 引用释放细分版 CRC `3931807f` 六客户端人工确认卡住。最后成功采样仍为
  短调用，随后 drmdiag 超时、复查无回显，不能用前一轮阶段 204 推断本轮。
  对象锁/dma-buf/最终回收标记已经链接，但 shell 式按需采样仍存在冻结后不可读
  的盲区；需要首次长停顿时自动捕获或外部硬件调试，不能宣称已定位具体锁。

- gem_open 内部版 CRC `a558e94c` 六客户端，人工确认卡住；本轮长期活跃的是
  单条 GEM_CLOSE，started=42014919291 ns，now=105483658875 仍在阶段 204。
  shell 正常、其余五客户端挂起，不能强行与前两条 open 阻塞归为同一锁。
  已将 handle_put 细分为 609 对象名锁前、610 拿锁后、612 dma-buf 释放前、
  613 解锁前、614 最后 GEM 引用释放前、615 返回，四项回归及构建通过，尚待上板。

- 同一 `3a3d1176` 镜像再次卡顿：BO 导入/创建从 178361412333/178361613000
  ns 持续停在阶段 316，now=225274188708，约 47 秒；VOP 时钟正常、FS=0，
  部分客户端输出降至约 3–4 FPS。进一步添加 open 内部阶段 501 映射分配、
  502 MM 锁、503 MM 区间插入、504 页/MMU 映射、505 映射锁，三项测试及
  集成重编通过；尚未上板，不认定任何子路径已经修复。

- 内部细分版 CRC `3a3d1176` 六客户端：PRIME_FD_TO_HANDLE（0xc00c642e）与
  CREATE_BO（0xc0186442）分别从 75596958583、75597152250 ns 停在阶段 316
  （驱动 gem_open），不同 BO 地址，连续至 now=109416825875 仍未返回。
  now=132052988666 再查时活跃槽已消失，VOP FS enable=0x2，说明后来恢复进度。
  本轮不是 close/IDR/全局对象锁阶段；长停顿位于 Panfrost 映射建立回调范围，
  目前不能区分映射分配、MM 区间管理、shmem 页获取或 MMU 更新，不能判永久死锁。

- 人工确认 `d2a0d050` 六窗口冻结后，VOP gate/PM/standby 仍正常且 FS=0。
  同时 GEM_CLOSE 阶段 201（驱动 close）与 CREATE_BO 阶段 302（句柄创建）
  started 分别固定为 195862533958、195862696708 ns，now=255748250333，
  两者约 60 秒未返回。FS 关闭可能是主循环停止提交后的结果，不能据此判为
  GIC 故障。已进一步加入 310–316 句柄创建阶段及 401–404 映射 close 阶段，
  四项测试与集成重编通过，更新 TFTP，尚未上板。

- 只读诊断版 CRC `d2a0d050` 已上板。Weston 空闲：VOP enabled=1、usage=1、
  suspended=0、hclk/aclk 硬件均开启（软件各 3 引用）、standby=0、FS enable=0。
  六客户端开始运行后 FS enable=0x2，随后从约 73 秒起多次采样为 0；event=NULL，
  gate/PM/standby 不变。尚待本轮视觉确认。不能只凭 IRQ 停止判断 GIC 故障：
  上游 vblank_disable_fn 在 refcount=0 时会主动关帧中断，需要进一步区分
  引用管理异常与用户态停止提交/未处理 pageflip 完成事件。

- 新增只读 vopdiag：报告 enabled、runtime PM usage/suspended、硬件 gate 与软件
  引用、待完成 event、FS enable/status 和 standby。仅 trylock 模式锁，硬件
  hclk/aclk 关闭时不访问 VOP MMIO；不清中断、不强开时钟、不修改输出。
  CRU 回读、clk 并发和只读约束三项测试通过，集成构建通过（1812296 字节），
  已更新 TFTP，尚未上板验收。首次诊断编译的 ctrl/standby 字段错误已按本版
  common/standby 定义修正，不部署失败产物。

- clk 引用竞态修复版 CRC `f4ac9119` 已核对上板并运行六客户端；人工确认画面
  冻结。IRQ151 在两次后续快照均为 2685，而 GPU job IRQ52 从 38721 增至
  49446，shell 与 drmdiag 正常。修复不能认定已解决显示停顿；须继续核对 VOP
  FS 使能/状态、standby、硬件 gate、runtime PM 及共享 IRQ。VOP 寄存器读取
  必须确认访问时钟有效，不通过强开时钟或中断改变现场。

- Runtime clk_enable/clk_disable 原先无锁修改普通 enable_count。六宿主线程各
  100000 次临时引用、同时保留一个永久引用的执行测试复现计数破坏或提前 gate。
  增加 IRQ-safe 锁，将计数和 gate 的零/一转换串行化后测试通过；RK3399 gate
  回调仅作 MMIO 写入，无睡眠或递归 clk_enable。已完整构建并更新 TFTP，尚未
  上板验证，不能认定这项已解释视觉冻结或停止的 IRQ151。

- 人工连续移动鼠标后：events/events_read 从 0 增至 1050，OHCI IRQ60 从 23
  增至 723，证明该次事件进入输入层并被读取，不是鼠标完全未上报。
  两次中断快照 GPU job IRQ52 从 87450 增至 102640，但共享 VOPL/IOMMU IRQ151
  均为 1145。设备树 vopl 与 vopl_mmu 均使用 SPI119（119+32=151）。
  客户端仍输出约 47 FPS，shell 可用，不能等同屏幕刷新。优先核对 VOP 输出、
  FS 中断使能/状态、GIC 共享 IRQ 与帧完成链路；计数不变尚未证明具体原因。

- 已撤除依赖复位保留 DRAM 的 IRQ 快照与对应测试；RK3399 重走 DDR 初始化，
  不保证记录保留，不能作为主要取证方法。内部阶段版 CRC `04be8101` 已构建上板。
  六客户端人工确认冻结时，GEM_CLOSE 从 started=59016806291 固定在阶段 201
  （驱动 close 回调），CREATE_BO 从 59016951833 固定在阶段 302（句柄创建）。
  now=60456549416、62660298166、64865947125 的连续快照不变，约 8 秒后再次
  观察到进度恢复，不能断言永久死锁。后续 now=111197825958 时 shell、ps 可用，
  原长期记录已消失，Weston 仍处理新 ioctl。阶段与对象指针是范围线索，尚未
  证明锁环、具体锁持有者或 GPU/显示完成问题已修复。

- IRQ 固定快照临时版 CRC `0cb0320b`，镜像 1807832 字节，已核对并启动六客户端。
  IRQ 快照地址 `0x023fae40`（8 项、每项 64 字节），DRM 槽位 `0x024df578`。
  快照仅记录最后 IRQ 的被中断寄存器与进入/返回时间，不能保证复位保留，也不是
  当前阻塞 PC；每 IRQ 清缓存增加开销，此版不能用于性能验收。
- 现场 shell 仍正常：两次 drmdiag 的 now 为 102275448333、133881570958 ns，
  GEM_CLOSE（Weston）的 started 始终为 93744468125；另一 CREATE_BO 的 started
  始终为 93742299875，持续约 40 秒未返回。pstate 确认 PID 6 处于 CREATE_BO，
  其它客户端在 ppoll；ps 中 Weston 与 PID 6 对应线程 READY。此证据说明创建/释放
  路径持续停留，尚未证明共同锁或内存管理具体根因。先保留现场，禁止直接重载。

- 六客户端 100 轮脚本首轮 PID 4–9 运行时人工确认冻结；脚本随后确认六条
  SIGTERM 与退出 0、ESRCH 和 17 线程基线。这仅是系统回收检查，不是视觉通过。
  第二轮获得 PID 10–14，发送第六条 spawn 时无回显，脚本停止；随后 drmdiag
  也无回显，未发送后续 pstate。整体验收为 0/100，不能把首轮 ROUND_PASS
  当成完整验收。板端可能存在未完成的第六个 spawn，不可在未查询前假定其 PID。

- 固定 16 槽位 ioctl 诊断版 CRC `def14ef6` 已上板，正常路径仅记录内存，
  `drmdiag` 按需打印；空闲查询正常，满表不等待与返回归还的宿主测试通过。
  首轮 PID 2–5 短周期纹理运行获人工确认正常，四条 SIGTERM 均送达，
  客户端退出 0，线程数恢复 17，诊断无活跃 ioctl；人工确认窗口全部消失。
- 同一 Weston 不重启，再启动 PID 8–11 的四个 800x600 纹理窗口，运行 60 秒。
  四进程自然退出 0、随后均 ESRCH，线程数再次恢复 17，shell 正常，诊断无活跃
  ioctl。人工确认旋转、拖动、光标和退出全部正常。此为两轮功能验收，不证明
  长期无泄漏或此前偶发黑屏已根治；未据此提交完成 tag。

- 无成功 read 分片打印、无 DESTROY_DUMB 临时打印的镜像 CRC `c3eeaa18`，
  四个 800x600 纹理客户端每 5 秒重建，先持续响应采样，随后查询超时。
  人工确认黑屏；本轮未发送 kill。空回车无回显，额外被动采集 8 秒无输出。
  因此高频成功诊断不是复现的必要条件，但尚未区分显示失效与整机长停顿，
  也未捕获 panic 或具体阻塞边界。禁止据此声称已修复或永久 GEM 死锁。

- CRC `fecb4f3c` 的释放边界诊断直接记录连续 DESTROY_DUMB enter/leave，
  返回值均为 0。未证实该 ioctl 永久阻塞；之前最后 syscall 采样不能替代调用边界。
  该调用频繁，临时打印产生大量输出，污染减少 read 日志的对照。因此删除释放
  边界打印再重编，不把本轮串口超时当作干净对照的结论。

- 后续复查发现该轮系统恢复响应，客户端继续输出 FPS，Weston 最后采样 ioctl
  已返回（active_syscall=-1）。因此先前串口超时和人工冻结不能证明永久 GEM 死锁。
  对 PID 4–7 的四条 SIGTERM 均确认送达，退出码 0、线程数恢复 17、shell 正常；
  视觉撤窗及光标恢复仍待本轮人工确认。
- crate-base.png 的每次成功分片读取仍有临时指纹打印。修改为成功静默、仅失败
  报告，保留三份指纹校验与错误返回；读取分片/usercopy/诊断回归共 5 项通过。
  此项是减少已知取证负载，不代表已经证明冻结根因或完成硬件修复。

- 诊断镜像 CRC `1651c67e` 下再次进行不发送 kill 的短周期纹理对照，
  人工确认冻结，串口采样随后超时。运行阶段即可复现，SIGTERM 不是必要条件。
  该版新增的释放边界 `pr_info` 被 Runtime 格式过滤，不能用于判断入口/返回；
  已改为仅该 ioctl 的直接 printk，重新构建，尚待上板取证。

- 同一镜像 CRC `91cd2118`，四个 800x600 纹理客户端运行 60 秒后均退出 0，
  线程数恢复至 Weston 基线 17，shell 正常。人工确认窗口全部消失、光标可移动。
- 随后四客户端每 5 秒重建纹理场景，人工确认旋转和拖动正常；发送首条 kill 时
  已无串口回显，后续 kill 未发送。不能据此认定 SIGTERM 或进程退出导致冻结。
- 重启后进行不发送 kill 的同条件对照（PID 4–7），仍出现 pstate 采样超时。
  最后有效采样为 Weston ioctl `0xc00464b4`，对应 `DRM_IOCTL_MODE_DESTROY_DUMB`。
  此处只证明最后采样位置，尚未证明该 ioctl 内部死锁；需进一步记录 GEM 释放边界。
- 原始尾部证据位于独立调试目录的 `com5-ddr800-no-kill-control.tail.bin`；
  本轮视觉冻结状态仍需人工确认，短周期持续运行与信号退出尚未验收。

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

## 2026-10-09 BO 锁、SLUB 交错与等待语义

生产 Panfrost BO 创建/析构函数的宿主测试确认，128 次循环后遗留 128 个
mappings.lock 句柄；已补销毁，通用 shmem 的 pages_lock/vmap_lock 原本已有
销毁，未重复添加。另以生产 OSAL 取锁函数复现 K_WAIT_ABORTED 后无锁返回，
普通 mutex_lock 现对中止等待重新阻塞取锁，未加入轮询延时。该测试不覆盖
所有非法句柄错误，也不代表完整 Linux 可中断锁语义已实现。

执行原生 DRM MM、当前 Runtime 红黑树/位操作的 20000 次区间插入、删除和
复用，没有重叠或遗留节点；诊断输出头被宿主替换，不据此判断硬件并发正确。

进一步执行 SLUB 生产函数的确定性交错模型，确认两处竞态：
1. 远端释放在 slab 锁与 cache 锁之间丢失所有权后，可把已重新冻结的页
   发布到 partial，也可能无 slab 锁修改远端 freelist。
2. partial 获取方转交 freelist 未与远端归还同步，读取之后、清空之前
   归还的对象会丢失。
修复统一 slab -> cache 的锁顺序；获取方先保留 frozen 所有权并释放 cache
锁，再在 slab 锁内转交 freelist。冻结页的远端归还仍只取 slab 锁。
相关测试覆盖本核释放、远端释放、partial 归还和再占用交错，共 5 项通过。
这些确认了软件缺陷，但未证明已覆盖本次所有卡死原因。

两处 SLUB 修复版 CRC32 7a837366：人工曾确认可旋转、鼠标可移动；发送
SIGTERM 后仍未退出。三个实例 pending 已清除并停在 ppoll，另一个最近
syscall 为 BO 创建。运行中线程未读栈，因此不能把最近 syscall 当作活跃 PC。

补充只读 syscall_active 标记，仅在分发函数调用前写入 nr+1、返回后清零，
由 pstate 输出 active_syscall（-1 表示已返回），不参与任何执行决策。
最终候选软件回归 358 项通过，集成全量构建 150.74 秒，零错误、33 个警告。
BIN SHA256：cdd4745b5ebfb1539d40173c0c6e160bd12376e8d9f01144346268b98be059ea，
板端 CRC32 97275b32 匹配。短周期四实例后 COM5 查询无回显，未采到有效
活跃标记；不能继续声称已经定位在 BO 函数内，整体回收验收仍不通过。
采集已结束并释放 COM5，请求复位后提前采样。没有强删活跃对象或关闭断言。

关键证据：副本父目录 com5-slub-both-stop-state-1009、
com5-active-syscall-short-cycle-1009、com5-active-syscall-before-term-1009。

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

## 2026-10-09 原子轮询修复后复测

镜像 CRC32 为 `dca562d8`。修复 Linux Runtime 的原子 MMIO 轮询与
`udelay` 睡眠行为后，两轮四客户端后台停止均得到退出码 0、PID 查询
ESRCH 和 shell 响应。单个前台 build 场景自然结束以及 Ctrl+C 后也确认
PID 已回收、后续 `ps` 正常响应；这些结果不等于全部内存已释放。

随后四个 glmark2（PID 10–13）每五秒重建 build 场景，人工确认旋转、
鼠标与拖动正常，但压力期间出现以下失败：

- desktop-shell（PID 7）报告 `corrupted size vs. prev_size`，退出信号 6。
- Weston（PID 5）在 `weston_surface_commit_state()` 触发
  `state->buffer_release_ref.buffer_release == NULL` 断言，退出信号 6。
- 四个客户端随后退出；之后发送 SIGTERM 已返回 ESRCH，不能把这次
  客户端退出计作主动终止验收成功。
- shell 仍响应 `ps`；本轮是用户进程崩溃，未复现整机无回显。
- 采样曾出现越界的 `close_stage=1853189955`，尚需区分内存破坏与
  诊断输出问题，不能仅凭该数值确定损坏来源。

关键证据位于副本父目录
`com5-com5-four-repeat-build-1009c.tail.bin`，只保留有界串口尾部。
此次未修改上游断言，也未关闭中断或强制释放活跃 GPU 对象。
四进程重复运行、纹理校验及完整资源回收仍未全部通过，不发布完成标签。

### 无拖动对照与释放阶段错误

同一镜像、同一次启动中重新启动 Weston（PID 15），四个客户端 PID
18–21 在无诊断采样的 35 秒观察期间继续报告 FPS，人工确认持续旋转。
随后逐个发送 SIGTERM，前三个退出码为 0；第四个的 GEM 清理路径出现
`slub_free: ptr 0000000020f3ab00 has no slab metadata
(sp=000000001fb42601), leaking`，其他同页描述符也报错。调用链包括
`drm_gem_shmem_page_free -> luna_shmem_free_pages ->
drm_gem_shmem_put_pages -> drm_gem_shmem_free_object ->
drm_gem_handle_delete`。串口同时出现一次 18.69 ms 的 irqoff 报告，
其与密集错误打印的因果关系尚未确认。

Runtime `alloc_pages_node()` 单独 kzalloc 分配 struct page，再通过
linux_osal_page_alloc 分配物理页；`__free_pages()` 先归还物理页再 kfree
描述符。故当前释放错误指向描述符所在页的 slab 所有权/元数据，尚不能
只凭调用链认定 GEM 重复释放或 buddy 为唯一根因。

第四个客户端最终仍输出退出码 0，后续 ps 可响应且 Weston 存活；但
错误路径明确泄漏资源，退出码不能作为完整回收成功证据。本轮无需复位。
证据为副本父目录 `com5-com5-four-nodrag-stop-1009d.tail.bin`。

### buddy 描述符取证镜像

仅扩展原 SLUB 错误分支诊断，完整集成构建后镜像 CRC 为 `11bc5a14`。
重新启动 Weston 后，四客户端 PID 4–7 启动阶段便出现 Weston 用户态
异常，随后 GEM 清理复现错误。采集中的 buddy 数据如下：

- 描述符数组地址 `0x2501000`。
- 对象页 PFN `0x174b2`，记录地址 `0x28483a8`，flags=0、order=0、ref=1，
  slab_meta=`0x16f26d01`，next/prev 均为 0。
- 相邻 PFN `0x174b3` 的记录 flags=1、order=0、ref=0，slab_meta=`0x1`。
- 同一物理页上多个相隔 32 字节的 page 描述符释放均出现相同损坏值。

相邻记录同样异常，不能仅归因于一个 GEM 对象传错指针；元数据区域
写坏、CPU 别名、DMA 错写的具体来源仍未确定。此次没有人为 SIGTERM，
不能将异常后的退出计作回收验收通过；后续 ps 正常响应。
有界证据为副本父目录 `com5-com5-metadata-four-build-1009g.tail.bin`。

采集工具已修复命令无提示符后继续发送后续命令的问题，并验证保留已收
证据及停止发送。此前没有 spawn 回显/PID 的一轮不计作四客户端运行。

### 页表翻译诊断与三轮重复测试

增加错误现场的内核页表/当前 TTBR0 翻译对照，避免将进程页表别名中的
读数误认作原物理描述符被写坏。首次构建使用 CONFIG_ARCH_PROCESS 条件，
该宏仅由架构组件 target 设置，Luna 镜像不包含诊断字符串；改用
CONFIG_PROCESS 和非 NOMMU 条件后，确认最终 BIN 含 `slub translation:`。
新镜像 CRC32=`750716cc`，完整集成构建成功，未改变释放或 GPU 策略。

同一次启动依次运行三轮四客户端，每轮场景持续五秒并循环重建：

- build 第一轮 PID 4–7，第二轮 PID 8–11。
- texture 第三轮 PID 12–15。
- 每轮分别发送 SIGTERM，全部退出码 0，随后各 PID 查询返回 ESRCH。
- 每轮结束 ps 均回到 17 个原生线程，Weston 仍存活，shell 正常响应。
- 本组三轮有界记录未见堆损坏、SLUB 元数据错误或 PNG 数据校验错误。

诊断未被触发，因此尚未取得同一错误地址的双页表翻译，不能判定真实
物理覆盖还是映射别名，也不能认为增加日志已经修复故障。原生线程数与
PID 消失只验证调度/查询状态，不证明所有隔离的 TCB 或内存均已释放。
对应证据为父目录 `com5-com5-translation-*-1009k.tail.bin`。

### 纹理画面人工确认与自然退出

用户指出此前纹理轮没有观察到画面，因此该轮仅保留串口运行与 PID
退出证据，不计作纹理显示验收。随后单个 800x600、30 秒 texture 场景
得到窗口出现并旋转的人工确认，但首轮结束后串口无响应；重新复位并
连续采集后，同条件单客户端退出码 0、ESRCH、线程数 17、shell 正常。

同次启动的四客户端 30 秒场景全部自然退出，但记录中有一次
`libpng error: incorrect data check`，不能计作无错误通过。
按用户要求重跑四个 800x600 texture 场景 60 秒（PID 9–12），用户确认
画面均正常；本轮全部退出码 0，四 PID 返回 ESRCH，线程数回到 17，
shell 响应，记录中未见 libpng 或 SLUB 错误。此轮是单次通过，不解释
之前的偶发校验失败和元数据损坏，不发布完成标签。

有界记录为父目录 `com5-com5-four-texture-continuous-1009m.tail.bin`
以及 `com5-com5-four-texture-visual-retry-1009n.tail.bin`。

### 协作退出候选版及首次 Weston 故障符号

Loader 移除 exit/reap 对其它线程的异步 terminate：挂起线程不等于已经
终止，进程退出等待其它线程在返回用户边界自行停止后再释放地址空间。
旧代码的挂起状态执行测试及两个契约检查均失败，修复后 Loader 和信号
等待回归 166 项通过。完整集成镜像 CRC=`bbf20b24`。

该版首轮四个 800x600 texture 客户端自然运行 60 秒，人工确认正常；
全部退出码 0、ESRCH、线程数 17、shell 正常，未见 PNG/SLUB 错误。
第二轮四客户端每五秒重建纹理场景时，发送 SIGTERM 前 Weston 用户态
异常，不能计作主动停止验收成功。其子程序及客户端随后退出，ps 正常。

故障记录：PC=`0x2002279c8`，fault_addr=`0x9`，x20=`0x1`。
VMA 映射与 libweston 符号对应库基址 `0x200210000`、偏移 `0x179c8`：
`weston_buffer_release_reference()` 的 `ldr w2, [x20, #8]`。
调用链包含 `weston_buffer_release_move()` 和
`weston_surface_commit_state()`。buffer_release 参数已经为非法指针 1，
其写入来源尚未定位，不跳过断言或按 NULL 处理。

板端 libweston-9.so.0 只读回读与本地产物逐字节一致，398664 字节，
SHA256=`4856633be05d3beaf8831232912aaa60b6588f12782da172c69e9b7968cba581`。
原始有界记录为 `com5-com5-cooperative-four-signal-1009s.tail.bin`。
本轮未复现此前 SLUB 错误，不足以证明协作退出修复解释了所有内存损坏。

### usercopy 与 VMA 锁返回值修复（待上板验收）

实际执行 process_user_buffer_copy 的测试复现：等待返回 K_WAIT_ABORTED
或错误时原实现仍复制并解锁，且没有检查读写权限。普通离散跨页读取
通过，取消等待、写入只读页、读取仅写/无权限页、锁错误五种情况失败。
修复为取消等待重试、错误返回且不解锁，并按复制方向检查 VMA 权限。

进一步统一 Loader 内部 VMA 锁获取，覆盖 ARMv8 和通用 ABI 的字符串
复制、brk、mmap、munmap、mremap、mprotect、futex 和 clone 初始化。
私有帮助函数 process_vm_lock_acquire 复用现有 OSAL，不新增标准接口。
通用 mmap 的文件引用也在退出与锁失败路径配对释放。
Loader 回归 169 项通过；完整集成构建成功，33 个已有警告，无构建错误。
BIN SHA256=`6d8b44ab74a2817ff2ff63153e46d36a004e6c5c96181303000c15181e28ec03`。

这些是可验证的并发/权限缺陷，但尚未证明为 PNG 错误、Weston 指针
损坏或板卡失去回显的唯一来源。镜像已更新 TFTP，待重新上板验证。

### brk 收缩语义与诊断格式修复

对照本地 Linux 5.10-RT mm/mmap.c:236-263：brk 跨页收缩撤销尾部整页。
Luna 原实现只移动逻辑堆顶，重新增长时复用带旧内容的页。执行实际
uspace_brk 的模型复现了尾部未撤销、全退还后重新增长内容不为零和
撤销失败仍更新堆顶；同页内收缩保留内容的对照通过。
修复为调用已有 uspace_munmap 撤销尾部，保留边界所在页，重新增长由
既有零填充分配器提供页。Loader 回归 171 项通过。

添加仅针对 crate-base.png 的读边界片段指纹，比较复制前后源缓冲及
安全读回的用户副本；不修饰输入，也不改变 read 的正常返回值。
首轮日志 bytes=u 且后续参数错位，定位到 Luna 格式化器不支持 z 长度。
实际格式化器对照 host snprintf 复现 `%zu|%08x|%d` 得到
`u|00001000|305419896`，而预期为 `4096|12345678|-7`。
新增 zu/zd/zx 支持并消除最小负数取绝对值的有符号溢出，UBSan 对照
测试通过；此前错位的读校验记录不能用于判断数据一致。

扩大回归时修正三个因旧变量名/条件写法失效的源码契约检查，保留
SLUB 行为约束与实际竞争执行测试，相关回归合计 211 项通过。
新镜像 SHA256=`e9669ceb42e761ec3e875f2d91bba19537e2bb1d3c4522e27f64306ad1eb7353`，
完整构建成功，33 个已有警告，无新增警告。待重新上板验证；这些修复
尚不能解释全部板端故障，不发布完成标签。

### 内核编译与 SIMD 上下文约束冲突

已确认 ARMv8 平台只在 assembler flags 中设置 -mgeneral-regs-only，
C/C++ flags 缺失该约束。扫描实际链接 ELF，排除 arch_fp_save/restore
后仍有 58 个函数使用 FP/SIMD 寄存器，包括 luna_print/printk、JBD、
proc_fd_init_stdio、sys_rt_sigaction 等。ThreadX 用户线程执行内核代码时
不会把内核 SIMD 临时值保存到 lower EL 的用户 FP 保存区，普通内核
工作线程也不保证分配 FP 上下文。因此编译输出与调度约定存在真实冲突。

为内核 C/C++ 补齐通用寄存器编译约束，用户 graphics 工具链仍独立。
ethspeed 的实际浮点显示改为整数四舍五入的两位 MiB。禁止 SIMD 后
GCC 的 popcount 改用 __popcountdi2，补充无 SIMD、无锁的软件辅助函数；
一万余随机/边界值测试通过，最终反汇编确认没有递归自调用。
相关回归 215 项通过，完整重编成功，33 个已有警告。

最终 ELF SHA256=`e254c0f61fdf50e2ce29fcbfab93f21b30fa16d6209ae577ed2b7c56a6154525`，
audit_kernel_simd.py 输出 unexpected_fp_simd_functions=0。
这是已经修正并通过机器码核对的架构约束冲突；尚未完成该版物理压力
验证，不将它直接等同于所有 PNG、指针损坏和卡死故障已闭环。

### 2026-10-10 四窗口重复运行与页元数据异常

通知修复版 BIN CRC32 为 `2cfe8ecc`。四个无纹理 build 场景运行
30 秒，第一轮人工确认旋转、拖动和关闭均正常，四个进程退出后 shell
响应且线程数回到 17。第二轮仍能退出并查询 ps，但释放 Runtime 的
`struct page` 描述对象时出现 SLUB 错误：PFN `0x216b2` 的 buddy 记录
`0x29dd3a8` 中 slab_meta 为不对齐值 `0x204c4941`。主机与活动页表对
该记录的翻译一致。诊断栈包含 drm_gem_shmem_page_free；这些 fatal
级别的栈输出不能直接当作 CPU 异常或 panic。

此前四纹理场景仅两个窗口成功，另两个报告 PNG 解压校验失败；采集到的
554 个读取片段与参考文件一致。该片段校验并不证明所有用户态解码状态
正确。无纹理重复运行也触发页元数据异常，故 PNG 解码不是必要条件。

Runtime 数据页由 buddy 分配，页描述对象由 kzalloc 分配，释放接口配对
未发现明显混用；尚未定位首次非法写入。新增固定 256 条 slab 所有权
赋值记录，仅 ARMv8 进程配置包含，错误时解锁后报告最近 before/after
和 caller。不改变分配与释放行为，记录缺失不代表此前没有所有权更新。
串口采集额外保留最多 8 KiB 首次错误现场，防止后续重复栈覆盖证据。
此版本属于取证版本，不算稳定性通过，不提交完成标签。

取证版 CRC32 `faec8a5a` 上板后首次四窗口即捕获异常：PFN `0x1a064`
记录 `0x28b7728` 最近经 new_slab 正常写入 `0x17780000`，报错时变为
`0x17780001`。这一轮已证明所有者指针在合法发布后被改写，而不只是
元数据对象的 magic 检查失败。尚未证明是加一、置位、越界或 DMA 写入，
也不能排除未记录的非法写路径。四客户端退出后 ps 仍响应，线程数 17。
首次错误保留在副本父目录 com5-owner-diag-four1.first-fault.bin，最大
8 KiB。不把取证开销下的复现时间与原镜像直接做性能比较。

解锁地址取证版 CRC32 `1c8a46aa` 中，arch_spin_unlock 对描述符数组
地址范围的检查已通过最终反汇编核对。四窗口再次捕获三个所有者低位
变化：`0x14610c00 -> 0x14610c01`、`0x1e7f4600 -> 0x1e7f4601`、
`0x21828a00 -> 0x21828a01`。首次栈为 drm_gem_unmap_dma_buf，经
dma_buf_detach 和 rockchip_gem_free_object 到 DRM ioctl。采集片段
未出现 slub lock target，不能确认 ticket 解锁为改写来源。测试结束后
COM5 查询无回显，未完成回收验收；这是未闭环取证，不是修复结果。

### DMA 缓存语义的确定缺陷

对照本机 phytium-linux-kernel 的 Linux 5.10-RT cache.S，Luna 的
arch_dcache_invalidate_range 曾对未对齐边界直接 IVAC；区间外同缓存行
的 CPU 脏数据可能丢失。修正为未对齐首尾 CIVAC、完整内部行 IVAC，
保留零长度直接返回。指令推演覆盖六种区间和旧行为，不替代硬件验收。

Runtime dma_map_sgtable/dma_unmap_sgtable 丢弃 attrs，导致 DRM PRIME
明确要求 DMA_ATTR_SKIP_CPU_SYNC 时仍执行缓存操作。实际函数提取执行
测试修复前返回 4，修复后通过；跳过同步时仍计算每个 SG 的 DMA 地址。
两项合计 8 个检查通过。尚未证明这些缺陷直接导致 slab_meta 低位改写。

修复版 CRC32 `fe1935c4` 已完整重编、TFTP 校验并上板。四个 build
窗口运行期间人工确认移动鼠标后卡死；采集片段中未出现 slab、panic、
退出或 FPS 标记，随后空回车没有回显，后续查询停止，COM5 释放。
因此 DMA 两项修复不能视为本次卡死的闭环，也不能将未打印 slab 错误
等同于元数据没有损坏。鼠标事件、唤醒与图形并发路径仍待定位。

同一 CRC `fe1935c4` 无鼠标对照人工确认画面正常。四进程结束后 ps
响应、线程数 17，inputstat 的 events/reports/wake 均为 0。然而运行中
已发生多次 slab 所有者低位改写。这排除了“必须收到鼠标事件才会产生
该内存异常”的前提；不能把随后鼠标触发失效直接归因于 HID 驱动，也
不能把画面正常及进程退出当作内存回收通过。

### 临时 CPU 写观察点取证

新增四个硬件写观察点采样最近分配块首的 slab_meta。每 CPU 的寄存器
配置由 IRQ 恢复边界同步，仅 ARMv8 EL1 进程取证版使用；DAIF 的 D 位
在观察激活时解除屏蔽，IRQ/FIQ 位保留。此版本改变执行时序，不能用于
性能结论或作为永久修复。需要后续以受控写入验证观察点确实触发，不得
因未命中而排除 CPU 写入；DMA 与其他虚拟地址别名写入不在此观察范围。

合法赋值集中到临时汇编 STR 入口，异常处理读取实际 WVR/WCR 和 FAR，
仅对匹配观察地址且不在合法入口的写入保存现场，避免仅依据异常后读到
的低位值判断。实际异常处理函数的主机测试通过；不替代硬件自检。

最终取证版 CRC32 `31e9957a` 完整构建并上板。两轮四客户端 build 均
有 FPS 和自然退出，轮间 ps 响应，未采到 slab 错误或写观察点报告。
四纹理客户端中一项 PNG 解码失败，三项有 FPS；人工反馈看到了但卡住。
之后空回车、ps、inputstat 均响应，线程数 17，事件计数 0。
纹理读取的 554 个已采集片段全部与参考一致，仍不能证明解码状态正确。
该版尚未验收，不提交或推送临时观察点，不发布完成标签。

### 独立 FP 上下文实测

luna-test/fp-context-probe 使用 Catboy 构建静态 glibc 用户程序，汇编
在 q0–q31、FPCR、FPSR 保留哨兵期间只运行原始 syscall 或纯整数循环，
不调用用户 C 函数。四线程 1000 批实测通过，4194304000 次用户循环
及 1536000 次 syscall 后未见寄存器不一致。覆盖普通 syscall、主动
让出、睡眠及长用户计算；当前内核仍带观察点，不能直接排除图形并发、
信号或跨进程场景。并发图形测试尚未启动即失去串口回显，因此未执行。

补充读取序列检查：失败的纹理 PID 15 在 writer-watch-texture 日志中
从偏移 0 到 500819 的 139 条读片段连续，全部片段指纹正确。PID 14
存在两条未观测区间，可能由日志交错/缺失造成，不能视为文件读取损坏。
此前“片段正确”的证据不等同于全部 PID 的完整文件校验，本次仅对
连续覆盖的 PID 补充完整读取序列证据。仍需查用户态使用数据后的状态。

### 私有映射与页表所有权修正

实际旧 sys_mmap 分支不检查 MAP_PRIVATE，也只用 seg.size >= len 选择
ELF 缓存段，再取 seg.kva + 文件偏移；文件偏移不是段内偏移，存在越界
和私有页共享风险。实际分支执行回归先失败，移除 EL1 mmap 对此私有
装载器缓存的复用后通过。普通文件继续使用既有分配/读取路径，设备
继续使用 mmap 回调；不能因此宣称普通 MAP_SHARED 已具备完整写回语义。

arch_process_unmap/protect 原来直接修改可能从内核根表借来的下级表，
未经过 map 所用的私有所有权确认。实际入口的四项回归先失败；补齐
ensure_owned 后验证内核表不被修改、克隆失败不执行修改，修复后通过。
两类缺陷是确定的代码问题，仍未证明为板端 slab_meta 改写的直接来源。

观察点自检版 CRC `1879ca24` 只改专用 canary；输出自检前缀后 COM5
无回显，没有捕获预期异常报告。自动观察点已停止介入 IRQ 恢复，不再
依据此前未命中排除 CPU 写入。自检前 boot 日志已存在 ext4 inode 8/2
及 journal bmap 错误，块号 4294967295；需区分媒体损坏和读取实现故障，
未执行格式化或修盘。存储日志仍确认 SD 为 mmcblk0、eMMC 为 mmcblk1。

新增只报告的用户物理映射检查：若映射覆盖 buddy 描述符数组，打印
PID、VA、PA 和调用地址；不拒绝映射，不隐藏原故障。最终 ELF 的 DWARF
布局检查未发现跨模块差异：process_mm 48、vspace 16、buddy_page 40、
slab_page 64 字节，slab_meta 偏移 32。新版本待上板，不发布完成标签。
# 2026-10-10：U-Boot 独立读取 eMMC 元数据

DDR800 构建与烧写：

- 用户授权 eMMC 和 SD 都更新 DDR800。独立工作目录为 D:/workspace/codex-workspace/nanopc-ddr800-20261010，原 WSL U-Boot 未编辑/清理。
- 从 U-Boot v2024.07 HEAD 3f772959501c99fbe5aa0b22a36efe3478d1ae1c 导出源码，叠加原 tracked 修改，仅新增替换完整 DDR 参数 include；沿用原 .config 和 BL31，四并发构建 271.2 秒成功。
- 实际 TPL DTB 的 1530 个参数与标准 1600 表逐项一致，800MHz/LPDDR3/双通道；DTB 存在于 TPL binary，组合镜像布局和 FIT 检查通过。
- 新 idbloader.img：167936 字节，CRC cdf10305，SHA256 3c968974e73718479d9747f781614f06369b8f88dda7fdb50ea40992de5cc6c4；FIT：1185280 字节，CRC 64371d5b，SHA256 c09b68d567c2080608a45a456a8445f8c01a5965ba258cee6f99a8b9a1c770dd。
- 烧写前物理 eMMC 的 MBR/保留区、环境、IDB、FIT 已备份至 D 盘，转储大小及 CRC 检查通过。SD 保存了分区表/保留区和环境区域；依用户要求没有另行转储旧 SD FIT。
- SD mmc1/fe320000/SD32G 和 eMMC mmc0/fe330000/AJTD4R 的首分区都从 LBA409600 开始；分别先写 FIT（LBA0x4000，2315 扇区）、再写 IDB（LBA64，328 扇区），只写启动有效载荷，未连续覆盖完整镜像的填充区域。
- 两介质都通过 TFTP 大小与两次 CRC、写后读回两次 CRC和逐字节比较。原 MBR/保留区 CRC：eMMC 3c95bc2f、SD 3e203bb9；环境区域 CRC：eMMC d574fa86、SD 011ffca6，写后均一致。
- 写命令在回车执行前严格核对串口字符回显，并检查控制器报告的实际设备/LBA/扇区数。任一不一致就停止；不把 U-Boot 空回车（可能重复上一条命令）当作安全同步。
- 两个 flash-result JSON 均为 written and verified; cold boot pending。已开启 COM5 冷启动采集，待人工断电上电；尚未认定 DDR 根因或图形稳定性恢复。
- 烧写后首次 180 秒采集收到 0 字节，未确认 POR/800MHz/提示符。脚本退出并关闭 COM5；不能推断板卡启动失败或把安装成功等同冷启动通过。

网络检索与本地 DDR 参数核对：

- OpenWrt 官方源码保留 NanoPC-T4 内存不稳定修复：
  https://raw.githubusercontent.com/openwrt/openwrt/master/package/boot/uboot-rockchip/patches/101-nanopc-t4-fix-memory-unstability.patch
  补丁将 rk3399-sdram-lpddr3-samsung-4GB-1866.dtsi 改为 rk3399-sdram-lpddr3-4GB-1600.dtsi，描述了 memtest 失败和随机内核崩溃。
- U-Boot v2024.07 官方 NanoPC-T4 dtsi 仍包含 1866 参数：
  https://raw.githubusercontent.com/u-boot/u-boot/v2024.07/arch/arm/dts/rk3399-nanopc-t4-u-boot.dtsi
- 本地 /home/surest/nanopc-workspace/u-boot 同样包含 1866 表；dtsi 工作区修改只增加 SD sample phase=0，没有 DDR 修复。RAM 驱动/DDR 参数文件未出现在本地 git 修改列表。
- 对实际生成 tpl/u-boot-tpl.dtb 的 /memory-controller/rockchip,sdram-params 用 fdtget 解析：1530 个 u32；按 2 个 channel 结构布局，base 从 cell 34 开始，ddr_freq=933、dramtype=6（LPDDR3）、channels=2、stride=13。
- 1600 参数表的 ddr_freq=800。这里 933/800 是 MHz 时钟，1866/1600 是对应双倍数据率（MT/s）；不能混称实际时钟 1866MHz。
- 本地 TPL DTB SHA256 a6a627424c4dd3b76f29371276eed49403716d142da48a612c600710cbc2033e；output/u-boot-rockchip.bin SHA256 8d202337dcc2a97faf5a1baa9a6277a393ba699e2cc45c2bfc1bbb1c7c30d015。与此前板端 933MHz 输出一致，但未逐字节验证当前板端 bootloader 与本地镜像完全相同。
- 原补丁讨论中作者报告同频 rkbin DDR blob 正常，而开源 TPL 不稳定，并提到板卡差异；因此调查对象是 TPL 参数/训练实现，不应断言芯片绝对不能运行 933MHz：
  https://www.mail-archive.com/u-boot@lists.denx.de/msg481827.html
- Rockchip 官方 RK3399MINIALL.ini 使用 rk3399_ddr_800MHz_v1.30.bin，FriendlyElec 构建脚本采用其 uboot-rockchip/rkbin 流程，不能与当前开源 TPL 混同：
  https://raw.githubusercontent.com/rockchip-linux/rkbin/master/RKBOOT/RK3399MINIALL.ini
  https://raw.githubusercontent.com/friendlyarm/sd-fuse_rk3399/kernel-4.19/build-uboot.sh
- DDR 初始化/训练已成为有直接源码证据的高优先级候选，尚非本机根因定论。建议只更换完整 1600 参数表（不是仅改 933 常量），重编 TPL/完整启动镜像并冷启动，重复 memtest/eMMC/TFTP/PNG 和图形验证；本次调查未修改或烧写 U-Boot。

冷启动对照准备：

- 持续采集 90 秒未收到启动输出；Windows PnP 中 CP210x COM5 状态 OK。仅发送回车，在 1500000、115200、921600 三个速率均收到 0 字节；未改板端波特率/环境，串口句柄均已释放。尚不能判定是供电、启动链或串口链路问题。

- 用户确认已执行断电上电；但随后 COM5 打开未收到可辨认输出，未取得 POR 或 U-Boot 提示符，因此未宣称冷启动校验通过。
- COM5 已转为持续启动采集，等待再次触发上电以捕获 TPL/SPL。此前软件重启记录为 RST，尚不能排除残留 DMA 状态或平台初始化影响。
- 没有启动 CRC 不匹配的 Linux 镜像，没有停用 USB 控制器绕过；原工作空间未修改，未提交验收 tag。

PNG 最小复现与跨环境读取完整性（尚未闭环）：

- 新建 luna-test/png-context-probe，使用 glmark2 同源 zlib，不创建 EGL/DRM/GPU 作业；主机正常输入/篡改输入测试 2 项通过。文件/IDAT/解压流 FNV 基准分别 b9a73c4c、9e12187a、8f315671。
- 初版 ELF 2985840 字节，SHA256 f101a54096968ab0774ed2e412e60212b0a7162ad256fa07299c99d1aafef59e，上传及 PNG 回读核对通过。未启动 Weston 的单进程仍解压失败：输入 FNV 9e12187a，输出 33362ce7。
- 同一 ARM64 ELF 在 WSL qemu-aarch64-static 通过；保存失败解压流后主机比较，786944 字节初次只有偏移 190376 的 0 变成 2。后续快照回读又出现更多相同位变化，不能直接把回读差异认定为解码器写入。
- GP/NZCV 探针补充 x0–x15、x18–x29 哨兵和不修改条件码的循环；x16/x17 用于探针自身，未完整验证。QEMU 2 线程/20 批次通过，COM5 2 线程/100 批次通过，非全部异常/所有寄存器通过。
- 最新 PNG 探针补传出现回读不一致，随后已发生的解压结束前后执行不计作可信版本验收；停止继续加载，优先验证读取完整性。
- 不执行新程序，ELF 两次 FTP 回读：第一次 SHA256 2f2aba36cc6232cfa76b190dafbca7ca794b7d250117eed06c77e909f5970c1f 与主机一致，第二次 21035213f123f03d2b6b66311cfe55fdeccb1c6d48bcc234f8b02fea17f3b264，差异仅偏移 0x287d58 的 0→2。
- Luna shell 两次 md5sum 同一 ELF：2e9a22e8fa1eb54de9dc40d683aaac25（正确），随后 0a2175a4f3ff763b5de37be8e8654eb9。不能再把问题限定于用户态 FP/PNG/GPU。
- 软件 reboot 后 U-Boot SPL 首次 u-boot 镜像 SHA256 报错，自动重试成功；Reset cause=RST。不得据此宣称启动区被写坏。
- U-Boot 同一 ELF 加载到 0x04000000 CRC=1a585d59（正确）；加载到 0x04400000 CRC=e320ad83；cmp.b 差异同为偏移 0x287d58、0→2。两缓冲区不做 I/O 的重复 CRC 稳定；正确缓冲区 CPU cp.b 到 0x04800000 后 CRC 正确。首次 cp.b 回显被破坏、命令未执行，其后未初始化目标 CRC 被排除；较慢重新发送 cp.b 才确认执行成功。
- U-Boot eMMC 当前 MMC High Speed 52MHz、8-bit；mmc dev 0 0 0 后模式未改变，因此未认定 legacy/降频对照成立。随后同地址两次 ext4load CRC 正确，故障间歇性。
- 再通过 TFTP 加载 Linux 镜像：板端 42349056 字节 CRC=1ec23ebc，与期望 d6955d14 不符，救援启动中止，没有执行未校验镜像。
- 主机独立向既有 TFTP 服务读取同文件：42349056 字节，CRC=d6955d14，SHA256=81cb13b0e7cec2dd010c041a1b135584eec39c7377dccce8c0900a46e30669a5，与本地一致；未停服/重绑。板端坏缓冲重复 CRC 稳定。
- 下一步要求真正断电冷启动并核对 POR，重复 eMMC/TFTP 校验。残留总线主设备 DMA、缓存/内存属性、平台/供电/硬件均仍是假设，不把任何一项当已确认根因；未停止 OHCI 绕过或修改启动汇编。

控制唤醒修复版的物理复测：

- 完整集成重编 126.79 秒，33 项既有警告，无错误；BIN SHA256 52c9d9c1453c7ea60d20fe9ef94ffc0f9e042251c1fb25ef56a8cb5c9fb191fb，板端 CRC 91cd2118。ELF 审计 unexpected_fp_simd_functions=0。
- 保存 /env 后 shell reboot 返回 U-Boot，新镜像正常挂载 eMMC 并启动 Weston，环境文件生效。
- 四纹理客户端 PID 4–7：仅 PID 4 完整运行，312 FPS / 单场景 score 311；PID 5–7 报 libpng incorrect data check，score 0，却均退出 0。用户确认只有一个窗口且未卡住。不能把这一轮视为四窗口通过，也不能把单场景分数当全套 glmark2 评分。
- 四客户端退出后 shell/ps/inputstat 响应，17 个基础线程；该轮未观察到 gpu sched timeout，但三个客户端提前失败，不能据此证明超时已修复。
- 原 FP 探针不同进程具有相同哨兵，存在跨进程串线漏检空缺；新增第三参数 nonce 区分 Q 哨兵，实际生成函数旧版失败，新版通过。
- 新探针 ELF 3458912 字节，SHA256 ebe59a1de20f32f4b38b0fefe11c2e812d6467e134924059542f00d837f1a055，FTP 回读一致。
- 同时运行四进程 PID 8、11、14、17，各 2 线程、500 批次，nonce 1–4：四进程均 failures=0、fp_context_probe_pass、退出 0。共 4194304000 整数循环迭代、1536000 次原始系统调用；测试后 shell/ps 响应，18 个线程（含 FTP）。这覆盖独立进程 FP 哨兵，不覆盖所有 GPR、信号或四个 GPU 客户端并发。
- PNG 并发错误、SLUB 破坏与完整资源回收仍未闭环；未提交或打验收 tag。

重建后的图形恢复与新的阻塞证据：

- 冷启动 Luna CRC a225385d，6 核、eMMC 挂载、鼠标与触摸屏枚举正常；FP 探针 2 线程 1 批次返回 0。
- 初始 rootfs 部署漏掉 artifacts/armv8a-user/mesa/libgallium-25.2.8.so；已按固化 manifest 补齐该库、modetest、kmscube，FTP 回读 SHA256 均一致，并补入部署脚本。不能把此前 574 文件校验通过等同于依赖闭包完整。
- Weston 启用 HDMI 1920x1080；用户确认时钟 PID 9、计算器 PID 10 的两个窗口、鼠标拖动正常。SIGTERM 后两进程退出，shell/ps 响应；仍有 cursor dnd-* 缺失和 iconv 警告，不认定无报错验收。
- 四个 800x600 texture:duration=30.0（PID 11–14）出现后，用户确认画面卡住；shell/inputstat/ps 仍响应，四客户端 active syscall 29，ioctl 0xc02864c3（同步对象等待）。Weston active syscall 22。
- 作业超时：js=0、config=0x3304、status=0、head=tail=0x4671540。此证据不能区分硬件作业未运行、完成 IRQ 丢失、软件 fence 未通知；不把 status=0 当作完成证明。
- Runtime wake_up_process 只设置首次运行标志；kthread_park 设置标志后没有唤醒等待队列，可能卡在 GPU 恢复。实际函数测试旧实现失败；新实现为 task 增加控制通知源，wait_event 同时订阅业务/控制源，取消订阅后再销毁 completion。9 项主机测试通过（含正常通知、第二订阅失败回收），完整集成重编中，未硬件验收。
- 该唤醒缺陷不等同于 GPU 首次超时或 SLUB 破坏根因，后续仍需分别定位。

用户随后明确要求重做磁盘并重新上传资产：

- 仅重新格式化 Linux /dev/mmcblk2p1（MMC AJTD4R，起始 LBA 409600，长度 30126080）；不改变分区表、前 200 MiB 启动区或 SD 卡。
- 使用救援环境 /usr/sbin/mke2fs 1.46.5，4096 字节块、256 字节 inode；启用 has_journal、ext_attr、filetype、extent、sparse_super、large_file、extra_isize、metadata_csum；未启用 flex_bg、resize_inode、64bit。未把该特性选择认定为原破坏根因修复。
- 新 UUID 3587a595-2b06-4d81-9a12-037851a414bc，标签 luna-graphics；格式化后 e2fsck -fn 返回 0。
- 本地固化 output/rootfs 的 graphics、Qt 库/插件与稳定示例重新部署，补充 /lib 的 glibc 解释器/基础库以及 fp-context-probe.elf；省略过程诊断 Qt 程序。
- 部署包包含 574 个文件，46194904 字节，SHA256 2713c9aedc2b69adc3dad387cd6793931a9cd04b7e15d3761b21b9f0a7df7a90；救援板端包校验一致，解压返回 0，逐文件 sha256sum -c 返回 0。
- sync/卸载后再次 e2fsck -fn 返回 0，632 个 inode、104143 个已用块。仅证明 Linux 部署及文件系统检查通过，尚需 Luna 挂载和图形/回收验收。

Linux 救援恢复阶段：

- TFTP 启动 nanopc-linux-6.6.155-Image、rk3399-nanopc-t4-linux66.dtb、rk3399-rescue.cpio.gz，均通过板端大小和 CRC 检查，出现 RK3399_RESCUE_READY。
- Linux eMMC 是 mmcblk2（MMC，AJTD4R），分区 mmcblk2p1 起始扇区 409600；救援根为 RAM，检查前目标未挂载。
- `e2fsck -fn -b 32768 -B 4096` 发现 inode 校验错误、疑似垃圾 inode，最终中止；未使用首次命令中错误展开的返回码作为证据。
- `e2fsck -p -b 32768 -B 4096 -z /tmp/emmc-repair.undo` 返回 4：日志事务 4 损坏，根 inode 校验修正，遇到 inode 81 疑似垃圾后停止，需要手工修复。
- 随后 ro,noload 挂载可列出部分目录，但 graphics、qt5、多项图形库等仍报 Bad message；已卸载，不把可挂载认定为恢复完成。
- D 盘 disk-recovery-20261010 已保存：原主分区前 8388608 字节，SHA256 f8b6bd262b5cfd48da029280cd0be965e288946061adfd61ec21dd1aab991c8a；撤销文件 32768 字节，SHA256 a22363c9e881c58c8aa8fa84465745bb0286846315649bbb9d8547238f3c0c44。
- 卸载后 `e2image -Q` 保存全文件系统元数据 QCOW2，33374208 字节，SHA256 9fef19bc2676212176cb82bbb5faf916a33701452f47943df9b2874ead5e89ba。元数据镜像不是完整用户文件数据备份。
- 尚未允许批量清除损坏 inode，未格式化；图形压力验收仍未恢复。

后续只读取证：

- 块组 1 的备份 GDT：绝对扇区 0xa4008；块组 3：0x124008。
- 分别读取 16 扇区到不同 RAM 缓冲区，`cmp.b` 确认 8192 字节完全相同；两份 CRC32 均为 e7864dcf。
- 主 GDT 首块 CRC32 为 42321d24，不等于全 ff 的 4096 字节 CRC f154670a；因此不能描述为整块全 ff，只确认起始 192 字节读到 ff。
- 主 GDT 下一块起始数据不是 ff，损坏范围尚未完整测量。
- 备份 group 0 的 inode 表块号 0x423；读取绝对扇区 0x66118，根 inode（块内偏移 0x100）的模式为 0x41ed，extent magic 为 0xf30a。
- 备份一致和根 inode 可读不保证整个文件系统正确，更不能证明哪个写入者导致主 GDT 损坏；恢复前应使用标准 Linux e2fsck 只读检查，保留原始元数据。

- COM5，1500000；U-Boot `mmc dev 0` 对应 `mmc@fe330000` eMMC。
- DOS 分区 1 起始扇区 409600，长度 30126080 扇区。
- 只读执行 `mmc read 0x03000000 0x64000 0x10`，返回 16 blocks read: OK。
- 超级块偏移 0x438 为 `53 ef`；偏移 0x418 的 s_log_block_size 为 2，即 4096 字节。
- 分区偏移 4096（首个组描述符块）的前 64 字节全部为 ff。
- 独立再次执行 `mmc read 0x03100000 0x64008 0x8`，返回成功，前 64 字节仍全部为 ff。
- 这解释了 Luna 从 bg_inode_table_lo 得到 0xffffffff；并非仅由 Luna ext4 的组描述符解析生成。尚不能区分介质内容损坏和底层读异常，也不能据此确定破坏者。
- 未执行格式化、fsck 修复或磁盘写入；本轮所有 mmc 操作只读，目标地址是 U-Boot RAM 缓冲区。
- 图形验收阻塞；映射修复、页表所有权与观察点异常处理的 8 项主机测试通过，不等同硬件稳定性验收。

## 2026-10-10 六客户端冻结与存储错误联合取证

- 同一集成镜像 CRC `d276077e`，六个 800×600 Wayland 纹理客户端每 5 秒重建场景，人工确认冻结；不算验收通过。
- 第一轮冻结时 shell 仍响应，card0 提交计数固定为 6856，事件读取固定为 3429，多次查询均未增长，ready/pending 均为 0；随后 COM5 无回显。
- 第二轮周期采样后人工确认冻结；提交/读取停在 2152/1077。客户端仍输出约 47 FPS，不代表显示正常。
- 线程栈显示部分客户端等待 poll 信号量，其他时刻存在全局 epoll 锁等待且持有者变化；尚未证实永久死锁。Weston 仍执行 PRIME 导入和 GEM 释放。
- SIGTERM 发送给 PID 4 后确认 exit code=0、fd close complete、zombie published；给 PID 5 发送后出现 ext4 read `-110`，随后 `rk3399-sdhci: cmd18 irq error int=0x18100 adma=0x0 present=0x15df0206`、块读 `-5` 和 PNG IDAT CRC 错误。
- 未继续发送 PID 6–9 的终止命令，后续采样超时；不能声明全部客户端回收。PNG 错误可能是读故障的后果，未验证落盘文件已永久损坏。
- 后续须分离 eMMC 并发读、运行中块读超时与图形提交停滞，不能仅凭最后 ioctl 或文件锁等待认定根因。
- 有界证据：独立调试目录中的 `com5-events-six-frozen.summary.json`、`com5-early-freeze-stopped.summary.json`、`com5-early-freeze-term.summary.json`。
- 复位后同一镜像、不启动 Weston/GPU：单探针 20 轮解压通过；六个独立探针 PID 2–7 各 100 轮解压全部通过并退出 0，线程恢复到 14，shell 响应。探针每进程只读一次文件，不能当作每轮重新读盘，也不能排除缓存影响。
- 板端纹理文件 MD5 `e8a1f21e19f50f513e9490dd52ce78b0` 与本地源码资产一致；本次未证明持久化文件损坏。证据为 `com5-storage-png-single`、`com5-storage-png-six`、`com5-storage-png-end` 的有界采集。
- SDHCI 取消路径关闭 SIGNAL_ENABLE、清 INT_STATUS 和软件请求指针，当前未执行命令/数据状态机复位；需验证超时后的 DMA 停止与迟到 IRQ 边界，尚不能将此审计发现等同最初画面冻结的根因。
- 继续对照时，PNG 六进程全部退出、ps 恢复 14 后，下一条 Weston spawn 无回显且未取得 PID；再次空回车仍无响应。不能假定 Weston 已启动，拟进行的 GPU+并发读对照尚未执行。证据为 `com5-storage-gpu-control-weston` 和 `com5-storage-no-gpu-late-check`；命令失响应也需调查独立进程回收/存储路径。
- 下一次复位后无 Weston 对照：六个 PNG 探针退出 0，随后 90 秒周期 ps/ints 查询持续响应，另一次 load 探针也校验通过、退出 0，ps 恢复 14。未复现持久的无 GPU 回收失效，不据此排除竞争条件。
- 随后启动 Weston PID 8，HDMI 启用，启动期间采样超时；独立复查空回车、drmdiag events、ps 均正常，线程为 17。card0 commit=107/read=54、fail=0、ready/pending=0。本例证明单次脚本超时不能直接认定整机卡死，需复查；此前两次无回显仍仅为观测，不升级成已证明的回收根因。
- 证据：`com5-lifecycle-six-png-idle`、`com5-lifecycle-after-idle-reload`、`com5-lifecycle-reload-weston`、`com5-lifecycle-weston-recheck`。

## 2026-10-11 无纹理对照与 timerfd 丢唤醒修复

- Weston 与六 PNG 校验进程同时运行，人工确认正常，六进程退出 0、线程恢复到 18（含诊断线程）。随后六个无纹理 build 客户端也被人工确认冻结，PNG 解码不是必要触发条件。
- 无纹理冻结时 shell 响应、GPU 作业继续，card0 commit=1934/read=969 多次不变，无积压事件。六客户端 SIGTERM 均正常退出且线程恢复 18，但人工确认画面仍冻结，不能将未回收进程作为解释。
- 退出后 Weston 主线程栈位于 epoll 等待，未取得硬件暂停 PC，不能认定所有先前 syscall 标记都是实时执行停点。
- 审计发现 timerfd_poll 先检查 expirations 再订阅 poll_source。首次订阅之前一次性定时器到期时，旧实现既返回未就绪又没有通知等待者。
- 执行真实 C 函数的测试在订阅前注入到期：旧实现退出 2（未返回可读）；修复改为先订阅后检查，测试及 timerfd/pselect 相关回归共 5 项通过。不增加周期轮询或固定延迟。
- 此修复证明 timerfd 的一个真实竞态，不证明所有板卡冻结均由它造成；尚待新集成镜像上板验收。
- 修复版完整集成构建 returncode=0，BIN CRC dfebcebd。人工确认初始桌面正常，六 build 客户端再次被确认冻结；commit=1892/read=948 不增长。timerfd 修复不足以解决本机显示停滞，不登记为图形验收通过。
- 自动进度检测已接入独立目录 six_client_reclaim.py：仅在持续渲染阶段预热 5 秒后，每 2 秒读取 card0 commit/read；任一通道连续 10 秒不增长即失败，计数倒退或采样损坏也停止，不将其判据用于空载桌面。
- 4 项检测器测试通过。observe-only 在当前六客户端 PID 4–9 上约 15 秒自动判 render_progress_stalled，立即保存 DRM/pstate/线程栈/输入/IRQ/VOP 现场。客户端仍输出约 47 FPS；不以 FPS 或退出码代替显示进展。
- 自动判据只证明提交/完成事件停滞，不等于逐像素画面验收；成功轮次仍明确 visual=unverified。失败现场留存，不自动复位、清除事件或继续其他轮次。
- timerfd 数值诊断版 CRC ee42e3dd 自动测试在约 18 秒后停止提交，约 30 秒自动失败并抓现场：Weston timer armed=1、settime result=0，期限 40843209916ns；now=54563945333ns、fires=750 未增长。再次 now=81453705375ns 时仍未到期回调。另一个进程周期 timer 正常到期，不能解释为全部系统时间停止。
- 源码与执行测试确认：__mod_timer 解锁后线程可迁移，随后直接编程旧 CPU 会被 timer_program_local_hardware 静默跳过，但入队返回 0。测试在解锁时注入迁移，旧实现退出 3（未编程）。
- 修复入队后请求归属 CPU 重新读取树并重编；本地判断到重编保持 CPU 身份稳定；树选择与硬件写入保持同一短临界区，中断处理末尾亦如此，避免旧期限覆盖新最早期限。回调仍在锁外执行。
- 迁移与相关回归 9 项通过、远端重编契约通过；本次内核修复待集成新镜像实际回归，不提前登记图形稳定性通过。
- 归属 CPU 重编修复集成成功，CRC 91d3b482。自动六 build 客户端持续 45 秒提交/读取增长至 3234/1617，六客户端退出 0、pstate 均 ESRCH、线程恢复 18；单轮系统检查通过，visual=unverified。
- 随后纹理三轮计划首轮即中止：约 10.47 秒最后有效样本 commit=4685/read=2343，其后 drmdiag events 查询等待扩展到 20 秒仍无提示符；独立空回车复查也无回显，未取得新 timerdiag 快照。无明确 panic/存储错误可归因。
- 因此修复候选不能登记完整稳定性通过。计划三轮仅首轮启动，其余未执行；自动测试停止并保留故障，不在失败后继续轮次。
- 证据：`enqueue-fixed-build-round1.json`、`six-client-reclaim-results.json`、`com5-enqueue-fixed-texture-failure`。旧 timerfd 竞态和新入队迁移竞态均有执行测试证明，但不能把所有卡死归因于同一缺陷。
- 同 CRC 91d3b482 复测：纹理 45 秒自动系统检查通过；随后三轮计划第 1 轮通过，第 2 轮 timerdiag 提示符超时停止。独立复查恢复，timer arms/fires 从 7543/3770 到 10305/5152，DRM commit/read 随后增长到 12128/6065，不能认定本次超时为渲染冻结。
- 自动脚本已补空回车复查（不重发原命令），仍失败记 command_completion_unconfirmed；提示符复查及进度判定共 6 项测试通过。不把暂时无回显等同停机。
- 同一第 2 轮的六 PID 16–21 继续观察 25 秒提交/事件增长，再逐个 SIGTERM 全部退出 0，线程恢复 18，退出后仍有提交推进至 17330/8667。本轮由独立补充检查确认，不能追补成原三轮脚本完整通过，第 3 轮未执行。
- 证据：`enqueue-fixed-texture-retry-pass1.json`、`enqueue-texture-transient-command.json`、`com5-texture-repeat-progress-recheck`、`com5-texture-transient-cleanup`。仍待更多轮次及画面/输入确认，不宣称 100 次验收通过。
- 回收后再次尝试三轮时，初始 ps 经空回车确认仍无响应，未启动任何新客户端；网络探测超时/主机不可达亦未确认板卡存活，不能记录为新渲染轮次失败。
- 审计并执行测试复现 stop_timer 的另一漏洞：到期处理出树后先设 cpu=-1 再执行回调，旧 stop_timer 看到 -1 直接返回，允许 k_hrtimer_delete 在 running_timer 仍指向该对象时释放它。测试旧实现退出 2（未等待回调）。
- 修复移除该提前返回，依据保留的 raw_timer 基座锁下同步 running_timer，回调结束后才能删除/释放；回调仍锁外执行。相关测试 13 项通过。此为独立生命周期缺陷，硬件相关性仍待新镜像回归。
- 回调删除同步修复集成成功，CRC 53432cc5。相同 Weston、未重启，自动完成两轮六纹理客户端：每轮持续 40 秒提交/读取增长、六退出码 0、各 PID ESRCH、线程恢复 18，再空载观察 45 秒，各 13 次 ps 复查正常。
- 第二轮结束后独立 COM5 重新打开查询正常：线程仍 18；Weston timer armed=0、next=0、pending=0，另一周期 timer 按期继续运行，未观察到逾期未回调。
- 本结果仅为两轮系统与回收检查通过，不等于 100 次、冷重启或像素/鼠标拖动验收。继续保留之前失败记录，不据此宣称所有内核/平台均通过。
- 证据：`timer-lifetime-two-rounds-pass.json`、`com5-timer-lifetime-two-rounds-postcheck`。
- 继续扩展 5 轮时，初始 ps 在正常等待、额外等待和空回车复查后仍未确认完成，脚本停止，尚未启动新客户端。独立空回车亦无回显。故 45 秒回收后观察不能作为更长时间稳定性的充分证据；本次不是新增 5 轮渲染测试失败。
- 证据：`six-client-reclaim-results.json`、`com5-lifetime-fixed-later-noecho`。尚未取得最终线程/IRQ停点，不将新失响应直接等同之前已复现的 timerfd 或删除竞态。
- 同 CRC 53432cc5 复位后，自动完成六纹理客户端 40 秒运行、退出和回收，随后连续空载 180 秒（45 次 ps/timerdiag 检查），线程保持 18、周期 timer 正常推进。
- 再静默 60 秒不发送命令，关闭并重新打开 COM5，空回车/ps/timerdiag 均响应；周期 timer fires/reads=5/5、next 大于 now，Weston 一次性 timer 正常未设定，无逾期遗留。
- 本轮系统检查通过；连续查询可能改变竞争时机，因此另保留静默观察结果。单轮长观察不证明已解决所有晚发失效，也不代表像素画面、拖动或 100 次验收。
- 证据：`timer-lifetime-180s-idle-pass.json`、`com5-post-reclaim-silent-minute`、`com5-after-silent-minute-recheck`。
- 压力切换八窗口：先前六窗口运行被在无遗留客户端的空载阶段停止，以切换测试参数；未完成轮次不追补通过。脚本统一以 --clients 参数检查全部 PID/退出码。
- 同 CRC 53432cc5 八窗口 100 轮计划：前 2 轮系统检查完整通过；第 3 轮八客户端渲染和回收完成，空载检查 8 次后 ps 经过等待及空回车仍未确认完成，独立复查无回显，脚本停止，其余轮次未运行。
- 最后 timerdiag now=302117849541ns：Weston armed=0/pending=0；周期 timer fires/reads=4/4，next=306086507958ns，大于该次 now。尾部出现 NUL/异常字节。该快照不支持当时已发生旧的一次性 timer 逾期未回调，亦不能凭异常字节认定内存或 UART 时钟根因。
- 证据：`eight-round3-idle-failure.json`、`com5-eight-round3-idle-recheck`；八窗口完整自动系统检查当前为 2/100，不等于视觉或总体验收通过。
- 调度/IRQ采样轮次先因并发 stdout 插入 DRM 数值行而停止严格解析；同一八 PID 再观察提交从 6016 到 7404、读取从 3008 到 3703，不能将解析失败视为冻结。只读采样已限制重试 3 次，保留原始数据且不拼造数值，相关检测器测试 8 项通过。
- 随后真实停点：八进程长时间处于 DRM_IOCTL_SYNCOBJ_WAIT，MMU AS 锁 owner=0/waiters=0，系统 timer IRQ 继续增长。SIGTERM 后等待调用起点晚于投递时间，可能是用户退出清理再次进入等待，不证明 SIGTERM 未递送。
- SIGKILL 单进程实验打印 process[4] exit code=9 于 shell tid=14，之后未恢复提示符。源码确认 k_process_signal 的默认致命动作直接调用 k_process_exit，在发送方同步等待目标停止与 fd 清理；不符合异步投递语义，解释此实验的控制台被等待阻塞，不证明所有晚发失响应均同因。
- 修改进程级默认 TERM/CORE 为投递并唤醒，由目标返回边界执行默认退出。SIGKILL 强制不受忽略动作/阻塞掩码影响；目标驱动资源仍走正常释放，不强制释放未完成 GPU 对象。发送/接收执行测试旧实现 exit=4，修复及信号/协作退出回归 7 项通过。
- 新集成构建成功，BIN SHA256 8fc7fb4db68502af93fb0ac0729fc01ab3d8bf2cc8e457c5f093234472430fea，已更新 TFTP，尚待上板测试。GPU fence 完成/超时恢复仍未收敛，不能登记完整图形稳定性通过。
- 证据：`com5-eight-syncobj-stalled-state`、`com5-eight-fence-sigkill-one`，测试 `components/loader/tests/test_process_signal_wakeup.py`。
- 异步致命信号修复版 CRC 5dfe746d 上板：单客户端 PID 4 的 SIGKILL 命令及时返回 delivered，退出由目标 tid=19 执行，随后 pstate 返回 ESRCH，线程恢复 18；未复现旧发送方 shell 同步回收阻塞。
- 同镜像自动完成八纹理客户端 PID 5–12：40 秒提交从 16415 增至 19031，全部退出码 0、PID 均 ESRCH、线程恢复 18，随后 45 秒空载 11 次检查正常。本候选仅 1 轮系统检查通过，visual=unverified，不计为 100 轮或 GPU fence 故障已闭环。
- 证据：`com5-async-kill-pilot-result`、`async-signal-eight-round1.json`；既有 GPU fence/watchdog 恢复停点仍保留为未完成项。
- 同 CRC 5dfe746d 随后扩大为三轮时，初始 ps 经等待和空回车复查仍未确认完成，rows=[]，没有启动新客户端。独立 COM5 空回车也无提示符，串口已释放；这是上一轮回收后的晚发失响应，不能记录为三轮渲染失败或宣称异步信号修复解决全部冻结。
- 证据：`async-signal-late-idle-failure.json`、`com5-async-signal-late-idle-recheck`。GPU watchdog 配置 500ms，但既有停点未取得超时恢复执行现场，仍需 workqueue/GPU 调度线程诊断，不以强制完成 fence 规避。
- 同 CRC 5dfe746d 复位后，八纹理客户端 PID 4–11 持续 40 秒，commit/read 从 308/154 增至 2860/1430，全部退出码 0、各 PID ESRCH、线程恢复 18；回收后空闲 180 秒，43 次检查正常。
- 关闭并重新打开 COM5 后 ps/timerdiag 仍正常：线程 18，Weston timer armed=0/next=0/pending=0，周期 timer fires/reads=4/4，next=335790818875 大于 now=295960775541。仅证明本轮未复现逾期 timer 或晚发失响应，不证明长期故障消除；本轮 visual=unverified。
- 证据：`async-signal-eight-180s-idle-pass.json`、`com5-async-signal-long-idle-postcheck`。定时器迁移、回调删除、timerfd 注册竞态、异步信号相关执行测试重新运行 7 项通过。delayed work ticket 发布与回调释放存在待验证并发窗口，尚未归因或修改。
- 同一 Weston 未重启重复两轮：第 1 轮 PID 12–19 完成 40 秒纹理运行、全部退出 0/ESRCH、线程恢复 18，45 秒空闲 11 次检查正常；第 2 轮第一个 spawn 未确认完成，没有有效 PID，独立空回车无回显，串口已释放。
- 独立执行 queue_delayed_work 真实函数并注入 schedule 返回前回调完成，ASan 稳定报告 call->ticket 读取的 heap-use-after-free。说明该生命周期窗口确实存在，不证明本次板端失响应同因；生产实现尚未改动，回归测试以 strict xfail 登记已知缺陷，不能算通过。
- 证据：`async-signal-eight-repeat-spawn-failure.json`、`com5-async-signal-repeat-failure-recheck`；`components/linux-runtime/tests/test_delayed_work_publication.py`，使用 --runxfail 在 D 盘生成材料重现失败。
- delayed work 发布交接修复：提前到达的回调只登记到期，不释放调用对象；ticket 发布完后重新排队，业务回调始终在 worker 中执行，避免调用方持驱动锁时内联恢复。转交完成后发布方不再读取 call。提前/正常完成、取消清理和排队失败执行测试通过，取消 strict xfail；相关生命周期测试共 8 项通过。
- 集成重编成功，BIN SHA256 8f865373e6f73f68a02f84e2ce955f3c96076d44f17b2f0860d0ce4bb43f2109。首次 TFTP 仍为旧大小，脚本拒绝启动；覆盖现有文件并核对 SHA 后上板 CRC 29e47289，未修改 TFTP 服务。
- 新候选首轮八纹理客户端 PID 4–11 持续 40 秒，提交/读取从 302/152 增至 2898/1450，全部退出 0/ESRCH、线程恢复 18；45 秒空闲 11 次检查正常，visual=unverified。不能凭单轮通过认定长期冻结已解决。
- 证据：`publication-fixed-eight-round1-pass.json`、`com5-delayed-work-publication-fixed-boot-retry`；新候选正在继续不重启重复运行，未提交推送。
- CRC 29e47289 首轮后重复测试停在初始 ps，rows=[]，没有启动新客户端；独立空回车无提示符。已修复 UAF 不能据此归为全部晚发失响应的根因，证据 `publication-fixed-repeat-idle-failure.json`、`com5-publication-fixed-repeat-idle-failure`。
- 扩展只读 schedstat stack workers，选择 linux-work/linux-softirq/pan_js；保持 8 行、有限保存栈、运行中不读栈、锁外打印。默认图形范围和 pause/resume 限制不变，范围执行测试与生命周期测试 2 项通过。
- 诊断候选集成构建成功，BIN SHA256 1bcf0170c26a8ae9e60c83c70595f8f3baa8babb8429a251183fc2b3f3504b91，已更新 TFTP。COM5 仍无提示符，未加载，串口已释放，等待复位；构建成功不算上板验收。
- 用户复位后诊断镜像 CRC 6af469af 上板，schedstat stack workers 取得 8 个 Runtime/GPU 线程快照。八纹理客户端 PID 4–11 运行 40 秒并全部退出 0/ESRCH，线程恢复 18，空载 90 秒共 21 次检查正常，重新打开 COM5 后 ps/worker 栈仍正常，visual=unverified。
- 压力期间 worker tid=9 保存栈经匹配 ELF 解析为 drm_atomic_helper_wait_for_vblanks -> linux_osal_wait_for_completion；空载后回到 linux_work_loop 队列等待。该样本期间提交仍推进，不是已确认的永久死锁或 GPU 超时恢复停点。
- 此轮未捕获自动重启日志，不能判定先前无回显为硬件看门狗复位。目标 BSP/Runtime 源码检索未见显式 watchdog/wdt 初始化，不能排除固件遗留硬件配置；Panfrost 500ms 作业 watchdog 与整板复位不是同一机制。
- 证据：`worker-stack-eight-90s-idle-pass.json`、`com5-worker-stack-watchdog-check-boot`、`com5-worker-stack-post-reclaim-reopen`。脚本新增 worker 保存栈采样，仍保留有限尾部；100 轮与视觉验收未完成。
- 同 CRC 6af469af、同一 Weston 连续重复两轮八纹理运行，各 40 秒、退出 0/ESRCH、线程回到 18、各 45 秒空闲 11 次检查正常。期间一次提示符缺失通过空回车复查恢复，保留 prompt_rechecks=1，不能认作无异常的完整验收。
- 随后 60 秒不发送命令的串口采集无新启动输出；重新打开 COM5 首个 ps 无提示符，其余命令未发送。网络对照：压力中 192.168.137.11 两次响应均小于 1ms；故障后一次超时、一次由 192.168.137.1 返回 Destination host unreachable，不是板卡响应。不能认定仅 UART 失效，也不能凭此确定硬件看门狗、死锁或整机停转根因。
- 最后有效空闲快照中四个 linux-work 与 linux-softirq 均在队列等待，三个 pan_js 在信号量等待；timer IRQ 总数 722578、GPU job IRQ 74650、MMU IRQ 0。该快照早于最终无响应，不得作为停机现场。
- 证据：`worker-stack-eight-repeat-two-pass.json`、`com5-worker-stack-two-rounds-silent`、`com5-worker-stack-two-rounds-after-silent`。两轮仅限定采样窗口系统检查通过，扩展静默阶段失败；不追补为 100 轮或长期稳定性通过，串口已释放。
- 同 CRC 6af469af 新启动空载对照：仅 Weston 及其 keyboard/desktop-shell，没有启动 glmark2。基线线程 18，静默 120 秒后重新打开 COM5，ps/timerdiag/worker 栈/IRQ 查询全部响应，网络两次响应小于 1ms。
- desktop-shell 周期 timer fires/reads 从 0/0 到 2/2，next=196005275416 大于 now=168476179958；Weston armed=0，无已设置的逾期 timer。四个 workqueue 与 softirq 仍队列等待，pan_js 仍信号量等待。静默采集无新启动输出。
- 本单次空载对照未复现，不排除低概率空载缺陷，但不支持将分钟时钟重绘或 GPU 空闲本身直接定为根因。下一步应分离单客户端/多客户端退出及遗留资源状态；不关闭时钟、timerfd 或回收来规避。
- 证据：`com5-idle-control-boot`、`com5-weston-idle-control-baseline`、`com5-weston-only-idle-120s`、`com5-weston-only-idle-120s-recheck`。实际像素画面未人工确认，系统检查不代表显示验收。
- 同一 Weston 单纹理客户端自然结束对照：PID 4 运行 texture:duration=30.0，退出码 0，pstate ESRCH，线程恢复 18；随后静默 60 秒后 ps/timerdiag 正常，网络两次响应小于 1ms。分钟 timer fires/reads=8/8，next 大于 now。该对照同时改变客户端数、场景重建和退出方式，不能仅据此归因为并发。
- 脚本支持 --clients 1 保留六/八客户端验收参数，新增真实 gpu sched timeout 日志检测，进度/提示符检测器 8 项回归通过。严格单客户端对照 PID 5 使用与八客户端相同的每 5 秒重建及 SIGTERM：40 秒提交推进、退出 0/ESRCH、线程回到 18、60 秒空闲 14 次检查正常、prompt_rechecks=0；继续进行退出后静默观察。
- 证据：`com5-single-texture-natural-exit`、`com5-single-texture-after-silent`、`single-texture-sigterm-control-pass.json`。自然结束的一项 texture 分数 299 仅是单场景结果，不是全场景或 DRM 性能总分；显示未人工确认。
- 严格单客户端 SIGTERM 对照之后再静默 60 秒，重新打开 COM5 的 ps/timerdiag/worker 栈正常，线程 18、所有 Runtime worker 回到队列等待，分钟 timer fires/reads=12/12，next=796005275416 大于 now=765692015083。网络两次响应小于 1ms。
- 证据：`com5-single-sigterm-control-silent`、`com5-single-sigterm-after-silent-recheck`。本轮未复现，支持继续调查并发压力及共享回收状态，但不能以一次阴性结果认定客户端数量为根因，也未完成八客户端 100 轮。
- 后续初始 ps 再失响应，新的八客户端 rows=[]，未启动。独立空回车无提示符，网络一次超时、一次主机 .1 报不可达。与先前单客户端正常复查文件的时间间隔约 36 分钟（11:12:22 至 11:48:18），不是已确认的几秒内故障；实际失效时刻未知，期间是否有外部操作待用户确认。
- 因当前启动以来只做过单客户端对照，不再把故障限定为八客户端或多进程；短空闲成功不足以证明长期稳定。新增 --silent-seconds 将静默后的复查纳入每轮通过前条件，检测器 8 项通过；本次未进入该测试阶段。
- 证据：`after-single-long-gap-initial-failure.json`、`com5-after-single-later-noecho`。只读系统栈范围测试旧实现 exit=4，扩展 schedstat stack system 覆盖 System Timer Thread、system cleanup、signal foreground、shell、netx、drm-watch 后通过；保持默认图形与暂停控制范围不变。
- 系统范围候选集成成功，BIN SHA256 bd4a43364d53fb85f1797de4405c21aa98877c5a26569fd7a25958662ea3bf2d，已更新 TFTP。stack_debug.o 时间晚于源码，最终 ELF 反汇编含范围 2 分支，排除本次链接旧对象；两项范围/生命周期执行测试通过。
- COM5 仍无提示符，诊断候选未加载，串口已释放。后续需更长空闲对照并核对约 36 分钟观察空档是否存在外部复位/操作；不能据单客户端短期成功将故障定为仅多进程。
- 用户复位后新系统范围镜像 CRC 0c69a426 上板。未启动 Weston/glmark2/任何 Loader 用户应用，基线共 14 线程，system cleanup/signal/netx 为信号量等待，shell 正常；USB、存储、DRM 内核驱动仍初始化，不称为禁用设备的最小内核。
- 38 分钟不发送命令的串口采集完成（基线文件 13:12:14，采集文件 13:50:40，无 stop 文件）；尾部只有 00 11 BD 三个非文本字节，没有完整 panic 或新启动日志。随后首个 ps 无提示符，其余命令未发送，网络一次超时、一次主机 .1 报不可达，串口已释放。
- 此空载启动没有用户进程退出回收，因此图形应用/Loader 回收不是该次失响应的必要条件。实际失效时刻未知，也不能凭三个字节认定硬件看门狗、DDR、UART 或内核死锁根因。需要在失效前采集调度/IRQ现场，不再把调查仅限 Mesa。
- 766 秒附近的时间换算溢出假设经源码/执行测试不成立：muldiv64 使用 96 位中间结果；在四种频率、乘积边界、38 分钟至 24 小时输入上与 128 位参考计算一致，测试 test_long_time_conversion.py 通过，没有修改生产换算代码。
- Runtime 普通 spin_lock 不禁止抢占、preempt_disable 为 barrier 是已有语义缺口，本次未证明相关，不以全局调度锁或关中断替换规避。证据：`com5-system-scope-kernel-idle-boot`、`com5-kernel-long-idle-baseline`、`com5-kernel-only-idle-38min`、`com5-kernel-only-38min-postcheck`。
- 添加默认关闭的 ARMv8 IRQ 面包屑，schedstat irqtrace on/off 控制；仅记录各核 PC/PSTATE/分发阶段，无 IRQ 内打印、无新锁、无 SGI。phase=2 只表示 handler 返回，不是异常返回完成；读取为并发近似，历史 PC 不是实时停机 PC。
- 检查发现 ThreadX idle IRQ 传入的系统栈不保证完整 GP 帧，不能解引用为 regs->pc。诊断改为 current EL 读取 ELR/SPSR，lower EL 使用已有保存帧，不改变汇编或公开入口。旧诊断 idle 分支测试失败，修正后 EL1/EL2/EL3、CPU 越界、关闭路径等五项测试通过；缺失寄存器头文件的一次构建失败未部署。
- 修正版集成构建成功，BIN SHA256 f0d76c57499490e97be9f3f839f096f7da353a79dd1de9aead39fd268bfaa74a，上板 CRC 29bf908a；最终反汇编核对 current EL 读取 elr_el1/spsr_el1。
- 无图形应用，启用诊断后每 10 秒采样一次，持续三分钟；先 ping 两次小于 1ms，再串口 irqtrace/schedstat/ps 正常。CPU0 IRQ count=242811，phase=2；SMP owner=next=392771、count=0、preempt=0，线程 14。此仅验证取证链，非长稳定性验收。
- CPU0 初始历史 PC 解析为 rk3399_uart_putc，其他核为 _tx_solicited_return 的 ret；不能仅凭这些名称认定故障位置。后续先网络后串口，以区分静默中失效与首次串口接收诱发，前序一直先 ps 后 ping 的结果不能证明先后因果。
- 证据：`com5-irq-breadcrumb-boot`、`com5-irq-breadcrumb-baseline`、`com5-kernel-irq-breadcrumb-3min`、`com5-irq-breadcrumb-postcheck`；未提交推送，未解决长期失响应。
- 下次会话先网络不可达，再串口返回 U-Boot（对 schedstat 报 Unknown command），确认状态已变化，不得作为同一 Luna 失响应现场。上次健康文件 14:10:55，本次 14:29:56，期间是否人工复位待用户确认，不提前认定自动复位。
- U-Boot 只读 version 为 2024.07，Oct 10 2026 15:43:12；reset_reason 未定义，CRU glb_rst_st（0xff760514）读为 0。找到对应独立 DDR800 材料 `D:/workspace/codex-workspace/nanopc-ddr800-20261010`，生成时间与板上一致，配置未启用 WDT/WATCHDOG/SPL watchdog；不能用旧 WSL 根构建的 Aug 27 材料推断板上行为，也不能排除其他固件/硬件复位。
- 同 CRC 29bf908a 重新启动，仅 14 内核线程，无图形用户进程，每 10 秒轮换 IRQ/SMP/系统栈采样；uptime 553290977750ns 最后完整 IRQ 快照 CPU0 count=554474/irq=27/phase=2、历史 PC=0x2209d0c（UART putc）。随后 SMP owner=next=906083、count=0、preempt=0，系统线程快照仍正常等待。
- 后续 schedstat irqtrace 采样超时，采集自动写 stop 文件、停止发命令并保存尾部，没有自动复位。尾部提示符后有 00 00 40 f5 非文本字节；网络先探测超时/主机 .1 报不可达，独立空回车无提示符。最后正常快照不是最终停点，不能定为 ticket 锁死锁、UART 或看门狗根因。
- 证据：`com5-irqtrace-next-network-first`、`com5-uboot-reset-reason-readonly`、`com5-irqtrace-repro-fresh-boot`、`com5-kernel-irqtrace-long-repro`、`com5-irqtrace-repro-final-state`。采集提前因失败停止，未完成计划 38 分钟，不算通过；串口已释放。
- 显式开启诊断才创建 CPU5 高优先级观察任务（亲和性 0x20）。启动后不使用睡眠、同步、分配或调度锁 API；保持 IRQ 开启且 arch_cpu_relax 为 yield，不是 WFE。故障直写控制台仅一次，不复位/暂停目标；中断、观察核或 UART 本身故障仍可能让其失效，不声称等同硬件调试器。
- 初版总 IRQ 判定改为复用 k_time_timer_probe_get 读取 CPU0 tick 期限，避免设备 IRQ 风暴掩盖 tick 停滞，没有新增公开接口或改 tick 推进。判定器覆盖回绕/时间回退/单次报告，与 IRQ 帧路径共五项执行测试通过。
- 初版 CRC 0aba65a0 上板，绑定 CPU5、共 15 线程；off 后协作完成、CPU5 current/execute 清空，再次启用正常。停止只请求协作，完成任务的控制块留到再启用时删除，不把此结果叫全部内存回收。
- 旧观察器停止后显式 reboot 捕获完整 TPL/SPL/U-Boot，Reset cause: RST；UART 切换期间有 NUL。该次原因是命令重启，不能将所有非文本字节解释为自动复位或内核损坏。
- tick 期限版 BIN SHA256 6228d6effeb32ae57e30d9b98122384483ff4b668f5e07484bb2df1539aa9479，上板 CRC 3cf7d7e5。CPU5 观察状态 deadline 持续推进，随后 20 分钟被动采集、不发查询、未启动图形用户进程；尾部仅 00 00 00 00 00 00 00 20 a2 ff，无 observer 报告或完整 panic/新启动输出。先网络探测超时/主机不可达，再串口无提示符。
- 因观察器没有输出，不能定为仅 CPU0 tick 停止；可能观察核也被中断/异常停止、时钟或 UART 失效。panic 路径确实能通知其他核进入停机，但本轮没有证据证明调用了 panic。证据：`com5-independent-observer-baseline`、`com5-observer-stop-check`、`com5-observer-restart-check`、`com5-observer-candidate-explicit-reboot`、`com5-kernel-tick-observer-passive`、`com5-tick-observer-passive-postcheck`。
- 独立发现 __panic 用 vsprintf 写 512 字节栈缓冲区，写完才截断；真实函数长消息执行测试 ASan 报 stack-buffer-overflow，修正 vsnprintf 并处理负返回为 panic formatting failed 后通过。相关六项测试通过，不把独立缺陷等同本轮失响应根因。
- 修复版集成成功，BIN SHA256 1f1671126652e3d189be94cfcb65bfc9c55b66b8cf3ab9fdb91d94a49825c804，已更新 TFTP。COM5 仍无提示符、串口已释放，新镜像未加载；未提交推送，长期稳定性验收未完成。
- 证据：`com5-retry-1011-six-png`、`com5-retry-1011-build-frozen`、`com5-build-frozen-all-exit`、`com5-frozen-repaint-state`；测试 `components/loader/tests/test_timerfd_poll_race.py`。
- Weston 单独启动对照：CRC d276077e，未启动 glmark2，90 秒周期查询均响应；之后 inputstat/drmdiag 仍响应，commit=112/read=57，事件无积压。软件正常不代表实际显示正常。
- 人工随后反馈黑屏，`vopdiag` 查询和独立空回车复查均无回显，未取得黑屏后的寄存器状态。启动日志含 HDMI-A-1 enabled、hdmi route、vop vblank enable，无明确 panic/持续 ioctl 超时报告。不能宣称空载显示验收通过，也不能将六客户端压力视为必要触发条件。
- 证据：`com5-weston-idle-continuous`、`com5-weston-idle-input-baseline`、`com5-weston-idle-black`、`com5-weston-idle-black-recheck`。缺少从首次桌面出现到黑屏的人工时间点，不能判断是否从未点亮。
- 有界 panic 格式化镜像上板 CRC 3333fb81，TFTP 1817992 字节匹配；未启动图形应用，14 内核线程，启用 CPU5 观察器后为 15。静默 60 秒后先网络收到板端 TTL 回复，再串口 ps/observe 正常，tick deadline 推进至约 77.84 秒。只算短时诊断检查，不是长稳验收。
- 后续会话 `com5-resume-state` 空回车无提示符，停止发送后续命令并释放 COM5；未捕获最终停点，也未确认自动复位。此间外部操作与准确失效时间未知，不能归因为图形回收。已请求复位到 U-Boot；早期 RAM panic 记录尚未实现。
- 证据：`com5-bounded-panic-idle-start`、`com5-bounded-panic-idle-quiet`、`com5-bounded-panic-idle-postcheck`、`com5-resume-state`。未提交推送，长期冻结仍未闭环。
- 新增每核 64 字节 panic 阶段记录，入口在容错线程查询之前，写入后使用既有 arch_dcache_flush_range 写回；不申请内存、不加锁、不打印。阶段 1=入口，2=容错判断完成，3=同步日志冲刷完成，4=栈输出完成，5=全局停机，6=远端核停机；记录异常帧/格式串指针但不解引用。
- 两项真实 C 执行测试通过，集成完整构建 119.85 秒、40 警告、无错误。BIN SHA256 1bb9e3604d092eb88b23acddd007c757a03ba105817bae8a67eb0d66a398025f，上板 CRC e4f4809c，六核及鼠标/触摸枚举正常，未启动图形应用。
- 当前 ELF 的 panic_records 地址 0x023daf80；各核偏移 0x40，CONFIG_MAX_CPUS 对应记录总范围需按构建配置核对。复位到 U-Boot 后、TFTP 之前可 md.q 0x023daf80 30 查看前六核；有效 magic=0x50414e494352414d 且 stage_inverse=~stage。DDR 重训练、断电或缓存故障可能使记录丢失；本轮尚未触发真实 panic 验证留存，不能以空记录否定 panic。
- 用户复位后，在 TFTP 前读取记录区全为 ffffffffffffffff，未获得有效异常记录；CRU glb_rst_st=0，不推断故障原因。随后 U-Boot mw.q 写首字 canary，读回匹配；reset 捕获 RST，两次软件复位后首字仍匹配，证明该测试路径下该地址可保留，不保证物理复位/断电或真实 panic 缓存写回均有效。
- 当前 U-Boot dcache/off 命令均返回 Unknown command，未完成关闭缓存对照；文件名 retention-uncached 不代表实际关闭缓存。仍使用 booti，镜像 CRC e4f4809c，六核启动正常。证据：`com5-panic-record-reset-read`、`com5-panic-record-retention-reset`、`com5-panic-record-retention-uncached`、`com5-panic-record-canary-readback`。
- 2026-10-12 会话首个空回车无提示符，后续观察查询未发送；网络超时/由主机 .1 报不可达，未取得板端 TTL 回复。已释放串口并请求复位后先读旧记录，不将 ping 进程退出码当网络通过。证据 `com5-oct12-initial-state`。
- 审计发现 kernel_mem_fault 在 __panic 前 pr_fatal 打印 FAR，若控制台阻塞，panic RAM 记录尚未写入。新增顺序回归约束先失败，再将 FAR 并入 __panic 格式串，三项测试通过；不修改故障容错钩子，不把此诊断盲区认定为失响应根因。新镜像尚待完整构建与上板。
- 顺序修复版完整集成构建成功：109.99 秒、40 警告、无错误；BIN 1818008 字节，SHA256 d5175e1f3edf0e481df068d2e4cfc335878954ca17509eea5df032d0382740f5。尚未加载，需先读取旧镜像 0x023daf80 记录；未提交/推送，冻结仍未闭环。
- 后续已确认 U-Boot，TFTP 前旧记录区仍全 ff，无有效阶段。加载顺序修复版，CRC 2d9425d1、大小匹配；无图形应用，180 秒每 10 秒轮换 IRQ/调度/系统栈查询，无查询超时。结束后先网络收到板端 2ms TTL 回复，再 observe/ps 正常，deadline 188222213375ns，15 线程。此为有诊断负载的三分钟检查，不代表此前几十分钟静默条件通过。
- 证据 `com5-oct12-pending-record-read`、`com5-oct12-fault-order-idle-sampled`、`com5-oct12-fault-order-postcheck`。观察器控制台仍使用 UART 无界 TX 轮询，可能使故障报告失效，尚未归因/修改；串口已释放，未提交推送。
- 同镜像 CRC 2d9425d1 后续基线健康：板端 TTL 回复，observe deadline=1676583213375ns（约 27.9 分钟），SMP owner=next=2681236/count=0/preempt=0。随后十分钟不发命令的静默采集完成；结束后先网络超时/主机 .1 不可达，再串口首个 observe 无提示符，schedstat/ps 未发送，串口释放。
- 该轮无图形应用、观察器占 CPU5，明确不能计为通过；准确失效时刻及最终 PC 未取得。下一步复位后先读 0x023daf80 异常记录，不加载镜像覆盖现场。证据 `com5-oct12-ten-minute-baseline`、`com5-oct12-ten-minute-passive`、`com5-oct12-ten-minute-postcheck`。
- 用户复位后的 `com5-oct12-ten-minute-fault-record` 在 TFTP 前读得全零、CRU glb_rst_st=0，没有有效 panic 阶段，仍不能据此排除异常。新增启动 stage=0 写回标记（不是 panic），回归先失败，补齐后三项通过。
- 启动标记版完整集成构建 130.39 秒成功、40 警告、无错误；BIN SHA256 929a650e530a0d25bbfcf94b63a942541fda64a053716a0a2c362148e89ac4f1，上板 CRC 20ce6bf9，地址仍 0x023daf80。六核启动/14 线程正常，随后显式 shell reboot 捕获 RST。
- 正常 reboot 后 TFTP 前六核记录全部有效：magic=50414e494352414d、CPU 0..5、stage=0、反码全 ff。确认实际 Luna 写回标记可跨该正常重启路径保留；不泛化为故障复位/断电保持，也不是实际 panic 测试。证据 `com5-kernel-record-startup-reboot`、`com5-kernel-record-normal-reboot-read`。未提交推送。
- CRC 20ce6bf9 恢复图形加速复现：观察器 off 后协作完成，仍有完成控制块；Weston PID1、基线18线程。八个 glmark2 PID4..11、800x600 texture、每5秒重建、持续120秒，DRM提交264->7248/读取133->3625；未触发自动停滞或故障标记。
- 八进程 SIGTERM 均记录 exit0、pstate ESRCH，线程恢复18；回收后30秒7次空闲检查仍正常，单轮 ROUND_SYSTEM_PASS。人工画面确认尚未返回，不称像素/拖动通过或长期稳定。资产仍在eMMC，未自动复位。证据 `oct12-eight-texture-120s-system-pass.json`、`oct12-eight-texture-120s.tail.bin`、`com5-oct12-weston-pressure-start`、`com5-oct12-weston-baseline`。
- 用户确认上述八路纹理旋转、拖动、窗口消失均正常。随后按要求启动八个默认全场景 --run-forever（无 -b），PID12..19；源码 next_benchmark 在列表末尾回到首项。没有自动 SIGTERM/复位。
- 全场景初期捕获 js0/js1 gpu sched timeout，status=0/head=tail，观察验收停止，客户端仍继续切换场景、shell响应。后续 pid17 在 bump high-poly 时 uspace page alloc failed：size=0x601000 page894/1537、size=0x621000 page892/1569，std::bad_alloc，exit6，pstate ESRCH。DRM shmem 当时resident/peak384MB；不能仅凭这些数据判定容量/碎片/泄漏根因。
- 此时仅七客户端存活、总线程25，提交15100/读取7552持续增长；不称八路全场景通过、不自动补启动掩盖退出。证据 `com5-oct12-eight-full-suite-start`、`six-client-reclaim-results.json`（observing阶段故障）、`com5-oct12-full-suite-after-timeout`、`com5-oct12-full-suite-running-check`、`com5-full-suite-exited-pid-check`。串口释放，运行客户端未主动停止。
- 用户看到仅一个窗口后，现场 ps 确认仅一 glmark2（tid23），总线程19；不是以进程仍在为据称八窗口渲染。BSP与DTS均限定RAM区间0x02000000..0x40000000，仅992MiB，板卡DDR4GiB不等于全部已纳入页池。逐4KiB页失败不能单纯解释为大块碎片；其余退出原因未完整捕获。
- 新增 ushell memstat 只读复用 k_mm_info_get，取样后打印，无新锁/分配；命令成功/失败/参数边界真实C测试通过。集成164.59秒、40警告、无错误，BIN SHA256 2ae2edf7a1d938ee45cbe6813f564dec0263182531e999e09dd7e80752e6a2ee，上板CRC6a9fb5b3。正常reboot切换，不扩容、不延长GPU超时。
- 实测total1034911744 bytes，初始free1015705600，Weston后free882388992。八路默认全场景PID4..11每5秒轮换memstat/ps，free依次546340864/136314880/147312640/145293312/142917632/132583424，最后场景shading gouraud。随后采样超时，停止发命令；用户确认黑屏，网络超时，未捕获新的OOM/panic/GPU timeout。最后有效空闲约126MiB，不将黑屏直接定为内存耗尽或锁死根因。
- 证据 `com5-full-suite-one-window-state`、`com5-full-suite-memstat-boot`、`com5-full-suite-memory-pressure`；请求复位后TFTP前核对新ELF记录地址再读标记。串口已释放，冻结未闭环。
- 用户复位后，在TFTP前读0x023daf80：前六核记录全ff，连stage0启动标记也无效，CRU状态0。此复位路径未得到有效保留记录，不能凭无panic标记排除异常；证据 `com5-oct12-black-memory-panic-read`。
- 确认 Loader uspace_map_alloc_paged 中途物理页OOM分支未撤销此前用户映射即free_pages；失败区间尚未登记VMA，后续也不能依赖正常VMA回收清除此PTE。真实C函数第三页OOM注入测试失败（已归还页仍被映射），补uspace_rollback_pages(proc,base,i)在free前，连同vm映射/brk契约八项通过。
- 此为确定的OOM回滚隔离缺陷，可能造成释放页再利用后被旧用户映射访问；并未证明所有黑屏均由它触发。物理页池容量与GPU超时尚未改变，待完整构建和复测。测试 `components/loader/tests/test_paged_alloc_failure.py`。
- OOM回滚版完整集成126.82秒成功，BIN SHA256 be149cae15a23b3d6acab08409ada2bd5688f5b5c18febeaa9c3edf91c947998，上板CRC3782a463，八路默认全场景PID4..11，不扩容。约117.76秒pid10/11逐页申请失败/bad_alloc；CPU2 Weston k_malloc(0x3ce8)失败，栈经drm_gem_shmem_get_sg_table/drm_gem_map_dma_buf/dma_buf_map_attachment/PRIME导入。
- 约117.788秒明确panic FAR=fffffffffffffff4，随后输出不完整、ps超时。FAR对应ERR_PTR(-ENOMEM)=-12；源码drm_gem_map_dma_buf未检查get_sg_table错误指针便dma_map_sgtable。真实C注入ERR_PTR(-12)，对象函数与旧driver回调分支测试先失败；补IS_ERR原样返回后与OOM回滚测试两项通过。此证据解释本轮特定错误链，不泛化全部历史冻结。
- 证据 `com5-oom-rollback-fixed-boot`、`com5-oom-rollback-fixed-eight-full-suite`，测试 `components/drm/tests/test_prime_sg_error.py`。panic格式日志已可定位，仍需复位后先读取0x023daf80；新SG修复候选正在重编，尚未上板。
- SG错误指针修复候选集成103.31秒成功、40警告、无错误；BIN SHA256 d14023d014fef70d354072ebca7087c841bd1c37688db70a3d60c01f81c39240，上板CRC6c8e59be。复位后旧RAM标记仍全ff，不将该失效取证途径视作排除panic依据。
- 同1GB配置八路默认全场景PID4..11，约144.6秒SG分配失败、pid10/11 bad_alloc，未再次捕获FAR=-12内核panic。pid10退出6后继续memstat/ps响应，free从约32MiB回升191172608 bytes，场景继续bump/effect2d；最后有效free210182144 bytes、总线程23（六glmark客户端+Weston组+内核）。因此可确认首次低内存后软件继续推进，不称八路全场景通过。
- 随后采样超时，先网络超时再空回车无提示符；最后完整ps仅一linux-work为SUS|SEM，其余工作队列等待，历史状态不是最终锁停点。尾部非文本字节，未取得最终PC/新panic。请求复位，仍有独立失响应路径未闭环；未提交推送。
- 证据 `com5-sg-panic-reset-record`、`com5-prime-error-fixed-boot`、`com5-prime-error-fixed-eight-full-suite`、`com5-prime-error-fixed-postcheck`。
- 同CRC6c8e59be重新启动八路全场景、无专核观察器，每5秒轮换worker栈/SMP/IRQ/内存。三分钟后查询仍正常，pid8在OOM退出，七客户端继续desktop场景；最后一次锁owner=156750059 next=156750062为并发样本，不判定死锁。
- 再采120秒：GPU BO CREATE_BO连续返回ENOMEM（resident383MB/peak386MB），pid6发生用户态SIGSEGV（pc=0x2009bdb64, esr=0x92000006, exit11），pid9 exit6；后续最终仅两客户端（tid19/21），总线程19，free516476928 bytes，DRM commit25506/read12754，shell仍响应。用户确认只剩两个窗口，与现场线程一致。
- 不宣称八路全场景通过或已修复全部失响应；该次已隔离为应用退出而非记录到的宿主panic。容量受限、应用OOM处理和更早失响应仍需独立验证，未调整容量/超时，未自动补启动。证据 `com5-remaining-stall-eight-worker-trace`、`com5-remaining-stall-heavy-scenes`、`com5-heavy-scenes-two-window-state`。
- 用户随后确认失响应/黑屏；独立先网络超时，再串口空回车无提示符，schedstat未发送，串口已释放。前次两客户端/约493MiB空闲时健康不构成长稳通过，晚发故障仍存在，不能将此失响应仅归因容量不足；最终停点和晚发前内存变化未取得。证据 `com5-two-client-late-black-state`。
- 晚发故障源码审计：Runtime普通spin_lock仅原子忙等，preempt_disable/enable仅barrier，irqs_disabled恒0，与Linux非RT抢占禁用/RT睡眠锁及迁移约束均不完整；这是确定语义缺口，不是已证明最终故障锁。Panfrost job_lock在GPU硬IRQ与reset irqsave路径共享，scheduler job_list_lock用于任务路径，须分别定位，不能全部改睡眠锁或关IRQ。
- k_thread_scheduler_lock实际调用ThreadX SMP protect，不能直接当Linux局部preempt_disable替代，否则引入全局调度锁/关IRQ耦合。GPU reset的park/cancel等待可阻塞worker，但在没有中断关闭/公共锁证据时，不足以单独解释串口和网络同时失响应。
- 排除一个未经验证猜测：pm_runtime_put_autosuspend虽调用名带sync的helper，当前实现只是排队autosuspend，callback仅标记is_suspended，未直接调用GPU关时钟驱动；不能据名字认定在job IRQ同步关时钟。下一步需公共锁持有者/等待者与IRQ阶段取证，仍不调整容量或超时。
- 同CRC6c8e59be低并发对照：Weston+两路全场景PID4/5，启用IRQ取证，无专核观察器。用户确认拖动即画面冻结。最后有效free697008128 bytes（约665MiB），无OOM/应用退出；最后完整IRQ时间46433526416ns，CPU0历史irq132 phase2，其他核SGI历史，worker栈均队列/信号量正常等待，DRM commit4790/read2396。
- 随后memstat采样超时停止发命令；独立先网络超时，再空回车无提示符、schedstat未发送，串口释放。两路、内存充足也能全系统失响应，排除八路峰值OOM为必要条件，不判定最后健康栈为最终锁停点。下一轮聚焦输入/重绘期间的共享锁和IRQ阶段，暂不扩容/延长超时。
- 证据 `com5-two-client-control-boot`、`com5-two-client-control-sampled`、`com5-two-client-drag-frozen-check`；未提交推送，仍未闭环。
- 新增默认关闭 spintrace，每核仅记录最近一次Linux自旋锁等待/获取/释放、锁地址、线程指针、返回地址和时间；不改变自旋锁布局、IRQ状态或原子操作，不增加锁/分配/打印。不是完整持锁栈，IRQ/嵌套/迁移可覆盖，禁止把phase0当作全系统无持锁证明。真实C包装顺序测试先失败后通过；关闭时仍有函数调用开销，诊断镜像非性能验收。
- 集成135.46秒、40警告、无错误；BIN SHA256 fd1d0db607ee8eafb29f72aaf3cf2965e4bb1fcfa99c0d6c1099c10c4c5fb406，上板CRCecf4b335。两路全场景PID4/5，开启spintrace每2秒交替查询/drmdiag。用户确认冻结，采样超时停止发命令；最后完整锁快照now45979982583ns各核phase0，没有取得稳定等待同锁证据，不能据此改锁或排除下一瞬间故障。
- 证据 `com5-spintrace-two-client-boot`、`com5-spintrace-two-client-drag`；DRM commit3465/read1733仍推进于失响应之前，不是最终停点。测试 `components/linux-runtime/tests/test_spin_trace.py`。未提交推送。
- 同CRCecf4b335仅Weston对照120秒：17线程，input事件0->7070且events_read7070，DRM commit109->2380，约841MiB空闲，查询响应；用户确认鼠标/点击均正常。events_dropped统计同时覆盖未读取的诊断环与客户环，不把6815直接判定Weston丢输入（读取计数等于事件计数）。
- 同启动只增加一glmark2（PID4）全场景，90秒交替inputstat/spintrace/drmevents查询无超时；用户确认旋转/拖动均正常。结束后18线程，free762560512 bytes，DRM commit16477/read8242，单客户端仍运行。仅该短观察窗口通过，未全场景完成或长稳验收。
- Weston报告unknown libinput event404；本地libinput头定义为新滚轮事件，随旧POINTER_AXIS事件同时发送，Weston9只处理旧事件。确定事件版本适配缺口，但不以该警告直接解释全系统冻结；暂未修改用户态资产。下一步优先多客户端并发提交/输入重绘交互，未自动复位/停止单客户端。
- 证据 `com5-weston-only-input-boot`、`com5-weston-only-input-observation`、`com5-weston-only-input-postcheck`、`com5-one-client-input-lock-control`、`com5-single-client-control-postcheck`；串口已释放，未提交推送。
- 后续单客户端基线uptime393s仍健康，free757456896 bytes；同启动新增第二实例PID5。40秒计划无输入对照中input events18393->22832且后续26482，不算严格无输入。两客户端/19线程、free566538240，显示提交持续推进。
- 随后90秒拖动取证input/spintrace/IRQ/drmdiag查询均响应；用户确认两窗口旋转/拖动正常。结束后19线程、free580706304、SMP owner=next349932457 count0 preempt0。两个实例仍持续循环，没有强制退出或自动复位。
- 此次是错开数分钟启动而非近同时启动，启动时间/场景重叠是待控制变量，不能从单轮推断并发初始化为根因或长期通过。证据 `com5-single-client-before-second`、`com5-second-client-no-input-control`、`com5-second-client-control-postcheck`、`com5-two-client-live-drag-followup`、`com5-staggered-two-client-final-state`。串口释放。
- 用户要求再增加两路：基线两客户端仍存活/19线程，free519639040 bytes，但刚捕获js0 gpu sched timeout（status0/head=tail），不是无错误基线。新增PID6/7启动确认；Weston同时报告computed repaint delay -27356msec、vop vblank enable，尾部到jellyfish场景后非文本字节。
- 用户确认先卡滞再黑屏；首个memstat采样超时停止发命令，网络超时，独立空回车无提示符，COM5释放。没有捕获本轮OOM/panic或最终锁点。负重绘延迟可能源于旧呈现时间/停顿，不能直接认定计时器跳变；需核对实际板端Weston对应源码，当前本地告警原字符串搜索未命中，不假定完全匹配。
- 证据 `com5-four-client-expansion-baseline`、`com5-four-full-suite-expansion`、`com5-four-client-black-postcheck`；未提交推送，四路全场景失败。
- 核对Weston compositor.c实际告警（跨两字符串拼接）：next_repaint=stamp+refresh-repaint_msec，再与presentation clock now相减；超限则next_repaint重置now。-27356ms说明呈现时间落后约27s，不单独证明系统时钟跳变，不能仅靠更改16ms门限规避。
- 同CRCecf4b335重新启动两路全场景--off-screen PID4/5。源码离屏为FBO、默认glFinish、不走每帧swap/native flip，仍初始化Wayland/EGL。120秒交替锁/DRM/输入/内存查询均响应，用户确认鼠标/桌面正常；19线程，free626782208 bytes，input4956/events_read4956，DRM commit1792/read898，GPU场景持续FPS输出（bump等）。未自动停止实例。
- 该短窗口支持优先检查呈现/PRIME与异步任务深度，但glFinish同步策略也变化，不能直接将VOP认定根因，未全场景长稳通过。证据 `com5-offscreen-control-boot`、`com5-offscreen-two-client-control`、`com5-offscreen-two-client-final-state`；串口释放。
- 用户随后报告黑屏；先网络超时，再COM5空回车无提示符，ps/spintrace未发送，串口释放。离屏双实例亦晚发整机失响应，撤回任何将故障仅缩到窗口呈现/PRIME的推断；Weston/输入/显示内核仍存在，离屏不是完全移除VOP对照，也不能独立排除它。最后约598MiB空闲仅是此前健康快照，最终内存/PC未知。证据 `com5-offscreen-late-black-state`，故障未闭环。
- 审计ThreadX全局SMP保护：现有下溢分支会把preempt计数清零再释放锁，此前未记录命中。新增仅异常分支记录原值/CPU/解锁返回地址/累计次数，无C调用/打印，不增加原函数已用寄存器之外的破坏，原清零/释放逻辑保持。汇编约束测试先失败后通过，连同SG和OOM两项执行测试共三项通过；不是行为修复，最终ELF反汇编核对。
- 集成132.27秒、40警告、无错误；BIN SHA256 0295f2ce79fc642b6ea9cfebf461ed8070880b06b19d0effb6f9771f221a0ff2，上板CRCe1a93368。两路全场景PID4/5，120秒每3秒交替schedstat/drmdiag持续响应，尚未捕获下溢/固定ioctl停点；人工画面确认待返回，不称长稳通过。证据 `com5-native-underflow-trace-boot`、`com5-native-underflow-two-client-pressure`、`com5-native-underflow-pressure-final-state`，实例未主动停止，串口释放。
- 用户先报告仍正常、随后报告冻结。独立先网络超时，再串口空回车无提示符，后续schedstat/drmdiag/spintrace未发送，尾部为空。最后健康文件11:51:00，冻结复查11:58:29，此约7分29秒是证据文件间隔，不是准确故障发生时刻；此前underflows0不能充当冻结时计数。
- 最终ELF debug_check_pending为W空弱实现，Ctrl-G不能获取各核PC；无实时调试入口时不虚构持锁者现场。正常shell reboot已验证RAM标记保留，但健康状态物理复位尚未验证，应先做该对照再依赖故障后RAM读取。当前记录地址0x023dbf80，下溢count0x023fd998/value0x023fd994/cpu0x023fd990/pc0x023fd988。
- 证据 `com5-native-underflow-live-freeze`；COM5已释放，未自动复位，未提交推送，剩余失响应未闭环。
- 健康物理复位对照：同CRCe1a93368启动后14线程/underflows0，用户仅按物理复位键；TFTP前启动记录和计数记录均全ff，与故障后相同。因此物理复位路径不提供可靠DDR记录保留，不能用故障后无标记排除panic/下溢或认定RAM故障。证据 `com5-healthy-physical-reset-control-start`、`com5-healthy-physical-reset-retention-read`。
- 新增显式开启的SMP长等待探针：原生获取慢路径每4096次轮询保存x0..x18/x30后调用无锁/无分配C探针，50ms同票据等待由Luna原子CAS选一核直接输出一次，不解锁/复位；UART仅有界轮询，不承诺总线故障仍可输出。判定/汇编保存约束与UART真实C测试通过，原子CAS实现和最终ELF调用核对未取调度/日志锁。
- 首版集成130.04秒、40警告、无错误；BIN SHA256 3c87dcc20a3f1cd4cb7335380bccc6b14c6cab640f6d3b41bbf5d99878be29fb，上板CRC07116233，两路全场景PID4/5。用户确认疯狂拖动后卡死，现场直出：cpu3 ticket31920263 caller0x22033a0 wait_ns50005958 owner31920261 next31920264 core0 count0 preempt1。等待者调用点解析为_ke_timer_create:120，不是CPU0持锁者调用点；这证明当时CPU0留锁暂缓状态使其他核等待至少50ms，未据单报告声称已知最终CPU0 PC。
- 增强首留锁点：同一票据第一次count归0但preempt非0时保存解锁返回地址和current_thread指针，后续IRQ重入不覆盖；原有计数/IRQ/释放行为不变。约束先失败后通过，五项测试通过。集成134.38秒、40警告、无错误，BIN SHA256 54180c4eb278cacfcdd645a38bfaf561bb7261c9a25c7d6c914efe622311f726，已更新TFTP，尚未上板，等待物理复位。
- 证据 `com5-direct-smp-wait-probe-boot`、`com5-direct-smp-wait-two-client-repro`；测试 `threadx/tests/test_smp_wait_probe.py`、`threadx/tests/test_preempt_underflow_trace.py`、`rockchip/tests/test_emergency_uart.py`。仍未修复全部冻结，未提交推送。
- 首留锁点版CRC bab50f75上板，两路全场景PID4/5，用户拖动后冻结。现场：cpu1 ticket64473346 wait_ns50006250 owner64473345 next64473350 core0 count0 preempt1 hold_ticket64473345 hold_pc0x2219c94 hold_thread0x2fd5400。hold_ticket与owner匹配，holder返回点解析为_k_mutex_put:252；waiter为_k_thread_system_preempt_check:70。
- native mutex_put该段在PI优先级恢复扫描前preempt++/TX_RESTORE，然后遍历thread_owned_mutex_list。现场符合该段，但尚未区分IRQ打断停滞或链表异常循环。未禁用PI、未强制解锁。
- 增加票据匹配/页池范围检查后的只读owner快照（线程状态、IRQ嵌套、owned_count/head，最多4个mutex节点的ID/owner/next/prev），不加锁/分配、不修改链表。范围判定真实C执行测试和有界快照约束通过；不是完全停机快照，也不保证页表已损坏时读取无故障，首行报告在对象读取前输出。
- 新版集成123.58秒、40警告、无错误；BIN SHA256 f72419d933e7c80659119304d5bf497a647f9fc67f0f6971f216e3c3d44330c0，已更新TFTP，尚未上板。证据 `com5-holdoff-owner-probe-boot`、`com5-holdoff-owner-two-client-repro`；未提交推送。
