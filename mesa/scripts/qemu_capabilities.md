# Mesa 25.2.8 QEMU profile and virtgpu bridge requirements

This is a source-derived integration contract, not a guest acceptance result.
The profile builds `virgl,softpipe`, with LLVM, Vulkan, GLX and shader cache
disabled. Panfrost remains the default profile and its output is separate.
`softpipe` is the actual 25.2.8 Gallium option; `swrast` is an internal aggregate.
The guest VirGL driver does not link host virglrenderer: QEMU supplies that side.
The checked source requires Meson >= 1.4.0, Python >= 3.8 and Mako >= 0.8.0;
this build script's type syntax requires Python >= 3.10. This profile's libdrm
minimum is 2.4.109, satisfied by the existing 2.4.113 metadata. LLVM/CLC host
compilers are not needed for virgl/softpipe (`mesa-clc` and `precomp-compiler`
are auto, with no enabled driver requiring CL). Existing generated target
lexers and Wayland materials are still used with the configured host tools.

## Build and deploy boundary

From the workspace root:

```powershell
python -B graphics/mesa/scripts/build_windows.py --profile qemu --output-root D:/workspace/codex-workspace/rt-full-regression-20261114/gpu/mesa --jobs 4
```

The opt-in `mesa-qemu` recipe uses `LUNA_MESA_QEMU_OUTPUT` instead of an implicit
output directory. The script refuses output within the graphics repository or
Qt SDK, and requires its own ownership marker before reusing managed children.
The default `mesa-panfrost` recipe, output paths and runtime paths are unchanged.
Generated target lexers and Wayland protocol materials are reused. Cross-file,
pkg-config metadata, caches, temporary files, build outputs and runtime copies
belong to the external output root. Only existing libdrm/Qt SDK dependencies are
consumed; this entry does not build other projects.

Runtime libraries: libgbm, libEGL, libGLESv2, libgallium-25.2.8, dri_gbm.
The source tree's `src/meson.build` enables `targets/dril` only for GLX/X11/XCB.
With this profile's GLX disabled, GBM/EGL link libgallium directly. Do not invent
`virtio_gpu_dri.so` or `swrast_dri.so` aliases pointing to the wrong ABI.
`libraries.json` records each exported library's SHA-256, SONAME and DT_NEEDED;
SDK/toolchain runtime dependencies are not overwritten by packaging.
Build-machine RPATH/RUNPATH entries are removed from exported copies using
Meson's ELF installer helper; original build libraries are preserved.

Example guest deployment into the profile's default runtime prefix:

```sh
export LD_LIBRARY_PATH=/opt/luna/qemu-graphics
export GBM_BACKENDS_PATH=/opt/luna/qemu-graphics
```

Include the guest's existing SDK/runtime dependency directories as necessary.
For a controlled software run with `luna_virtio2d`:

```sh
export GBM_ALWAYS_SOFTWARE=1
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=softpipe
```

For genuine VirGL acceptance, unset those three overrides, use the actual
`virtio_gpu` 3D DRM implementation, record GL_VENDOR/GL_RENDERER/GL_VERSION and
the loaded library hashes, and correlate with successful resource/command/fence
activity. GBM can automatically fall back to software; a visible frame or a
passing glmark2 scene alone does not prove GPU acceleration. QEMU GL backend
startup is host availability evidence only. `luna_virtio2d` remains 2D KMS.

## Minimum classic VirGL path

Source: `mesa/upstream/src/gallium/winsys/virgl/drm/virgl_drm_winsys.c`
and its `.h`, `mesa/upstream/include/drm-uapi/virtgpu_drm.h`.
The ioctl suffixes below are offsets from DRM_COMMAND_BASE, not complete
architecture-independent ioctl request values: use the actual UAPI macros.

**Versioned ioctl sizes matter:** this Mesa header's EXECBUFFER structure is
64 bytes (ring/syncobj fields included), while the local Linux 5.10 header has
the 32-byte legacy structure. Mesa's classic VirGL submit zero-initializes the
extended fields. Preserve DRM core's dispatch by ioctl type/number and its
user-size/driver-size copy/zero-fill compatibility; exact comparison against a
legacy full encoded ioctl request will incorrectly reject modern userspace.
Do not advertise newer ring/syncobj semantics solely because the larger request
can be accepted. The reference implementation is Linux 5.10 `drm_ioctl.c`.

