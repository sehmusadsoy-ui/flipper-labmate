# LabMate v2.0 — Phase 3B real E11 WSL FAP build result

**Date of owner's test:** 2026-10-21, 22:35 local log time.  
**Development branch:** `dev/v2.0-signal-doctor`, Draft PR #21.  
**Scope:** Owner-executed WSL build of the Phase3B ZIP source using `scripts/build-v20-phase3b-e11-isolated.sh`. No GitHub Actions claim; the assistant did not independently access the owner's machine or the resulting FAP bytes.

## Verified by user-provided console output

```text
LINK    build/f7-firmware-C/.extapps/labmate_d.elf
SDKCHK  targets/f7/api_symbols.csv
API version 87.1 is up to date
APPMETA build/f7-firmware-C/.extapps/labmate.fap
FAP     build/f7-firmware-C/.extapps/labmate.fap
FASTFAP build/f7-firmware-C/.extapps/labmate.fap
APPCHK  build/f7-firmware-C/.extapps/labmate.fap
V19 E11 SDK EXPORTED-API/FAP REVIEW PASS | bytes=107484 | sha256=b6043433a55cee5d6b5fd42d13fe5aafff0040da0e890abd179089100de08f6e
REVIEW ONLY — NO DEVICE WRITES OR FIRMWARE INSTALLATION
b6043433a55cee5d6b5fd42d13fe5aafff0040da0e890abd179089100de08f6e  /home/adsoy/labmate-v20-phase3b-build-20261021/momentum-src/build/f7-firmware-C/.extapps/labmate.fap
PHASE3B E11 FAP BUILD AND REVIEW PASS | HOST ONLY | NO FLASH
```

**Artifact:** 107,484 bytes, SHA-256 `b6043433a55cee5d6b5fd42d13fe5aafff0040da0e890abd179089100de08f6e`.  
**Prior Phase3A artifact:** 103,152 bytes, SHA-256 `f361e1b8757520f392b1577b40ce23cae914f250c30fdfc0b75fe2f3058ef9d8`.  
**Change in artifact size:** +4,332 bytes; *not* a proof of UI function or behavior.

The build script invokes the integrated offline host gate before FBT; reaching the `PHASE3B E11 FAP BUILD AND REVIEW PASS` line indicates it did not stop on a failing host runner, although the complete per-suite transcript was not included in this user-supplied excerpt.

## Acceptance boundaries

- **PASS — owner-run:** E11-patched Momentum SDK compile/link, FAP generation, FAP metadata/app checks, ARM ELF/API verifier.
- **PENDING:** hardware installation, on-device 128×64 visual checks and STOP/BACK; no device writes reported.
- **NOT IMPLEMENTED YET at Phase3B build:** completed verified Frequency/Pulse snapshot producer wired into the Signal Doctor's dashboard store. The screen correctly displays NO SEALED DATA without evidence.
- **NO-GO:** Call Phase3B a fully functioning live diagnostic instrument; publish v2.0 Stable or modify protected stable tags. Preserve installed v1.8/v1.9 FAPs and microSD CSV/Profiles.

**Decision:** Phase3B isolated SDK/FAP compiler gate **PASS**; live Doctor evidence end-to-end acceptance remains **PENDING/NO-GO**.
