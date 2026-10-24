# LabMate v2.0 — Phase 3D native Frequency & Pulse E11 FAP build evidence

**Owner-supplied execution time:** 2026-10-21 23:59, Ubuntu WSL.  
**Development line:** `dev/v2.0-signal-doctor` / Draft PR #21; not a release.  
**Evidence boundary:** Log output was copied into the project chat by the owner. Assistant has NOT independently opened the owner's binary or generated an E11 image. The local Phase2F fixture was patched with the exact content from commit `9f3e838ec4294435c46eeb9fe4344481bd9188e0` prior to the successful run.

## Build invocation and result

Isolated build workspace:

`/home/adsoy/labmate-v20-phase3d-build-20261021/momentum-src`

FAP:

`/home/adsoy/labmate-v20-phase3d-build-20261021/momentum-src/build/f7-firmware-C/.extapps/labmate.fap`

The owner ran the repository's `scripts/build-v20-phase3b-e11-isolated.sh`, which executes the offline GCC/Clang host suite prior to the isolated, pinned E11 SDK source compilation. The prior Phase2F mock `LabMateApp` compile failure was corrected as a host fixture change, not by removing production IRQ evidence.

Actual user-reported final output:

```text
CC      applications_user/labmate/src/labmate_doctor_frequency_bridge.c
CC      applications_user/labmate/src/labmate_doctor_frequency_policy.c
CC      applications_user/labmate/src/labmate_doctor_pulse_bridge.c
CC      applications_user/labmate/src/labmate_doctor_pulse_policy.c
LINK    build/f7-firmware-C/.extapps/labmate_d.elf
SDKCHK  targets/f7/api_symbols.csv
API version 87.1 is up to date
APPMETA build/f7-firmware-C/.extapps/labmate.fap
FAP     build/f7-firmware-C/.extapps/labmate.fap
FASTFAP build/f7-firmware-C/.extapps/labmate.fap
APPCHK  build/f7-firmware-C/.extapps/labmate.fap
V19 E11 SDK EXPORTED-API/FAP REVIEW PASS | bytes=115104 | sha256=53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737
REVIEW ONLY — NO DEVICE WRITES OR FIRMWARE INSTALLATION
53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737  /home/adsoy/labmate-v20-phase3d-build-20261021/momentum-src/build/f7-firmware-C/.extapps/labmate.fap
V20 CURRENT E11 FAP BUILD AND REVIEW PASS | BUILD ONLY | NO FLASH
```

**FAP size:** 115,104 bytes.  
**SHA-256:** `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`.  
**Previous Phase3C size:** 111,540 bytes. Difference: +3,564 bytes.

Two **non-blocking SDK external app manifest warnings** remain (not LabMate compilation errors): `applications/external/cli_bridge/application.fam` invalid `.cli_gui` appid and `applications/external/mtp/application.fam` invalid `.f0_mtp` appid. Do not edit unrelated SDK manifests absent a separate scoped task.

## Acceptance decision

- **PASS, owner-run log:** Local pinned-E11 application source compile, link, FAP generation, APPCHK and exported-API/FAP integrity review.
- **Host suite gate exited zero:** Inferred from the build script progressing to FBT; complete per-test output is NOT included in this excerpt, so do not invent individual run counts.
- **PENDING:** Flipper installation (not authorized in this run); actual PC1/PB3/Pulse capture → STOP/BACK → released native leases → sealed snapshot → displayed Signal Doctor verdict; visual 128x64 QA, false positive/no-signal boundaries and physical accuracy.
- **NO-GO:** call this v2.0 Stable, alter `main`, publish release/tag, flash firmware, or overwrite the existing protected FAP/SD data.

**Next safe step:** Record the accepted host/native build and prepare an explicit E11 on-device regression and rollback checklist. Confirm device write authorization separately before any installation. The owner can preserve this exact known-hash FAP untouched as the Phase3D review artifact.
