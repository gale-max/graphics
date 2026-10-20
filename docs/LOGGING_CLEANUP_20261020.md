# Kernel Logging Cleanup

## Candidate

- BIN SHA256: `e7cd263c460c2ecef68860329d8fa6c80ba0a15f5930dbffd76fdeb9f4b2f07e`.
- Full `nanopc-t4-user` build succeeded; existing compiler warnings remain.
- 42 targeted host regressions passed, including executable log-level/prefix
  checks and the timerfd, watchdog-default, MMU and DRM VFS contracts.

## Changes

- Removed I2C probe checkpoints, Linux work callback-address prints, DRM
  endpoint/EDID/HPD dumps and USB/GMAC before/after register dumps.
- Removed FDT phandle enumeration and address-translation checkpoints.
- Removed DRM init/lastclose begin/ready/done checkpoints.
- Routed Luna Linux compatibility console output through `luna_print`, with
  timestamps and severity. Retained error/warning/notice distinctions and
  decoded Linux printk level prefixes.
- Emitted DRM formatted messages as single records instead of separately
  printing their prefix and body.
- Removed the OPP raw-console override; deferred probe is not logged as a
  repeated failure. Frequency/voltage readbacks and real errors remain.
- Initialized the optional vblank worker's empty list and wait queue instead
  of suppressing the real startup warning. The regression failed before the fix.
- Added severity to watchdog and thermal startup status, while keeping shell
  query replies unmodified. Environment startup status reports the resolved path.
- Corrected ps to label thread IDs as TID and display allowed CPU sets as
  ranges/lists instead of internal masks.

## Runtime Boundary

These are kernel logs. Application-owned Weston/glmark2 stdout is not rewritten
by the kernel log bridge. Shell command replies are also intentionally distinct
from kernel logging.

The previous four-hour run uses a different image. Its result must not be
attributed to this candidate. The replacement run requires its own deployment
CRC, startup log, thermal-guardian results and user visual confirmation.

Hardware watchdog remains opt-in and disabled at boot. The host guardian keeps
the default 85 C protection. Neither successful builds nor network/FPS progress
establish physical display acceptance.
