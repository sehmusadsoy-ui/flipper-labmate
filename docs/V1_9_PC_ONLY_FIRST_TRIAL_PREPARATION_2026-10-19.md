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


## 2026-10-19 — actual COM7 read-only device prewrite PASS

The operator ran the 12 synthetic tests in `tests/test_v19_e11_device_prewrite_ro.py` and reported `Ran 12 tests in 0.002s`, `OK`. They then executed `run-v19-e11-device-prewrite-ro.ps1 -Port COM7`, which reported:

```text
PINNED LOCAL HELPERS: 13/13 GIT BLOBS PASS
device_firmware_identity: PINNED_E11_LABEL_BASE_AND_RESOURCE_MD5
active_app: V18_FINAL_MD5_SIZE_PASS
prior_v18dev_device_backup: PINNED_MD5_PASS
v19_reserved_paths: BOTH_ABSENT_TWICE
old_e11_backup_preserved: YES
device_writes: NONE
v19_installed: NO
PC_LABMATE_DATA_BACKUP: VERIFIED (12 files, 2128 bytes)
V19 E11 DEVICE PREWRITE READ-ONLY PASS
NO DEVICE WRITES. INSTALL STILL REQUIRES NEW EXPLICIT CONSENT.
```

This establishes the two exact proposed new staging/backup SD paths were absent **at the time of the read-only scan** and that the current installed v1.8 identity and older protected E11 sidecar matched. It does NOT authorize any write, attest the internally flashed firmware image by SHA256, or prove that the paths will stay absent later. Re-run an independent identity/absence preflight immediately before any later authorized device-side staging; do not blindly retry a failed operation.


## Offline FAP-only promotion and manual rollback state-machine simulator — REVIEW ONLY

Source: `scripts/simulate_v19_e11_fap_swap_offline.py`. Fault-injection tests: `tests/test_v19_e11_fap_swap_offline.py` (**25/25 real operator-executed synthetic tests PASS on 2026-10-19; 0.003s; `OK`**). This virtual simulator imports no serial/COM Flipper transport, creates no files and performs no device calls. It reads only the three byte-pinned candidate and existing PC FAP backups; **it never writes anything**.

The state machine proves in-memory classification for:

- original FINAL v1.8 ACTIVE, **new** staged v1.9 VERIFIED with original v1.8 still ACTIVE;
- first rename original v1.8 → separately reserved exact v1.8 backup (app temporarily absent), then second rename verified v1.9 stage → ACTIVE;
- fault before stage's Ready response, short first chunk, wrong staged SHA, occupied stage, occupied recovery backup, unexpected or mutated legacy E11 backup; **STOP with old ACTIVE preserved**, no cleanup/retry;
- specifically requested **manual recovery** from first-rename interruption: only after exact between-renames classification, put retained v1.8 from reserved backup back at the absent active path, while keeping new v1.9 stage;
- specifically requested **manual rollback** after success, using **an additional dedicated absent path** `/ext/apps/Tools/labmate.v19-failed-before-rollback.bak`: first v1.9 active → failed backup; second retained v1.8 backup → absent active. Both steps are deliberately separate with a manual STOP state in between, and both original 1.8 / 1.8DEV backups must survive. **No real rollback tool has been created, tested or approved.**

The **fifth** path for a hypothetical future rollback has NOT been stat-checked on the real device, and is NOT approved for use. Future real device stage/promote/rollback scripts need completely separate reviews, precise CLI protocol/SDK ABI checks, simulated readback and explicit distinct operator approvals. The Windows/Flipper real storage implementation does not gain safety guarantees from this in-memory simulator alone.

Run first the 25 synthetic tests; if PASS, simulate using real PC-protected FAP bytes in WSL:

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/tests/test_v19_e11_fap_swap_offline.py -v
python3 /mnt/c/Users/sehmu/labmate-src-v19/scripts/simulate_v19_e11_fap_swap_offline.py \
  --candidate ~/labmate-build/v19-pc-only-prepared-3d66658/labmate-v1.9DEV-E11-PC-ONLY.fap \
  --current-v18-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482/installed_LabMate_v18_FINAL_E11_before_v19.fap \
  --legacy-e11-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d/installed_E11_v18DEV_before_final_label.fap
