# Graphics build-entry audit (2026-10-20)

Scope: this graphics checkout only. No Mesa/Qt full build, board access,
deployment, commit or push was performed. Existing glibc migration notes were
not changed. Paths and configuration tests are not binary/runtime acceptance.

## Configuration

Run the following in this checkout's graphics directory (PowerShell):

```powershell
Set-Location D:/workspace/codex-workspace/luna-graphics-20261008/os/graphics
$env:LUNA_GRAPHICS_SDK = 'D:/workspace/luna-workspace/os/luna-sdk/qt5-5.15.19/staging'
$env:LUNA_GRAPHICS_TOOLCHAIN = 'D:/workspace/luna-workspace/tools/toolchains/aarch64-none-linux-gnu/bin'
$catboy = 'D:/workspace/luna-workspace/catboy/catboy.exe'
```

The staging directory, Wayland library files and GNU/Linux compiler exist.
The deleted drive-root SDK is not a fallback. Defaults follow the checkout:
`<checkout>/os/luna-sdk/qt5-5.15.19/staging` and
`<checkout>/tools/toolchains/aarch64-none-linux-gnu/bin`.
This isolated checkout needs explicit overrides because it has no SDK/tools copy.
Compiler prefix remains `aarch64-none-linux-gnu`; `-mtune=cortex-a53` is CPU
tuning, not a bare-metal compiler selection. No CortexA/none-elf compiler
selection was found in the maintained entry files. Do not use a Catboy found
implicitly in PATH; this machine has another installation there.

## Entry Inventory

Commands below are reproduction entry points, NOT a claim that a clean complete
build passed. Execute in dependency order, never concurrently with dependency
clean/rebuild operations. Add `--dry-run` to each build_component command for
configuration-only checks. It writes ignored component/build.local.yaml;
source paths and build outputs stay component-relative. Direct Catboy YAML
uses checkout-relative defaults; environment overrides require the wrapper.

| Products | Entry from graphics directory | Inputs / boundary |
| --- | --- | --- |
| libdrm.a, modetest.elf | `python scripts/build_component.py libdrm libdrm modetest --catboy $catboy` | GNU/Linux compiler; Catboy source build |
| libgbm, libEGL, libGLESv2, libgallium/Panfrost, dri_gbm | `python mesa/scripts/build_windows.py` | libdrm, SDK Wayland/libffi pkg-config, Meson/Ninja/pkgconf, pinned generated materials |
| libglapi.a, libexpat | Mesa dependency products | Required by kmscube/glmark2 and packaging, not separate public build targets |
| kmscube.elf | `python scripts/build_component.py kmscube kmscube --catboy $catboy` | Local libdrm/Mesa outputs |
| glmark2-drm.elf, glmark2-wayland.elf; bundled png/jpeg/zlib | `python scripts/build_component.py glmark2 glmark2-drm glmark2-wayland --catboy $catboy` | Local libdrm/Mesa outputs, SDK Wayland |
| Weston compositor, desktop-shell, keyboard, DRM backend, GL renderer, private libraries and data | `Push-Location weston; & $catboy build -f build.yaml -p armv8a-user weston-desktop; Pop-Location` | Fixed generated materials, SDK public libraries, prepared weston/stage dependency closure; output/ tree |
| QtCore/Gui/Widgets, EGLFS/KMS, smoke and widgets examples | In Linux Qt source checkout: `python3 scripts/qt5_build.py --stage configure`, then stages `core`, `gui-eglfs`, `kms`, `widgets`, `smoke`, `widgets-display` | LUNA_QT_TOOLCHAIN, LUNA_QT_REFERENCE_SYSROOT/LUNA_QT_SYSROOT are separate Linux contracts; script rejects Windows builds |
| Windows qmake/moc/uic/rcc/QML/translation tools | `python qt5/sdk-recovery/scripts/build_windows_host_tools.py` | BLOCKED: missing sdk_paths module; no full rebuild claim |
| Windows SDK composition | `python qt5/sdk-recovery/scripts/package_windows_sdk.py --sdk <new-sdk> --target <target-install> --host-tools <host-bin> --host-mkspecs <host-mkspecs> --toolchain <bin> --sysroot <matching-sysroot>` | Requires complete target Qt install and host tools; default SDK honors LUNA_GRAPHICS_SDK parent. Use a NEW destination, not the shared active SDK |
| Window examples from installed SDK | `python qt5/scripts/build_window_examples.py --make <make.exe>` | SDK defaults to LUNA_GRAPHICS_SDK parent; --sdk overrides it |
| All SDK-delivered examples | `python qt5/sdk-recovery/scripts/build_sdk_examples.py --sdk <sdk> --output <new-build> --jobs 4` | Requires mingw32-make in PATH; no example builds in this audit |
| Base DRM artifact tree + hash manifest | `python scripts/package_artifacts.py` | Collects existing base outputs only; not a source build and not full Weston/Qt/Wayland delivery |
| Qt runtime tree | `python qt5/scripts/package_runtime.py --qt-root <qt-install> --graphics-root <staging> --runtime-root <matching-rootfs> --output <new-runtime>` | Copies libraries/loader from explicit roots; must preserve matching libc/loader ABI |
| Relocatable installed SDK copy | `python qt5/scripts/export_sdk_copy.py --source <sdk> --toolchain <toolchain-root> --graphics <graphics-root> --output <new-copy>` | Export of existing installed inputs, not a source rebuild |

glmark2 data, Weston share data, Qt plugins/fonts/QML and matching Wayland/rootfs
libraries are part of deployment, not replaceable by the executable list.
`package_board_assets.py` and deployment scripts contact a target: NOT run here.

## Regression Evidence and Gaps

- Initial regression run: 16 failed, 2 passed (deleted paths and ignored overrides).
- Added compiler-cache regression failed before implementation. Mesa now wipes
  only its bounded build directory when generated cross configuration changes;
  unchanged configurations use reconfigure. This prevents cached old compilers.
- SDK packager --help and source-root regressions failed first, then passed.
- New tests cover defaults, explicit overrides, cross configuration with spaces,
  Catboy configuration, cache invalidation and deleted-path/bare-metal guards.
- Final focused suite: 23 passed. Combined suite: 124 passed, 1 existing
  root-layout failure. GNU compiler -dumpmachine reports aarch64-none-linux-gnu;
  all six required SDK pkg-config files exist. PowerShell Kit script parses
  with zero errors; git diff --check passes.
- libdrm/modetest, kmscube, both glmark2 targets passed Catboy dry-run.
- The existing root-layout test is stale: its HEAD allowlist excludes pre-existing
  weston, RELEASE.md, output and .qmake.stash. It was not changed by this audit.
- Qt Quick/Wayland target libraries are required by SDK composition, but the
  base qt5_build.py stage set does not reproduce the complete delivered module
  set. SDK source archives, generators and host tools need an independent clean
  reconstruction exercise. Windows host-tools sdk_paths is missing here.
- Weston stage dependencies and SDK Wayland/libffi are pre-existing inputs.
  Their directory presence is not proof of complete, ABI-matched reproducibility.
- Historical SDK/validation documents still contain obsolete drive-root example
  paths. They were not bulk-rewritten; use the explicit configuration above.
- No final linking, artifact hash renewal, clean-machine reproduction, runtime
  loader compatibility or visual/board acceptance was performed in this audit.

Regression command (temporary outputs stay under this graphics checkout):

```powershell
New-Item -ItemType Directory -Force tests/.tmp | Out-Null
python -m pytest tests qt5/tests glmark2/tests weston/tests --import-mode=importlib -q --basetemp=tests/.tmp/audit
```
