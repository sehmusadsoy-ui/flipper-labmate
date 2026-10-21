# LabMate v2.0 — Phase3E firmware display and PC backup integrity evidence

**Evidence source:** Owner-provided Flipper LCD screenshots and Windows/WSL Python verifier stdout. This document is not a device firmware binary or active FAP cryptographic readback.

## Screen-derived observations

- Flipper Firmware Info displayed **Momentum-dev [6-10-2026]**, base short hash **d3f89dfe**, and related firmware build information.
- The running app About screen displayed **LabMate v1.9DEV**, **15 tool guides**, **3.3V GPIO ONLY**.
- These LCD labels support that **v1.9DEV is currently running, not the Phase3D v2.0 development FAP**; they do not authenticate the installed application's exact bytes, nor independently prove runtime E11 ABI compatibility.

## Owner's PC-integrity result

Owner executed `scripts/check_v19_e11_pc_backups_windows_ro.py` with existing immutable PC snapshot folders:

```text
PC_BACKUPS_PASS: 12 files, 2128 bytes
WINDOWS_PC_BACKUPS_RO: PASS | DEVICE_WRITES: ZERO | PC_WRITES: ZERO
PHASE3E PC BACKUP INTEGRITY: PASS
DEVICE WRITES: ZERO
```

This script's `verify_backups` checks exact pinned v1.8 Final and historical E11 v1.8DEV FAP sizes and SHA-256 hashes, their readback reports and the 12-file LabMate data snapshot against both PC and recorded on-device hashes. **This confirms those historical backups were intact at read time, but NOT a backup of currently active v1.9DEV.** It does not compare current device microSD data against a fresh readback.

## Next step: protect the current live v1.9DEV FAP

Before approving any v2.0 app trial, use qFlipper File Manager > SD Card > apps > Tools > `labmate.fap` > right-click Download to save the **current installed** FAP into a NEW dedicated PC directory. Avoid Upload, Delete, Rename, Firmware Update, Restore. Re-hash downloaded bytes locally and preferably compare the on-device MD5 before/after a read-only native CLI audit. If the file is absent or download fails, stop and classify state read-only; never guess which existing backup matches the active FAP.

**Phase3D source FAP** is independently owner-hash checked at 115104 bytes and SHA-256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`; this is the new development candidate and MUST NOT overwrite active LabMate or get flashed.

**Stage decision:** Historical backup integrity PASS; on-screen firmware/app version observed; current active app byte identity + dedicated PC backup **PENDING**; installation, rollback rehearsal, runtime proof, v2.0 Stable **NO-GO**. No device writes authorized by this document.