```

**Current status: device v1.9 NOT INSTALLED, no device write authorized.** Draft PR #15 / Stable v1.8 unchanged.


## 2026-10-19 — actual real-artifact FAP staging and manual-rollback simulator PASS

The operator used all **three actual SHA-pinned artifacts** (the prepared **97,540-byte** v1.9 E11 FAP, the real-device-readback **81,528-byte** final v1.8 FAP, and separately preserved **81,532-byte** older v1.8DEV E11 backup) as inputs for `scripts/simulate_v19_e11_fap_swap_offline.py`. Their reported output:

```text
CLEAN_STAGE: PASS
INTERRUPTION_AFTER_FIRST_RENAME: STOP_PRESERVES_STAGED_V19_AND_V18_BACKUP
CLEAN_VIRTUAL_PROMOTION: PASS_WITH_V18_AND_LEGACY_BACKUPS
MANUAL_GAP_RECOVERY_MODEL: PASS_ONLY_WITH_SEPARATE_CONSENT
MANUAL_VIRTUAL_ROLLBACK_MODEL: PASS_ONLY_WITH_SEPARATE_CONSENT
BAD_READY: FAIL_CLOSED_OLD_V18_ACTIVE
SHORT_WRITE: FAIL_CLOSED_OLD_V18_ACTIVE
STAGED_SHA_MISMATCH: FAIL_CLOSED_OLD_V18_ACTIVE
NO_BLIND_STAGE_RETRY: PASS
V19 VIRTUAL STAGE/TWO-RENAME AND MANUAL ROLLBACK MODELS: PASS
USB_CALLS: ZERO; DEVICE_WRITES: ZERO; PC_WRITES: ZERO
REAL COM WRITE TOOL / REAL DEVICE TRIAL: NOT AUTHORIZED OR EXECUTED
```

This upgrades the previous synthetic-only FAP state-machine result to a **real PC artifact input** simulation; it remains a pure-memory transition model. It does not establish that the pinned Momentum storage CLI will behave correctly while writing the card, or that an actual v1.9 rollback can be performed safely.

## Additional offline native-CLI protocol fixture — operator-reported 28/28 PASS

`scripts/simulate_v19_e11_storage_cli_offline.py` and `tests/test_v19_e11_storage_cli_protocol_offline.py` (28 distinct synthetic cases) model the concrete legacy E11 `storage stat`, `storage write_chunk`, native command echo / `Ready` / result framing, 4096-byte append chunks, post-transfer MD5 and full binary readback, plus **two non-atomic same-folder renames** in an entirely in-memory fake transport. The fixture intentionally imports no serial/Flipper transport, offers no real-device entrypoint and writes nothing to the PC. Test cases include short write, incorrect Ready, ambiguous first/second rename result, changed staged bytes, occupied backup, old v1.8/legacy E11 backup corruption, blocked retry and forbidden target paths.

After all **28 offline tests** pass, run the memory-only mock command using the three existing hash-pinned PC FAPs:

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/scripts/simulate_v19_e11_storage_cli_offline.py \
  --candidate ~/labmate-build/v19-pc-only-prepared-3d66658/labmate-v1.9DEV-E11-PC-ONLY.fap \
  --current-v18-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482/installed_LabMate_v18_FINAL_E11_before_v19.fap \
  --legacy-e11-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d/installed_E11_v18DEV_before_final_label.fap
```

The command must conclude `REAL-FAP INPUT MOCK NATIVE CLI E11 STAGE/TWO-RENAME: PASS`, `USB_CALLS: 0 | DEVICE_WRITES: 0 | PC_WRITES: 0` before considering further work. The **28 synthetic unit tests were actually executed** by the operator on Ubuntu/WSL and reported `Ran 28 tests in 0.010s`, `OK`. The separate **three-real-FAP input mock run** is still pending; do not claim its PASS before operator output.

