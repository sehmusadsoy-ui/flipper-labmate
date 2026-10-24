# LabMate v2.0 — Phase 3E PC preflight (owner observation)

**Date recorded:** 2026-10-22.  **Development branch:** `dev/v2.0-signal-doctor`; Draft PR #21.  **Device writes:** NONE.

## Owner-reported WSL results

```text
=== PHASE3E PC PREFLIGHT ===
PHASE3D FAP HASH: PASS
PHASE3D FAP SIZE: PASS

=== PC BACKUP INVENTORY ===
E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d
V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482
V19-LabMate-Data-bbacf95032af4bf2bbb470614eaff1a0
Backup FAP files:
E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d/installed_E11_v18DEV_before_final_label.fap
V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482/installed_LabMate_v18_FINAL_E11_before_v19.fap
V19-SCOPE-REDESIGN-PREBUILD-72eb58d/labmate-v19-99376-before-redesign.fap
V19-UI-POLISH-PREBUILD-6d258bf/labmate-v19-before-ui-polish-97724.fap
V19-WINDOWS-PC-CANDIDATE-3d66658-20261019/labmate-v1.9DEV-E11-WINDOWS-PC-ONLY.fap

PHASE3E PC PREFLIGHT COMPLETE
DEVICE WRITES: ZERO
```

**Input artifact checked on owner's host:**
`/home/adsoy/labmate-v20-phase3d-build-20261021/momentum-src/build/f7-firmware-C/.extapps/labmate.fap`

**Artifact:** 115104 bytes, SHA-256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`. The owner ran checks against these pinned values and both passed.

## Strict evidence boundaries

- This preflight **only showed that known backup directories and candidate FAP paths exist**. It did NOT hash, authenticate, or read the contents of any backup.
- **Current installed Flipper firmware and active LabMate FAP are unverified** in this run. Old V19 read-only checks assume an older installed v1.8 app, so MUST NOT be run as if that were still the live state.
- **Next gate:** run the existing `scripts/check_v19_e11_pc_backups_windows_ro.py` with three known PC backup folders. This verifier reads pinned FAP hashes, report metadata and all 12 data snapshot MD5/SHA256 values and does no COM/device/PC writes.
- After backup integrity passes, inspect Flipper firmware identity and installed app state separately, read-only. Do not use a legacy v1.8/v1.9 install, stage, activation, or rename script for this v2.0 artifact.
- **Installation permission has not been granted merely by running PC preflight.** No FAP upload, rename or firmware flash until the current on-device state and rollback are independently reviewed and the owner explicitly approves the specific write.

**Gate decision:** PC candidate binary identity PASS; backup *existence* PASS; backup *integrity* PENDING; device identity PENDING; FAP-only trial PENDING/NO-GO; v2.0 Stable NO-GO.
