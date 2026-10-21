# LabMate v2.0 — Phase 3C Pulse STOP E11 WSL FAP build evidence

**Date of owner-run build:** 2026-10-21 23:11 (local log timestamp).  
**Branch/source:** `dev/v2.0-signal-doctor` development ZIP with Phase 3C Pulse STOP producer.  
**SDK:** isolated copy of E11-patched Momentum; owner-run `LABMATE_E11_WORK="$HOME/labmate-v20-phase3c-build-20261021" bash scripts/build-v20-phase3b-e11-isolated.sh`.  
**Provenance limit:** owner supplied terminal log; no independent download/hash read of the owner's compiled bytes by assistant. This is NOT a hosted CI result.

## Output evidence

```text
        CC      applications_user/labmate/src/labmate_doctor_pulse_bridge.c
        CC      applications_user/labmate/src/labmate_doctor_pulse_policy.c
        LINK    build/f7-firmware-C/.extapps/labmate_d.elf
        SDKCHK  targets/f7/api_symbols.csv
API version 87.1 is up to date
        APPMETA build/f7-firmware-C/.extapps/labmate.fap
        FAP     build/f7-firmware-C/.extapps/labmate.fap
        FASTFAP build/f7-firmware-C/.extapps/labmate.fap
        APPCHK  build/f7-firmware-C/.extapps/labmate.fap
V19 E11 SDK EXPORTED-API/FAP REVIEW PASS | bytes=111540 | sha256=7f56e9dad3fc3a20bedb25155d01c5e6c7ffa0812d348a0e89852ed4eb169ef4
REVIEW ONLY — NO DEVICE WRITES OR FIRMWARE INSTALLATION
7f56e9dad3fc3a20bedb25155d01c5e6c7ffa0812d348a0e89852ed4eb169ef4  /home/adsoy/labmate-v20-phase3c-build-20261021/momentum-src/build/f7-firmware-C/.extapps/labmate.fap
PHASE3B E11 FAP BUILD AND REVIEW PASS | HOST ONLY | NO FLASH
```

**Important:** The final label still says PHASE3B because the reusable build script retains its old name and final message; actual compiled source list includes the new Phase3C files. No user-visible install/flash.

**Artifact size:** 111540 bytes.  
**SHA-256:** `7f56e9dad3fc3a20bedb25155d01c5e6c7ffa0812d348a0e89852ed4eb169ef4`.  
**WSL artifact:** `/home/adsoy/labmate-v20-phase3c-build-20261021/momentum-src/build/f7-firmware-C/.extapps/labmate.fap`.

### Non-blocking firmware manifest warnings observed

Two unrelated SDK external application manifests emitted warnings:
- `applications/external/cli_bridge/application.fam` appid `.cli_gui` is rejected against `^[a-z0-9_]+$`;
- `applications/external/mtp/application.fam` appid `.f0_mtp` similarly rejected.

The SDK continued to compile and verify the LabMate FAP. Do not silently rewrite unrelated Momentum manifests just to remove warnings. These are not a full-firmware CI acceptance test.

## Decision

- **PASS (owner-supplied transcript):** Phase3C native E11 SDK FAP compile/link, metadata, APPCHK, exported-API/FAP review, size and hash.
- **PASS (inferred from script reaching FBT):** integrated host script returned zero; detailed Phase2L/3A/3B/3C host lines were not supplied in this excerpt.
- **PENDING:** proof of actual Pulse IRQ→sealed snapshot→Doctor verdict on real Flipper; real 128×64 UX, START/STOP/BACK resource release, no false positive, UI review.
- **PENDING:** Frequency LOW/PC1 and HIGH/PB3/TIM2 source-backed snapshot generation.
- **NO-GO:** v2.0 Stable release, firmware flash, device installation, or modifying Stable/SD without explicit protection and consent.

**Note:** This report documents a past build. Later code edits would require a new FAP build, hash, and test evidence; do not carry forward this SHA to modified sources.