The **mock state machine is not evidence of device-side FAT atomicity or transport implementation**. It is only an offline safeguard to catch our orchestration mistakes before deciding whether to author/review any real-device write tool. Real source inspection, exact installed E11 ABI compatibility and rollback-specific independent read-only state classification are still required. **No device write or firmware operation authorized.**


## 2026-10-19 — real-FAP native CLI in-memory simulator PASS (operator)

The operator ran `scripts/simulate_v19_e11_storage_cli_offline.py` against all THREE actual hash-pinned FAPs (v1.9 local 97,540 bytes; installed v1.8 final PC readback 81,528 bytes; historical original E11 v1.8DEV 81,532 bytes). They reported:

```text
V19 E11 IN-MEMORY CLI PROTOCOL FIXTURE (NO DEVICE OR DISK WRITES)
MOCK_STAGE: PASS
MOCK_RENAMED_TO_V18_BACKUP: PASS
MOCK_V19_ACTIVATION: PASS
MOCK_ORIGINAL_E11_PRESERVED: PASS
MOCK_CHUNKS: 24
MOCK_RENAME_COUNT: 2
REAL-FAP INPUT MOCK NATIVE CLI E11 STAGE/TWO-RENAME: PASS
USB_CALLS: 0 | DEVICE_WRITES: 0 | PC_WRITES: 0
Firmware ABI attestation and real device write remain NOT AUTHORIZED.
```

This is another in-memory model using actual PC FAP bytes, NOT an actual USB write, firmware symbol lookup, or tested rollback on physical FAT. All original PC backup identities remain preserved.

## 2026-10-19 — proposed NEW **stage-only** device writer — UNTESTED / NEVER RUN

A limited review candidate is available at `scripts/stage_v19_e11_sidecar_only.py`; host tests at `tests/test_v19_e11_sidecar_stage_only.py` (**21/21 operator-executed synthetic offline tests PASS — 2026-10-19, 0.025s, `OK`**).

The proposed script is **capable of writing to the Flipper's SD card** if explicitly invoked later. It requires an exact separate authorization string and is **NOT AUTHORIZED BY EXISTING CONVERSATION CONSENT**. Do NOT invoke the stage script or give the authorization string in an operator-facing command yet. The ONLY permitted device write, *once it separately passes mock tests, native SDK/protocol review, source hash pinning and explicit operator approval*, would be append-chunks to a **new, previously ABSENT** non-`.fap` sidecar `/ext/apps/Tools/labmate.v19-new-stage`. It does **not** rename/overwrite/activate the current final v1.8, alter LabMate CSV/Profiles or flash firmware.

Before any potential stage it re-verifies existing active final v1.8, previous E11 native JS/Manifest and historical E11 device backup, all three PC backup sources, and both proposed stage and dedicated-v1.8 backup paths ABSENT twice. After potential stage it verifies the NEW file's exact size, device MD5 and TWO complete binary SHA256 readbacks; re-verifies active v1.8/native resources and unchanged reserved v1.8 backup path. A failed or ambiguous write causes STOP, leaving any partial sidecar alone, with absolutely no automatic retry, rename, remove, cleanup or rollback.

The reviewed synthetic `FakeCLI` tests cover echo/Ready drift, partial write, wrong tail, corrupt remote MD5/readback, occupied paths, changed old active/native identity, wrong candidate SHA, duplicate stage attempt, CLI-path allowlist, and missing authorization. **Do not claim test PASS until actually run.**

A separately designed **activation tool**, separate manually authorized rollback tool, independent SDK symbol/image attestation and a host replay using the exact native CLI transport implementation remain outstanding. Stage-only work does not imply v1.9 installation readiness. Existing version 1.8 and published Stable remain unchanged.


## 2026-10-19 — direct stage-only implementation replay (new independent offline gate)

After the operator executed all **21/21 synthetic tests PASS** on `tests/test_v19_e11_sidecar_stage_only.py`, we added:

