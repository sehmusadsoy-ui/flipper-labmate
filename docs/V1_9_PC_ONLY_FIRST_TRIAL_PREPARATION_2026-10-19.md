# LabMate v1.9 — PC-only first E11 FAP trial preparation (NO DEVICE WRITE)

**2026-10-19. Draft/Review; NOT a device installation authorization.**
Branch: `dev/v1.9-logic-scope` (PR #15 stays Draft).
Stable v1.8 and the installed custom E11 Momentum firmware MUST remain unchanged.

## Locked identities

| Artifact | Verified fact |
| --- | --- |
| LabMate source used to build the local FAP | `3d66658dad6e09df9c011a91a78881bcc16eb25b` |
| Momentum base patched by E11 | `d3f89dfe2ef6b01839201598e9be1590cba80322` |
| v1.9 local compiled review FAP | **97,540 bytes**, SHA256 `e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90` |
| WSL local review ZIP | SHA256 `2161804ab0939110d79db861106569ea6f20262a20d0578491c40f513b4926f3` |
| v1.8 currently installed, read from real COM7 device to PC | **81,528 bytes**, SHA256 `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61` |
| Historical v1.8DEV E11 FAP PC backup | **81,532 bytes**, SHA256 `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0` |
| Live `/ext/apps_data/labmate` fresh PC-only snapshot | **2,128 bytes**, `LIVE LABMATE PC READBACK SNAPSHOT VERIFIED`; earlier history preserved separately |

Historical 45-path scoped `git diff` SHA256 parity **PASS** using Git `core.abbrev=7`: `1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80`. This is **source parity**, not a live internal-flash firmware SHA attestation. The `a0cc3040...` ZIP `PATCH_DIFF_SHA256` records a different, unscoped whole-tree diff calculation and is NOT an error.

The real final v1.8 live FAP backup and v1.8DEV historical backup are protected in **separate, verified PC directories**; the current data snapshot contains 7 live files not in the historical backup, 2 changed files, and 9 historical-only paths. This is not a declaration that the 9 missing paths were restored.

## Stage 0: entirely OFFLINE PC candidate verification

Script: `scripts/prepare_v19_e11_pc_only.py`. Offline synthetic tests: `tests/test_v19_e11_pc_only_preflight.py`. **Actual operator-reported Windows/WSL offline test result (2026-10-19): 12/12 PASS** using `python3 /mnt/c/Users/sehmu/labmate-src-v19/tests/test_v19_e11_pc_only_preflight.py -v`; output `Ran 12 tests in 0.031s` / `OK`. These are synthetic/unit tests, NOT yet an actual local review ZIP + PC backup integrity run; do not treat them as device installation authorization.

The script has **no serial import, no USB/COM access, no device filesystem access, and no firmware logic**. Default behavior is verify-only; adding `--prepare` creates a NEW, separately named PC-only folder with a byte-verified candidate FAP and provenance, never writes to Flipper. It checks:

1. Local review ZIP byte SHA256 and its exact four-member inventory; zip members never extracted to unsafe paths
2. Already-extracted FAP and text files are byte-identical to the ZIP; exact FAP size/SHA256, `SHA256SUMS.txt`, `SOURCE_SHA`, `MOMENTUM_BASE`, `PATCH_DIFF_SHA256`, `BUILD_MODE=LOCAL_WSL2`, and `GITHUB_ACTIONS_RUN=NONE`
3. The actual final-v1.8 live FAP backup SHA256, record `AFTER_PROMOTION`, readback marker and `device_writes=false`
4. Preserved historical E11 v1.8DEV backup hash, original live readback marker/report
5. Every file of the **current 2,128-byte** live LabMate snapshot against its recorded file size, device MD5, PC SHA256, manifest and completion marker; rejects altered/missing/extra members
6. Staging target must be a **new, absolute** PC directory with no overlap with source/backup folders. Existing files are never overwritten

PC output includes `labmate-v1.9DEV-E11-PC-ONLY.fap`, `PC_PREPARATION_PROVENANCE.json`, `SHA256SUMS.txt`, `READ_ME_NO_DEVICE_WRITE.txt` and `PC_ONLY_PREPARATION_VERIFIED.txt`.

**No file made by this stage is installed on the Flipper**. Passing this stage does NOT turn any old v1.8 hardware-install consent into v1.9 consent.

## Real operator PC-only preparation PASS — 2026-10-19

Following the independently run **12/12 offline synthetic tests PASS**, the operator executed `prepare_v19_e11_pc_only.py --prepare` against the **actual** local review ZIP/FAP and three real PC backup roots. Output:

```text
V19 E11 PC-ONLY REVIEW PREPARATION; NO USB/SD/FLASH
V19 FAP SHA256: e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90
LIVE V18 + HISTORICAL E11 PC BACKUPS: PASS
LABMATE DATA SNAPSHOT: PASS | files: 12 | bytes: 2128
PC_ONLY_PREPARATION: PASS
PC_OUTPUT: /home/adsoy/labmate-build/v19-pc-only-prepared-3d66658
DEVICE_WRITES: NONE | FIRMWARE_FLASH: NONE | V19 INSTALL: NOT AUTHORIZED
```

The separate PC preparation folder exists; this report does not claim it has been copied to Windows or Flipper, nor that any new application is installed. Both original FAP backups and all **12** currently live LabMate data files were hashed and verified.

## Stage 0.5: prospective v1.9 **device READ-ONLY** reserved-path preflight

A newly added strict-purpose check is `scripts/check_v19_e11_device_prewrite_ro.py`; Windows wrapper is `scripts/run-v19-e11-device-prewrite-ro.ps1`. The wrapper accepts only **13 exact pinned Git blob identities** from the local authenticated source checkout; it fetches nothing via anonymous raw URLs. It rechecks the verified older/full E11 files, active final-v1.8 PC readback, the current **12-file** LabMate snapshot and the already present final-v1.8 build. It then issues only:

- `device_info`, `storage md5`, `storage stat` of existing old/new v1.8 app and native plugin/resource paths via the previously operator-proven phase-2B `audit()`;
- `storage stat` of two **new** proposed v1.9 paths to require both **ABSENT twice**: `/ext/apps/Tools/labmate.v19-new-stage` and `/ext/apps/Tools/labmate.v18-final-before-v19.bak`;
- second `audit()` pass to reject mid-check installed v1.8 E11 identity drift.

The remote communication is **read-only**; no `write_chunk`, `storage rename`, `storage remove`, FAP upload, GPIO toggling, app launch or firmware flash paths. Unexpected CLI echo, unexpected status, existing empty stage, altered old PC backups/CSV, or resource drift produce NO-GO, no automatic retry.

Added **12 synthetic unit tests**: `tests/test_v19_e11_device_prewrite_ro.py`. **Not yet executed by the operator; no real COM7 result claimed.** Even a future PASS does not authorize any app replacement, which still needs a separate, reviewed staging/rollback implementation and express operator permission.

## Stage 1: separately designed, consent-gated future FAP-only trial — NOT YET IMPLEMENTED

Before a device write, independently audit the active FAP and E11 native-resource identity **again**, verify that PC backup/data snapshot remained intact and establish whether these reserved proposed device paths are absent:

- Existing active target: `/ext/apps/Tools/labmate.fap` (current, verified final v1.8)
- Preserve existing historical backup: `/ext/apps/Tools/labmate.e11-pre-final.bak` (**never overwrite or rename**)
- Proposed v1.9 candidate staging sidecar: `/ext/apps/Tools/labmate.v19-new-stage` (**must be absent** before creating; no blind retry)
- Proposed final v1.8 on-device backup: `/ext/apps/Tools/labmate.v18-final-before-v19.bak` (**must be absent** before any activation)

These **are design-only reserved paths**, not a claim that they exist or are safe to use. Do not use old v1.8 installation scripts for a v1.9 candidate (they pin a different size/hash/backup state). Review pinned Momentum CLI echo/Ready behavior, end-of-transfer responses, file MD5 and full file readback in a Windows offline simulator **before** writing any sidecar.

Proposed conditional sequence, each step requiring a fail-closed readback gate and new explicit operator authorization:
1. Confirm firmware/application/old-backup/resource identity, stage and v1.8-backup path ABSENT. Reject any unexpected file and keep current app running.
2. Write **only** the candidate to the new non-app sidecar; verify exact 97,540-byte content + checksum/readback, twice. A failed or short transfer leaves existing final v1.8 ACTIVE; **STOP**, preserve any partial stage as evidence, NO automatic cleanup/retry.
3. Only after staged bytes are fully verified, perform two specifically reviewed same-folder renames: original `labmate.fap` → new `labmate.v18-final-before-v19.bak`, then verified v1.9 sidecar → `labmate.fap`. The existing old E11 `.bak` is untouched. If interrupted between renames, normal app path may be absent; **STOP** and require fresh diagnostic evidence, no automatic rollback.
4. Re-open with read-only device state inspection, verify new FAP and all preexisting recovery artifacts, then obtain a separate go/no-go for first functional tests.

**Rollback plan (design only, not rehearsed):** Preserve the exact 81,528-byte final v1.8 file both on PC and reserved on-device location. Any rollback first requires new read-only classification of *all* active, stage and backup paths and a separate approved operation; do not auto-rename old paths or overwrite an existing `.bak`. Replacing the FAP alone does not guarantee complete firmware rollback. If the currently installed firmware ABI does not export an E11-required symbol, **do not install the candidate**.

## Initial physical check (after separate installation approval only)

1. With all GPIO leads removed, attempt first application launch and normal STOP/BACK; if the app cannot load or faults, STOP and preserve device evidence
2. Verify menus, retained CSV/History and profile S1 data **without editing or deleting existing files**
3. With only **3.3V-safe** signals and known PA7→PC1 loopback, validate Logic Scope / Signal Compare alongside 100 Hz and 1 kHz, duty ~50%; sanity-check time base, edge capture and stop/restart
4. Check PWM generation / Frequency Meter / Pulse Analyzer / Button Analyzer / Counter / UART regression and resource BUSY behavior; firmware-wide TIM2/SubGHz/RFID concurrency acceptance remains separately open

**No firmware flash, Momentum updater, user-data cleanup, SD reformat, merge to main, stable release or unattended background testing.**
