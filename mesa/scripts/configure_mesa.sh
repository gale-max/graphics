#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${root_dir}/build/mesa-22.3.7"
setup_mode=()
if [[ -f "${build_dir}/meson-private/coredata.dat" ]]; then
    setup_mode=(--reconfigure)
fi

meson setup "${setup_mode[@]}" "${build_dir}" "${root_dir}/upstream/mesa" \
    --cross-file "${root_dir}/toolchains/luna-armv8a.ini" \
    -Dplatforms= -Degl-native-platform=drm \
    -Dgallium-drivers=panfrost -Dvulkan-drivers= -Ddri-drivers= \
    -Degl=enabled -Dgbm=enabled -Dgles1=disabled -Dgles2=enabled \
    -Dopengl=true -Dglx=disabled -Dglvnd=false -Dshared-glapi=enabled \
    -Dllvm=disabled -Ddraw-use-llvm=false -Dshader-cache=disabled \
    -Dbuild-tests=false -Dgallium-vdpau=disabled -Dgallium-va=disabled \
    -Dgallium-xa=disabled -Dgallium-nine=false \
    -Dgallium-opencl=disabled -Dgallium-rusticl=false \
    -Dgallium-omx=disabled -Dosmesa=false -Dvalgrind=disabled \
    -Dlibunwind=disabled -Dlmsensors=disabled -Dzstd=disabled \
    -Dzlib=disabled -Dtools= -Dvideo-codecs= -Dselinux=false \
    -Dperfetto=false -Dbuildtype=release -Db_ndebug=true
