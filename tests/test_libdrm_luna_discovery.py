"""Execute the vendored libdrm, replacing only the host device syscalls."""

from pathlib import Path
import os
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    "virtio_primary", "virtio_render", "panfrost_primary", "nonzero_minor",
    "invalid_fd", "regular_file", "wrong_major", "control_minor",
    "missing_path", "replaced_path", "names", "peer_not_guessed",
    "from_devid", "invalid_args", "enumeration", "empty", "independent_nodes",
]


def linux_path(path):
    path = Path(path).resolve()
    if os.name == "nt":
        return "/mnt/" + path.drive[0].lower() + path.as_posix()[2:]
    return str(path)


def run_linux(args):
    prefix = ["wsl", "-d", "ubuntu20.04", "--"] if sys.platform == "win32" else []
    return subprocess.run(prefix + args, text=True, encoding="utf-8",
                          errors="replace", capture_output=True, timeout=120)


@pytest.fixture(scope="module")
def discovery_binary(tmp_path_factory):
    out = tmp_path_factory.mktemp("libdrm-discovery") / "discovery"
    lib = ROOT / "libdrm"
    args = ["gcc", "-std=gnu11", "-g", "-O1", "-ffunction-sections",
            "-fdata-sections", "-DLUNA_GRAPHICS=1", "-DMAJOR_IN_SYSMACROS=1"]
    for directory in [lib / "include", lib / "upstream", lib / "upstream/include/drm"]:
        args += ["-I" + linux_path(directory)]
    args += [linux_path(ROOT / "tests/libdrm_luna_discovery_harness.c")]
    args += [linux_path(lib / "upstream" / name) for name in
             ["xf86drm.c", "xf86drmHash.c", "xf86drmRandom.c", "xf86drmSL.c", "xf86drmMode.c"]]
    args += ["-Wl,--gc-sections", "-Wl,--wrap=fstat", "-Wl,--wrap=stat",
             "-Wl,--wrap=ioctl", "-o", linux_path(out)]
    result = run_linux(args)
    assert result.returncode == 0, result.stdout + result.stderr
    return linux_path(out)


@pytest.mark.parametrize("case", CASES)
def test_actual_libdrm_node_discovery(discovery_binary, case):
    result = run_linux([discovery_binary, case])
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "pass: " + case
