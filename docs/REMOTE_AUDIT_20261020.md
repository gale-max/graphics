# Graphics Repository Remote Audit

Audit date: 2026-10-20.

Scope: only the 33 repositories under the graphics validation copy's os directory.
The primary Luna checkout and Catboy are excluded from modification/publication.

All 33 origin endpoints answered ls-remote. 21 GitHub upstream endpoints answered;
12 returned Repository not found while SSH authenticated as Surest-ok.
This means missing or inaccessible, not an unconditional proof of nonexistence.

Publication uses fast-forward master updates plus a release tag when possible.
Diverged/behind master branches are preserved; a separate release branch and tag
publish this snapshot there. A read probe does not prove a successful push.

Release tag: `graphics-grid16-20261020`. The release is initial graphics acceptance, not a claim
that the ongoing four-hour test has completed.

| Repository | origin | GitHub upstream |
| --- | --- | --- |
| components/ahci | `ssh://git@git.xahwsys.com:2222/luna/ahci.git` | `git@github.com:Surest-ok/ahci.git` (not found / inaccessible) |
| components/arch-armv7a | `ssh://git@git.xahwsys.com:2222/luna/arch-armv7a.git` | `git@github.com:Surest-ok/arch-armv7a.git` (reachable) |
| components/arch-armv7m | `ssh://git@git.xahwsys.com:2222/luna/arch-armv7m.git` | `git@github.com:Surest-ok/arch-armv7m.git` (reachable) |
| components/arch-armv8a | `ssh://git@git.xahwsys.com:2222/luna/arch-armv8a.git` | `git@github.com:Surest-ok/arch-armv8a.git` (reachable) |
| components/dm | `ssh://git@git.xahwsys.com:2222/luna/dm.git` | `git@github.com:Surest-ok/dm.git` (reachable) |
| components/drm | `ssh://git@192.168.31.6:2222/luna/drm.git` | `git@github.com:Surest-ok/drm.git` (not found / inaccessible) |
| components/fdt | `ssh://git@git.xahwsys.com:2222/luna/fdt.git` | `git@github.com:Surest-ok/fdt.git` (reachable) |
| components/fs | `ssh://git@git.xahwsys.com:2222/luna/fs.git` | `git@github.com:Surest-ok/fs.git` (reachable) |
| components/hypervisor | `ssh://git@git.xahwsys.com:2222/luna/hypervisor.git` | `git@github.com:Surest-ok/hypervisor.git` (reachable) |
| components/linux-runtime | `ssh://git@192.168.31.6:2222/luna/linux-runtime.git` | `git@github.com:Surest-ok/linux-runtime.git` (not found / inaccessible) |
| components/loader | `ssh://git@git.xahwsys.com:2222/luna/loader.git` | `git@github.com:Surest-ok/loader.git` (reachable) |
| components/module | `ssh://git@git.xahwsys.com:2222/luna/module.git` | `git@github.com:Surest-ok/module.git` (reachable) |
| components/netx | `ssh://git@git.xahwsys.com:2222/luna/netx.git` | `git@github.com:Surest-ok/netx.git` (reachable) |
| components/nvme | `ssh://git@git.xahwsys.com:2222/luna/nvme.git` | `git@github.com:Surest-ok/nvme.git` (reachable) |
| components/pcie | `ssh://git@git.xahwsys.com:2222/luna/pcie.git` | `git@github.com:Surest-ok/pcie.git` (reachable) |
| components/posix | `ssh://git@192.168.31.6:2222/luna/posix.git` | `git@github.com:Surest-ok/posix.git` (not found / inaccessible) |
| components/ulib | `ssh://git@git.xahwsys.com:2222/luna/luna-ulib.git` | `git@github.com:Surest-ok/luna-ulib.git` (reachable) |
| components/usb | `ssh://git@192.168.31.6:2222/Surest/usb.git` | `git@github.com:Surest-ok/usb.git` (not found / inaccessible) |
| components/ushell | `ssh://git@git.xahwsys.com:2222/luna/ushell.git` | `git@github.com:Surest-ok/ushell.git` (reachable) |
| components/vfs | `ssh://git@git.xahwsys.com:2222/luna/vfs.git` | `git@github.com:Surest-ok/vfs.git` (reachable) |
| components/virtio | `ssh://git@git.xahwsys.com:2222/luna/virtio.git` | `git@github.com:Surest-ok/virtio.git` (reachable) |
| components | `ssh://git@git.xahwsys.com:2222/luna/components.git` | `git@github.com:Surest-ok/components.git` (reachable) |
| document | `ssh://git@git.xahwsys.com:2222/luna/documents.git` | `git@github.com:Surest-ok/documents.git` (not found / inaccessible) |
| graphics | `ssh://git@192.168.31.6:2222/luna/graphics.git` | `git@github.com:Surest-ok/graphics.git` (not found / inaccessible) |
| integrated | `ssh://git@192.168.31.6:2222/luna/integrated.git` | `git@github.com:Surest-ok/integrated.git` (not found / inaccessible) |
| luna | `ssh://git@git.xahwsys.com:2222/luna/luna.git` | `git@github.com:Surest-ok/luna.git` (reachable) |
| luna-go | `ssh://git@git.xahwsys.com:2222/luna/go-luna.git` | `git@github.com:Surest-ok/go-luna.git` (not found / inaccessible) |
| luna-test | `ssh://git@192.168.31.6:2222/luna/luna-test.git` | `git@github.com:Surest-ok/luna-test.git` (not found / inaccessible) |
| rockchip | `ssh://git@192.168.31.6:2222/luna/rockchip.git` | `git@github.com:Surest-ok/rockchip.git` (not found / inaccessible) |
| stm32 | `ssh://git@git.xahwsys.com:2222/luna/stm32.git` | `git@github.com:Surest-ok/stm32.git` (reachable) |
| threadx | `ssh://git@git.xahwsys.com:2222/luna/threadx.git` | `git@github.com:Surest-ok/threadx.git` (not found / inaccessible) |
| virt | `ssh://git@git.xahwsys.com:2222/luna/virt.git` | `git@github.com:Surest-ok/virt.git` (reachable) |
| zynq7k | `ssh://git@git.xahwsys.com:2222/luna/zynq7k.git` | `git@github.com:Surest-ok/zynq7k.git` (reachable) |

## Reconstruction

Check out the same `graphics-grid16-20261020` tag in every repository.
The integrated repository contains repo.graphics-grid16-20261020.yaml selecting
release/graphics-grid16-20261020 branches, paired with the immutable release tag.
Catboy's current synchronization code requires a branch, not a bare tag name.
Verify each branch HEAD against the release tag before claiming an exact snapshot.
SDK/runtime packages and host collector evidence are separate deliverables;
see SDK_HANDOFF.md and GRID16_VALIDATION_20261020.md.

## Cleanup Boundary

15 tracked Python cache files were removed from the Git index.
Local cache files were retained and ignore rules prevent re-adding them.
No recursive git clean, branch deletion, history rewriting or force-push is used.
Existing build outputs and active collector/board-test files are retained.


## Unchecked Manifest Entries

The RT-Nano aliases refer to rt-smp-nano, which is not checked out in this
33-repository copy. Its entries retain their original master reference.
The snapshot is therefore the NanoPC-T4 graphics release, not acceptance
or complete reconstruction of every RT-Nano target in the general manifest.
