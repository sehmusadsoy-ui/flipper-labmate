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

## 2026-10-22 — Current active v1.9DEV FAP downloaded to PC

Owner used qFlipper to download `/ext/apps/Tools/labmate.fap` into a distinct PC backup folder and reported the following WSL local read-only screening:

```text
=== LABMATE V19 BACKUP CHECK ===
ACTIVE V19 PC COPY: PRESENT
FAP BYTES: 101468
FAP SHA256: d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2
DEVICE WRITES: ZERO
BACKUP LOCAL CHECK: PASS
```

PC-backed path: `C:\\Users\\sehmu\\Documents\\LabMate-FAP-PC-Backups\\V20-Phase3E-current-v19-before-v20\\labmate.fap`. Its hash has been observed on the owner's PC, **not yet independently confirmed against the current live device**. It is not the earlier 97,540-byte v1.9 candidate nor the 81,528-byte historical v1.8 backup. Do NOT assume equivalence.

Next strictly read-only gate: compute the local PC file MD5, then compare it to `storage md5 "/ext/apps/Tools/labmate.fap"` in the native device CLI, ideally add `storage stat` for 101468-byte size. These commands do not install or replace FAPs. Never paste PowerShell syntax into WSL bash, and quit qFlipper before acquiring COM7 through the web serial CLI. If local versus live MD5 differ, STOP; do not upload, rename, delete, flash, or substitute old backups.

**Status:** active v1.9DEV PC-copy presence, size, SHA256 **PASS**; full current live device backup byte parity **PENDING**. Device trial and v2.0 Stable NO-GO.

## 2026-10-22 — Current live v1.9 app read-only CLI stat / MD5

Owner provided a Flipper Lab CLI screenshot after connecting to device. Command outputs, transcribed exactly from displayed CLI:

```text
Firmware version: HEAD mntm-dev (d3f89dfe-dirty built on 16-10-2026)
>: storage stat "/ext/apps/Tools/labmate.fap"
File, size: 101468b
>: storage md5 "/ext/apps/Tools/labmate.fap"
066f017c695bb5a17158a7b26c8f4838
```

**Device app FAP size:** 101468 bytes — matches PC-downloaded copy size (reported in preceding gate).  
**Device app MD5:** `066f017c695bb5a17158a7b26c8f4838`.  
**PC copy SHA-256:** `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2` (owner-reported local hash).  
**PC copy MD5:** **MATCHED after later local hash verification**, as detailed below. Matching sizes alone is not proof of identical content. No device write occurred as part of `storage stat` / `storage md5`.

**Important firmware detail:** The screenshot's CLI says **built on 16-10-2026**, with short source `d3f89dfe-dirty`. The earlier on-device firmware info page was reported as **6-10-2026**; the CLI build timestamp is the observed value for this capture and differs from the earlier display. The `-dirty` suffix means the build reports local changes; short source identity does NOT attest exact installed binary ABI. Treat as separate evidence, not a firmware-flash recommendation.

**Gate:** PC MD5 parity PENDING; FAP-only installation NOT performed/authorized by these checks. Preserve the active FAP and all old backups. No automatic rename/upload.

## 2026-10-22 — LIVE v1.9DEV PC rollback copy parity PASS

The owner ran a local bash script that checked the downloaded PC copy of the active FAP against the Flipper CLI `storage md5` response and against the original PC SHA-256 value:

```text
V19 DEVICE-PC MD5 MATCH: PASS
V19 PC SHA256: PASS
V19 ROLLBACK COPY INTEGRITY: PASS
DEVICE WRITES: ZERO
```

**Live / PC MD5 match:** `066f017c695bb5a17158a7b26c8f4838`.  
**PC SHA-256:** `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2`.  
**Size:** 101468 bytes.

Thus the **current installed `labmate.fap` matches the downloaded PC file by MD5**, and the PC file also matches the independently recorded SHA-256. This is a verified read-only rollback *source* copy (not an exercised rollback procedure). Historical v1.8 FAP and twelve LabMate SD data file backups also passed earlier PC integrity verification. No device writes, flash, firmware changes or rollback occurred in this gate.

**NEXT:** prepare PC-only copy of exact Phase3D 115104-byte, SHA-256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737` candidate under a new filename, preserving this v1.9 copy. New FAP-only *side-by-side test* upload must have separate explicit approval, verify destination collision/readback and should NEVER overwrite `/ext/apps/Tools/labmate.fap`; test runtime and verify old app remains accessible. Release v2.0 Stable remains NO-GO.

