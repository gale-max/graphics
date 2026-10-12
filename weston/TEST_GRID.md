# 八窗口观察模式

在 Weston 配置的 `[shell]` 中设置 `test-glmark-grid=true`，只对
`com.github.glmark2.glmark2` 的新窗口启用 4 列 2 行初始布局。
默认关闭，不改变其他客户端的初始位置。

客户端仍使用 `--size 800x600`。合成器对完整窗口等比缩放后居中放入
工作区网格，保留标题栏拖动；不通过调整客户端大小降低渲染负载。
每轮须先回收旧客户端，随后启动八个新客户端。该模式用于观察，不是
与未缩放合成路径完全等同的性能测量，也不替代长期稳定性验收。

构建仍使用本目录固化的 Windows Catboy 工程。布局计算用独立 C 测试
检查八格不重叠、缩放边界和无效工作区；匹配与配置入口检查默认关闭。
上板需人工确认八窗口可见、模型旋转及拖动坐标正确。

独立副本可设置 `LUNA_GRAPHICS_TOOLCHAIN` 为交叉工具链的 `bin` 目录，
无需把工具链复制到副本。设置后运行本目录 Catboy 的 `weston-desktop`
目标。部署 `desktop-shell.so` 与 `weston-grid.ini`，启动 Weston 时使用
`--config=/graphics/weston/weston-grid.ini`。配置仅影响合成器，不修改
客户端的 `--size 800x600` 参数。
