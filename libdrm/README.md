# libdrm

本目录固定 Luna 用户态使用的 libdrm 源码、兼容头和 Catboy 构建配置。

```powershell
D:\workspace\luna-workspace\catboy\catboy.exe build -f build.yaml -p armv8a-user libdrm
D:\workspace\luna-workspace\catboy\catboy.exe build -f build.yaml -p armv8a-user modetest
```

Luna discovery uses `fstat`/`stat` and Linux-compatible `st_rdev` (DRM major
226, primary minors 0–63, render minors 128–191). Driver names do not determine
node type. The fd-name APIs return the verified node's actual path, including
nonzero minor indices; absent or replaced paths are rejected.

Luna currently has no userspace query for a node's parent DRM device identity.
Primary and render minors are allocated independently, so neither a minor
offset nor equal driver names establishes that two nodes belong together.
Device descriptions and enumeration therefore expose individual verified
nodes, identified by `/luna/drm/<major>:<minor>`, and do not claim physical
device grouping. Cross-type fd-name queries fail with `ENOTSUP`; querying a
render fd for its own render path works. Rockchip and Panfrost are not merged
into an invented device. Consumers needing a render device must enumerate
render nodes; exact primary/render association requires an additional kernel
identity interface. Enumeration counts describe nodes until that exists.

`tests/luna_discovery.c` is a target-side probe without Mesa/GL dependencies.
It checks discovery for the paths passed as arguments, or all enumerated nodes
when no paths are supplied. Host regression tests compile the actual vendored
libdrm and replace only device syscalls; see
`../tests/test_libdrm_luna_discovery.py`.

The upstream pin in `sources.yaml` is unchanged. Luna adaptations live in the
`LUNA_GRAPHICS` branches of `upstream/xf86drm.c` and the compatibility header;
the non-Luna discovery paths remain upstream implementations.