- `scripts/replay_v19_e11_real_fap_stage_offline.py` — directly calls `stage_v19_e11_sidecar_only.stage_only()` with the three exact archived PC FAPs and the existing in-memory `FakeCLI`. This deliberately tests the **actual stage-only orchestration**, rather than only the earlier separate conceptual model. Calls to *remote-native resource attestation* are mocked because the fake does not contain device_info; actual initial E11 read-only device attestation is independently PASS. The stage's stat, echo, 24 write_chunk/Ready exchanges, binary replay, MD5, full readback, and after-stage v1.8 unchanged checks execute on FakeCLI without PC/device writes. **This is not a full integration test with the real serial SDK.**
- `tests/test_v19_e11_real_fap_stage_offline_replay.py` — 12 synthetic boundary/negative tests against that direct-code replay, **operator-reported 12/12 PASS on 2026-10-19 (0.004s, `OK`)**.

Run the unit suite first and STOP on any failure:

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/tests/test_v19_e11_real_fap_stage_offline_replay.py -v
```

Only if all **12/12 pass**, run the independent real-PC-FAP-memory-replay command:

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/scripts/replay_v19_e11_real_fap_stage_offline.py \
  --candidate ~/labmate-build/v19-pc-only-prepared-3d66658/labmate-v1.9DEV-E11-PC-ONLY.fap \
  --current-v18-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482/installed_LabMate_v18_FINAL_E11_before_v19.fap \
  --legacy-e11-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d/installed_E11_v18DEV_before_final_label.fap
```

**No operator result is claimed in advance.** The standalone, dangerous real USB stage-only writer **MUST NOT be run** until a new, separately reviewed and explicitly authorized stage-only operation. Its use is NOT part of either of these offline commands. A successful offline replay will not imply native firmware ABI hash attestation or authorization to replace the active v1.8.


## 2026-10-19 — actual three-FAP direct stage-only code offline replay PASS

The operator ran `scripts/replay_v19_e11_real_fap_stage_offline.py` on the exact three verified PC artifacts after **12/12 synthetic replay unit tests PASS** (0.004s). User-provided output:

```text
V19 E11 REAL-FAP STAGE-ONLY REPLAY - IN MEMORY / NEVER DEVICE
FAP_CANDIDATE_BYTES: 97540
FAP_CANDIDATE_SHA256: e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90
STAGE_CHUNKS: 24
STAGE_ONLY_FULL_READBACK_TWICE: PASS
ACTIVE_FINAL_V18_UNCHANGED: YES
LEGACY_E11_BACKUP_UNCHANGED: YES
RENAME_ATTEMPTS: 0
REAL_FAP_ACTUAL_STAGE_CODE_OFFLINE_REPLAY: PASS
USB_CALLS: 0 | DEVICE_WRITES: 0 | PC_WRITES: 0
NATIVE_E11_FIRMWARE_ABI: NOT_ATTESTED | INSTALL: NOT_AUTHORIZED
```

Unlike the earlier virtual promotion model, this replay exercises the actual code that would stage a new non-app sidecar later. The on-device ABI remains un-attested at binary level; no FAP installation or COM stage has occurred. The 21 stage-only and 12 direct-code-replay offline suites and the actual PC backup hashes have now been checked by the operator.

Next stage is Windows PC-only candidate transfer/integrity verification and independent host review of *any* authorized command that might later write ONLY one fresh sidecar. The final-v1.8 app, original E11 device backup, data snapshot, firmware and installed app remain untouched. **No stage-only device write is authorized by these results.**


## Windows-side FAP candidate handoff — PC ONLY / operator action pending

Files:
- `scripts/copy_v19_e11_candidate_windows_pc_only.py` — WSL-local-to-Windows-mounted PC-only verified candidate copy;
- `tests/test_v19_e11_windows_pc_copy_only.py` — nine **offline tests: operator-reported 9/9 PASS on 2026-10-19 (0.011s, `OK`)**.

