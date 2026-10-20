# glibc and RT Backend Migration

## Agreed Scope

- Work only in the graphics validation copy.
- Cortex-A: Linux GCC; application support and acceptance use glibc.
- Cortex-M: bare-metal GCC; basic freestanding functionality only, no newlib application path.
- Kernel builds remain freestanding and do not link the target glibc.
- Preserve glibc static/dynamic C/C++ and graphics functionality.
- Add an independent NanoPC-T4 RT backend target; keep ThreadX as a comparison.

## Execution Plan

1. Add failing contracts for compiler selection and Linux-only ELF dispatch.
2. Migrate Cortex-A platform/tool overrides and remove newlib-only loader/application entries.
3. Rebuild all dependencies cleanly for NanoPC-T4, then compile basic ARMv7-A/Cortex-M targets.
4. Build the RT backend image separately and record compiler, configuration and image hashes.
5. Coordinate board handoff: do not interrupt the current guardian or open COM5 alongside the collector.
6. Validate glibc applications, Weston startup, sixteen distinct 4x4 windows, mouse and reclamation.

## Acceptance Boundaries

Host tests, successful linking, QEMU results and physical display acceptance are separate evidence.
Do not claim an RT graphics pass until the exact RT image has run on the board with user visual confirmation.
Existing glibc assets must be rebuilt or identified by hashes before reusing them as migration evidence.
Removing newlib support does not require deleting general ELF relocation or module-loader machinery
that is still used by kernel modules or other supported runtime paths.

## Progress

Final bounded result: both selectable backends passed their separate NanoPC-T4
sixteen-window, 600-second runs, including user visual confirmation and all
sixteen client reclamation checks. This does not mean two kernels execute
simultaneously or establish long-duration stability.

- Scope and architecture split confirmed by the user.
- RT backend source cloned from the configured project server master.
- Linux-only ELF dispatch and application matrix are implemented; retired newlib CRT/runtime build entries are removed while shared UAPI headers remain.
- Fresh integrated builds succeeded for NanoPC-T4 ThreadX, NanoPC-T4 RT, Zynq ARMv7-A and MPS2 Cortex-M. Cortex-M remains on its bare-metal compiler.
- libdrm, Mesa, glmark2, kmscube and Weston rebuilt successfully. Qt example applications rebuilt against the installed SDK; this is not a clean rebuild of every Qt library and host tool.
- Focused migration regressions: 79 passed. The full loader suite still has six failures reproduced on its unmodified baseline; these are not migration passes.
- MPS2 TCP-UART QEMU basic shell checks passed; timer progression remains an acceptance gap.
- Zynq QEMU glibc static/dynamic C/C++ markers passed. The expanded pthread/socket test stalls at file-time after its pthread counter; the expanded suite has not passed.
- RT physical boot first exposed a pre-scheduler sleep null dereference. Its focused regression and board progress past the previous crash point verified the fix.
- The next RT boot reached all six CPUs and the shell, but formatted command results were missing. A print queue checked IRQ state after its own irqsave, incorrectly suppressing RT thread draining. Regression coverage now models actual IRQ masking/restoration: nine printing tests passed.
- Corrected RT BIN SHA256 `038bb7ae0fcc2051be03cc543773a21239e46348f82c26e092b3abd537ac4dde`, CRC32 `1ae613d4`, passed board transfer verification and boot. Device initialization and actual `ps`, `wdt status`, `thermal`, and mounted-root directory output are restored. WDT is disarmed; initial CPU/GPU temperatures were approximately 44/40 C. The separate thread-name termination fix passed host regressions after this image was built; that fix is not part of the board-tested BIN.
- On that exact RT image, rebuilt ARM64 glibc static C passed 23/23 checks; static C++, dynamic C and dynamic C++ emitted their pass markers and exited zero. C++ thread creation also executed.
- Rebuilt graphics files and SONAME aliases were uploaded with SHA256 FTP readback and recoverable per-file backups. Weston PID11 initialized Panfrost, the HDMI 1920x1080 output and input devices. Sixteen clients PID14-29 completed the ten-minute temperature-protected short test (guardian PID39460).
- The user confirmed that the 4x4 sixteen-model display, motion and mouse are normal on the RT image above. This is physical startup/short-run visual acceptance, not a completed ten-minute endurance or reclamation pass. At confirmation the guardian remained active, with CPU/GPU approximately 47.5/43.3 C and an 85 C protection threshold.
- The RT ten-minute guardian subsequently finished with `reason=requested duration completed`. All sixteen PID14-29 recovery checks returned ESRCH. Post-run shell commands, mounted-root access and Weston PID11 state=1 still responded; WDT remained armed=0. The final retained load sample was CPU/GPU 51.1/47.5 C. Evidence is archived outside source repositories as `rt-glibc-10min-guardian-20261020.json`. This completes the bounded short run, not long-duration stability acceptance.
- Automatic periodic board inspection remains paused; the collector continues to own COM5 exclusively. The short test guardian alone owns the command mailbox while active. WDT remains off.

## Cleanup And ThreadX Impact

