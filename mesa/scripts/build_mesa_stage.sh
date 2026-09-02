#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${root_dir}/build/mesa-22.3.7"

if [[ $# -eq 0 ]]; then
    printf '%s\n' "usage: $0 <meson-target> [...]" >&2
    exit 2
fi

cd "${root_dir}"
if [[ ! -f "${build_dir}/meson-private/coredata.dat" ]]; then
    bash scripts/configure_mesa.sh
fi
ninja -C "${build_dir}" -j "${LUNA_BUILD_JOBS:-8}" "$@"