The tool first re-hashes the WSL candidate and all three preserved PC backup/snapshot roots. It only creates a NEW direct child `V19-WINDOWS-PC-CANDIDATE-...` of the original verified `/mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups` root. It rejects existing paths and symlinked sources. It writes a single reviewed FAP copy, provenance JSON, completion marker and checks the copied bytes from the Windows-mounted filesystem. Interrupted PC copies retain an incomplete guard; no overwrite/auto retry. Its output has no USB/COM device access and requires no Flipper connection.

This is **not a Flipper SD staging operation**; separate source hashing/Windows native wrapper review and a newly explicit device-write authorization are necessary for any subsequent sidecar upload. The artifact hash remains `e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90`. No new v1.9 build is requested or needed.

Run the nine unit tests first:

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/tests/test_v19_e11_windows_pc_copy_only.py -v
```

Wait for their actual result before invoking any PC-copy action. Do not run the real Flipper stage-only program or promote/flash firmware.


## 2026-10-19 — real Windows-mounted PC candidate copy PASS (operator)

The operator executed `scripts/copy_v19_e11_candidate_windows_pc_only.py` on the actual pinned WSL FAP, into a **new Windows-only PC folder** after 9/9 synthetic unit tests PASS, and reported:

```text
V19 E11 WINDOWS PC-ONLY TRANSFER - NO COM/DEVICE OPERATIONS
status: V19 WINDOWS PC-ONLY CANDIDATE COPY PASS
candidate_file: /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/V19-WINDOWS-PC-CANDIDATE-3d66658-20261019/labmate-v1.9DEV-E11-WINDOWS-PC-ONLY.fap
candidate_bytes: 97540
candidate_sha256: e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90
backup_files_verified: 12
backup_bytes_verified: 2128
device_writes: NONE
firmware_flash: NONE
install_authorized: NO
```

**PC handoff is closed PASS**; both original existing v1.8/v1.8DEV PC FAP backups and current 12-file LabMate data snapshot still verify. This is *not* the entire microSD and not a restore rehearsal. The stage-only writer remains unexecuted. Real on-device v1.9 APP ACTIVE = NO; v1.8 remains installed. Draft PR #15; published v1.8 immutable.

**Next permission decision:** only if separately authorized, consider writing the new **non-.fap** staging sidecar `/ext/apps/Tools/labmate.v19-new-stage`; do not promote, rename the active `labmate.fap`, flash firmware, or touch any backups. This is a genuine microSD device write and must have an independent exact-command Windows transport provenance review and fresh same-session live preflight. Regardless of stage outcome, no v1.9 activation without separate installed E11 SDK ABI compatibility and an independent express permission.


## 2026-10-19 — first PHYSICAL stage-only authorization scope

The operator explicitly approved **starting only the first device-side stage process** after a full PC FAP-copy PASS. Authorization applies solely to writing the verified **97,540-byte** v1.9 E11 candidate to the NEW, currently absent **non-app staging filename** `/ext/apps/Tools/labmate.v19-new-stage`, and only after current-session identity/absence and local helper/transport integrity gates pass. This approval **does not permit** changing the active `/ext/apps/Tools/labmate.fap`, renaming any file, deleting an incomplete stage, overwriting old backups, modifying user CSV/Profiles, flashing firmware, restoring, or performing an unattended retry. Firmware ABI attestation for activation remains open. Operator has **not yet run the stage**.

A new `scripts/run-v19-e11-stage-only.ps1` has been added. **DEFAULT IS DRY-RUN**, which tests PC-only provenance: 14/14 exact Git SHA-1 blobs (independently retrieved GitHub inventory PASS), exact pinned upstream Momentum d3f89dfe `scripts/flipper/storage.py` Git blob `0182cf45fa8ff254e31da6a1d059d570badb816e`, approved Windows-only candidate FAP SHA-256/size and data/backups. The `-ApplyStageOnly` flag (NOT recommended until the dry-run reports PASS and operator sends its output) independently reruns the PC verification and launches the approved single-sidecar stage-only code with that consent scope. Stage code itself performs fresh **same-COM-session** dual E11 live FAP/native resource identity and two absent path screens BEFORE any 4096-byte chunk write, then full binary double readback. Failure leaves stage on SD exactly as-is, stops, with **NO auto retry/rollback**.

Static structural tests `tests/test_v19_e11_stage_only_windows_runner_static.py` (10 synthetic source tests, **operator execution pending**) validate default dry-run, single stage writer, tight COM7/pinned helper/transport gates, Windows FAP integrity, and absence of backup-clobber/activation commands. Real wrapper hasn't run on Windows, and any actual COM stage result must be reported separately.

**Next steps, one gate at a time**: Git pull, run 10 static tests, run Windows wrapper DEFAULT (NO `-ApplyStageOnly`), examine results and fix any unmet prerequisite. Only then run the exact separately approved `-ApplyStageOnly` command once with connected idle Flipper, qFlipper shut down and no GPIO leads. If ANY error appears, never blindly rerun (sidecar state uncertain); perform read-only classification before a new decision.

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/tests/test_v19_e11_stage_only_windows_runner_static.py -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '& "$env:USERPROFILE\labmate-src-v19\scripts\run-v19-e11-stage-only.ps1" -Port COM7'
```