| Interface | Required behavior / dependency |
|---|---|
| DRM core VERSION, device discovery, GET_CAP | Driver name `virtio_gpu`; version major 0. Truthful dumb/PRIME/fence capabilities. Working per-file GEM handles and lifetime. |
| GETPARAM (0x03) | Mesa probes 3D_FEATURES, CAPSET_QUERY_FIX, RESOURCE_BLOB, HOST_VISIBLE, CROSS_DEVICE, CONTEXT_INIT, SUPPORTED_CAPSET_IDs. 3D_FEATURES must be nonzero only for a working negotiated 3D transport. Unsupported parameters may fail and Mesa treats them as zero. |
| GET_CAPS (0x09) | Query real host capsets. Without CAPSET_QUERY_FIX, request virgl capset 1. With it, request capset 2, and fall back to 1 on EINVAL. Preserve size/version and user-copy semantics; do not fabricate capset payloads. |
| RESOURCE_CREATE (0x04) | Create the host 3D resource with target, format, bind, dimensions, mip levels, samples, backing size/stride. Return distinct valid GEM bo_handle and host res_handle. Keep backing pinned through host use. |
| RESOURCE_INFO (0x05) | Return resource information for imported/existing handles. Required by handle sharing/import paths. |
| MAP (0x01) plus mmap/munmap | Return an mmap offset associated with the GEM object and validate mapping size/protection. Keep object ownership through mapping and close. |
| TRANSFER_TO_HOST (0x07), TRANSFER_FROM_HOST (0x06) | Correct resource, level, box, offset and applicable stride semantics; coherent CPU/host ownership and completion. |
| EXECBUFFER (0x02) | Consume the actual virgl command stream, validate/copy user pointers and buffer-handle arrays, associate per-file context/resources, submit to host, and honor requested fences. Successful return alone is not host completion. |
| WAIT (0x08) | Wait for the resource's actual GPU work. NOWAIT returns EBUSY while pending. Required for cache reuse, CPU access and the legacy fence path. |
| GEM_CLOSE | Release per-file GEM ownership safely after outstanding GPU work and maps; translate eventual resource detach/unref in the proper order. |
| PRIME fd/handle, GEM_FLINK/OPEN | Required when advertising and using DMA-BUF/shared-name paths, especially Wayland/compositor interop. Not a substitute for basic resource ownership. |

`pipe_loader_drm.c` may query the DRM-native-context capset before the VirGL
screen is created; returning the correct unsupported-capset error must leave
the ordinary VirGL path usable. Unknown queries must not reset the device.

The transport also needs negotiated VIRTIO_GPU_F_VIRGL, GET_CAPSET_INFO/
GET_CAPSET, CTX_CREATE/DESTROY, context-resource attachment, RESOURCE_CREATE_3D,
3D transfers, SUBMIT_3D and fenced completions. The native 2D helper's synchronous
presentation API is not an implementation of that DRM contract. Reusing the
matching upstream virtgpu driver with a Linux virtio/SG/DMA shim avoids rewriting
GEM/context/execbuffer ABI semantics. Only one driver may own a device's queues.

## Capability-gated extensions

* **Fence fd is version-gated:** `VIRGL_DRM_VERSION_FENCE_FD` is version 0.1.
  Reporting major 0, minor >= 1 makes Mesa use EXECBUF_FENCE_FD_IN/OUT, sync-file
  poll/wait, fd duplication/close and sync merge for external fences. Provide
  those semantics; do not advertise 0.1 with dummy or already-signaled fences.
  The legacy 0.0 path uses real resource WAIT and a small fence resource.
* **CONTEXT_INIT:** only advertise with real implementation. Mesa then requires
  a supported-capset bit for VIRGL or VIRGL2, selects VIRGL2 preferentially and
  calls CONTEXT_INIT with CAPSET_ID. EEXIST is tolerated for an already-created
  context (e.g. a compositor previously creating a dumb buffer).
* **RESOURCE_BLOB / HOST_VISIBLE:** optional for the classic path. Coherent /
  persistent map support needs both truthful flags, correct blob creation and
  host-visible mappings. Leave these capabilities absent until implemented.
* **Cross-device / PRIME / explicit synchronization:** advertise only the subset
  actually supported by the kernel bridge, virtual device and host renderer.

For 2D softpipe KMS, the separate minimum includes CREATE_DUMB, MAP_DUMB,
DESTROY_DUMB, mmap and ordinary connector/CRTC/framebuffer/present ioctls.
`kms_dri_sw_winsys.c` directly uses that path. A software rendering pass is a
useful independent control and must be reported separately from VirGL 3D.

Upstream references: https://docs.mesa3d.org/drivers/virgl.html and the pinned
25.2.8 source in this repository. Build options and behavior above were checked
against the local source, rather than inferred from current generic docs.
