#ifndef LUNA_GLMARK_CONFIG_H
#define LUNA_GLMARK_CONFIG_H

#define GLMARK_VERSION "2023.01-luna"
#if defined(GLMARK2_USE_WAYLAND)
#define GLMARK2_EXECUTABLE "glmark2-wayland.elf"
#else
#define GLMARK2_EXECUTABLE "glmark2-drm.elf"
#endif
#define GLMARK_DATA_PATH "/media/mmcblk1p1/graphics/data"

#endif