No device-write command is provided in this document prior to actual dry-run success and exact command verification. Stable/public v1.8 and custom firmware remain frozen; v1.9 draft PR #15.


## 2026-10-19 — Windows PowerShell pre-stage PC dry-run argument quoting FIX

The operator reported the **10/10 static Windows wrapper tests PASS** (`0.006s`, `OK`). They then ran `scripts/run-v19-e11-stage-only.ps1 -Port COM7` **without** `-ApplyStageOnly`, and the wrapper stopped at its preliminary Windows PC-only Python backup check:

```text
File "<string>", line 1
print(PC_BACKUPS_PASS:,n,files,,b,bytes)
SyntaxError: invalid syntax
Actual backups changed. NO COM.
```

**Root cause:** PowerShell's native argument quotation removed the intended double quotes inside `py -c` Python code; this was a **code invocation bug, not evidence of changed backup files**. No COM device access was attempted, no Flipper microSD writes, no stage or install, and the backup verification did not run to completion.

**Correction:** `scripts/check_v19_e11_pc_backups_windows_ro.py` is an independently pinned fifteenth Python helper that invokes the existing read-only `verify_backups` on three exact PC snapshot folders. The PowerShell wrapper now launches that verified **.py file** with an argument array instead of `-c`, eliminating Windows quote-loss ambiguity. All fifteen Python helper Git blobs and the upstream H0 `flipper/storage.py` Git blob must match before the PC dry run or any stage. New unit guard `tests/test_v19_e11_stage_only_windows_runner_static.py` expects **11 tests**, including rejection of a reintroduced `'-c'` path. Newly added independent helper/wrapper/test Git content checks were performed on GitHub; **neither the revised suite nor real Windows dry-run is yet operator-executed**.

Next: pull `dev/v1.9-logic-scope`, run **11** static host tests, then rerun exactly the **no-switch dry run**:

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/tests/test_v19_e11_stage_only_windows_runner_static.py -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '& "$env:USERPROFILE\labmate-src-v19\scripts\run-v19-e11-stage-only.ps1" -Port COM7'
```

Expected dry-run evidence: `PC_BACKUPS_PASS: 12 files, 2128 bytes`, `WINDOWS_PC_BACKUPS_RO: PASS`, `V19 E11 LOCAL HASH / TRANSPORT PRE-STAGE GATE: PASS` and `DRY RUN ONLY - ZERO COM / DEVICE WRITES`. **STOP on any error and do not invoke `-ApplyStageOnly` until the user reports an actual corrected dry-run PASS**, despite their previously granted limited permission. Authorization scope unchanged: at most one fresh non-app stage sidecar; no active `labmate.fap` rename, deletion, firmware flash, backup overwrite or automatic retry.
