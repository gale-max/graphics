# glmark2 图形回归工程

本工程使用 Catboy 构建 glmark2 的 EGL、GLES2 和 GBM 组合，用于验证 Luna
Panfrost 驱动的持续渲染、缓冲交换和显示稳定性。构建源清单与 upstream Meson
的 `gbm-glesv2` flavor 对齐，不引入 Android、X11、Wayland、Win32、DispmanX
或 udev 实现。

## 依赖

- `graphics/libdrm` 已构建 `libdrm`；
- `graphics/mesa` 已构建 Panfrost 的 `libgbm.so`、`libEGL.so` 和
  `libGLESv2.so`；
- zlib、libpng 和 libjpeg-turbo 直接使用 glmark2 upstream 内置源码构建。

## 构建

```powershell
cd D:\workspace\luna-workspace\os\graphics\glmark2
D:\workspace\luna-workspace\catboy\catboy.exe build glmark2-drm -f build.yaml -p armv8a-user
```

输出为 `build/glmark2-drm/armv8a-user/glmark2-drm.elf`。

## 部署和运行

将 ELF、同一构建批次的 Mesa 动态库和 upstream 的完整 `data` 目录部署到
`/media/mmcblk0p1/graphics`。不得混用不同构建批次的 `libEGL`、`libgbm`、
`dri_gbm.so` 和 `libgallium`，否则 Mesa 内部结构 ABI 不一致会在
`dri2_setup_screen()` 阶段崩溃。默认数据目录已编译为
`/media/mmcblk0p1/graphics/data`，也可以通过参数覆盖：

```text
load /media/mmcblk0p1/graphics/glmark2-drm.elf \
    --benchmark build:duration=2.0 \
    --data-path /media/mmcblk0p1/graphics/data
```

去掉 `--benchmark` 参数即可执行完整回归。

Mesa 25 将 GBM DRI 后端拆分为独立的 `dri_gbm.so`。运行前必须将其
与其他 Mesa 动态库一起部署，并通过标准环境变量指定搜索目录：

```text
setenv GBM_BACKENDS_PATH=/media/mmcblk0p1/graphics
```

当前 Mesa 同时启用 DRM 与 Wayland，DRM 直出程序也依赖 Wayland 运行库。
NanoPC-T4 上使用下列完整搜索路径：

```text
setenv LD_LIBRARY_PATH /media/mmcblk1p1/qt5/lib:/media/mmcblk1p1/graphics:/media/mmcblk0p1/graphics
setenv LIBGL_DRIVERS_PATH /media/mmcblk1p1/graphics/dri
setenv GBM_BACKENDS_PATH /media/mmcblk1p1/graphics
setenv GBM_BACKEND dri
```

## 构建契约检查

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

检查项覆盖平台源隔离、内置图片库、GBM/GLES2 源组合和 SD 卡数据路径。