- `components/ulib` now retains only `include/luna/uapi_generic.h` as its public header. Unused private syscall wrappers and socket compatibility headers are removed, in addition to the retired CRT/libc bridge sources. Loader and ARMv7 ABI consumers still need the fixed-width UAPI layouts; deleting the repository outright would break those references.
- Active test fixtures now use glibc targets. Historical design records and tests asserting that retired runtime paths stay absent are intentionally retained. Two obsolete ulib compilation databases were removed. Four old newlib-only compilation-database directories in luna-test remain because the cleanup command was rejected by execution policy; no runtime source or active target remains in those directories.
- RT sleep and thread-name fixes are confined to `rt-smp-nano/osal`; ThreadX does not link that backend. The independent target contract checks that NanoPC backend selection is isolated.
- The print-queue IRQ entry-state correction is shared by both backends. Executable tests cover ThreadX state zero, RT state one, interrupt enqueueing and later thread draining. It is therefore an intentional shared behavior change, not an RT-only change.
- Linux GCC/header type adjustments, Linux-only loader dispatch and newlib retirement also affect ThreadX builds. These are toolchain/application-policy changes, not a ThreadX scheduler replacement.
- The watchdog observer hook was renamed in both the shared driver and its ThreadX implementation. Its body is unchanged; absent hooks reject monitored arming. WDT remains off unless explicitly requested.
- Cleanup and backend contracts: 79 passed, one known three-VM shell-script contract deselected after reproducing its failure. This is not a claim that the full test repository passes.
- Fresh ThreadX NanoPC full build succeeded with 77 warnings and no errors. BIN SHA256 `3c94e403363cfabbd0b82afe0a86920881f06ac0501836d638738bf14cb3d3b9`; ELF SHA256 `95fc82d24f1d00fbecf089c5e61e26e125b2c59951fd398e5d8f11a2479c572f`. This exact image subsequently completed the comparison below.

## ThreadX Comparison Completed

After the user reset the board, the ThreadX BIN above was loaded and verified
with board CRC32 `76f55614` before boot. Actual ps, thermal and mounted-root
results are present, and WDT reports armed=0 feeds=0. The same four rebuilt
glibc C/C++ tests passed with zero exit status; static C passed 23/23 checks.
Weston PID11 reached running state using the same deployed graphics assets.
Guardian PID33324 ran sixteen clients for 600 seconds after all clients
started, with 85 C protection and no diagnostics.
Evidence uses `threadx-glibc-board-20261020.json` and
`threadx-glibc-startup-3c94e403363c.log` outside source repositories.

The user subsequently confirmed that all sixteen models and mouse are normal
on ThreadX. At confirmation guardian PID33324 was still active with PID14-29;
CPU/GPU were approximately 52.8/50 C. Physical startup/short-run visual
acceptance was recorded before the duration and reclamation checks below.

The ThreadX guardian subsequently finished with
`reason=requested duration completed`; every PID14-29 returned ESRCH in
recovery checks. Post-run ps, mounted-root access and Weston PID11 state=1
responded. WDT remained armed=0 feeds=0. The final retained load sample was
CPU/GPU 52.2/48.8 C. Evidence is preserved as
`threadx-glibc-10min-guardian-20261020.json`. Both backend ten-minute tests
therefore have user visual confirmation and successful bounded completion /
client reclamation evidence; neither establishes long-duration stability.

## Reproduction And Evidence Index

Use the integration configuration in `integrated`, not the standalone legacy
ThreadX platform defaults. Build with `catboy integrated build -t
nanopc-t4-rt-user --full -j4` or `catboy integrated build -t nanopc-t4-user
--full -j4`, with the installed Linux GCC binaries on PATH. These are
alternative backend images and require separate boots. The standalone
ThreadX repository still has bare-metal Cortex-A platform defaults; those
entries were not part of the accepted integrated build path.

Both runs used the same deployed graphics assets, 4x4 layout, sixteen clients,
600 seconds counted after launch, WDT off and an 85 C temperature limit.
The application matrix on each backend passed glibc static C (23/23), static
C++, dynamic C and dynamic C++ tests with zero exit status. Neither run proves
all scheduler behaviors, all BSPs, long-duration stability or a clean rebuild
of the complete Qt SDK.

Evidence files reside beside the validation workspace, not inside source
repositories; the following SHA256 values bind the bounded records:

| Evidence | SHA256 |
| --- | --- |
| RT guardian final status | `a5740936fc3bc653378dff7c7127355e5eee05c4ff35a952ffc2d00e09faa739` |
| ThreadX guardian final status | `6fc61058616b7e9eef7214c8237502c52e7d816535f5379a484fe34963d03bc1` |
| RT command receipts | `2d49c375f66635398f8d58368da54a49b3a3525a1184f5899c4ccb4ab40b3352` |
| ThreadX command receipts | `1d262db35ce3add15ed156b781000f15d379e6244231147714d263f79f39e704` |

Before committing, focused host tests passed 119 with 19 compiler probes
initially skipped. Re-running the compiler suites with LUNA_TOOLCHAIN_ROOT
set passed all 28 tests, including the 19 probes. The separate RT early-sleep,
print/state and thread-name executable harnesses each reported zero failures.
Known broader loader/QEMU gaps remain listed above and are not hidden by
these focused results. Local target-generated six-core default-header drift
and all probe binaries/caches are intentionally excluded from source commits.
