# 4x4 Grid and ps Deployment

- Kernel BIN SHA256: `41f6923834fa56fa7eb3e4aac96c9f0fe686ca669e996bc5793d718950d982f4`.
- Board transfer CRC32: `13132b1d`.
- Desktop-shell SHA256: `851a393a3bc061cda05353cad84dbb22aa4e210916c55fd7013d0529e378d629`.
- Grid configuration SHA256: `a5a13eb9b612f51de481053c6b63cdc11632ce0ff15670ee68313b8d4397786d`.

The module and configuration were uploaded under temporary names, read back and
hashed before rename. Existing board files were retained under backup names.
Both files were read back again after reboot; the configuration selects four
rows and the module matches the rebuilt source artifact.

The previous 4-hour run was interrupted at the user's request to deploy this
change. Its 16 clients were confirmed ESRCH; it is not a completed 4-hour result.
The prior guardian status is preserved in
`grid16-validation-20261020/interrupted-run-guardian.json` in the host workspace.

The actual board ps output now reports the shell on CPU0, uses TID rather than
PID and displays allowed CPUs as ranges/lists. The table is captured in
`grid16-ps-table-20261020.log`; startup is in `grid16-ps-startup-20261020.log`.

The geometry regression executes the C placement helper and verifies pairwise
non-overlap and display bounds for all 16 positions. This is not a substitute
for confirming four visible columns and four visible rows on the physical panel.

On 2026-10-20 at approximately 10:12 Beijing time, the user explicitly confirmed
four rows by four columns, all 16 models separately visible and moving, and
normal mouse input. This accepts the initial physical layout/input check, not
the subsequently ongoing four-hour stress result.

Hardware WDT remains disabled. The 85 C thermal guardian is enabled. New
long-run acceptance belongs to this image/module/configuration combination,
not the earlier 12-position layout.
