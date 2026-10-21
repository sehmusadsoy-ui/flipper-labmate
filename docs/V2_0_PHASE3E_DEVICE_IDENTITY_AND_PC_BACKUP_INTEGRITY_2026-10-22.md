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


## 2026-10-22 — Phase3D Windows PC-only trial copy prepared (owner report)

Owner confirmed a Linux `bash` command copied only the exact reviewed Phase3D E11 FAP to the Windows PC backups root under a NEW local subdirectory, read it back with `cmp`, and checked both old and new SHA-256 identities:

```text
V20 PC TRIAL COPY: PASS
V19 ROLLBACK SOURCE: PRESERVED
V20 FAP HASH: PASS
DEVICE WRITES: ZERO
NO FLASH / NO INSTALL
```

Candidate on PC: `C:\\Users\\sehmu\\Documents\\LabMate-FAP-PC-Backups\\V20-Phase3E-PC-ONLY-53afa54b\\labmate-v20-phase3d-trial.fap`.

Exact reviewed candidate: **115104 bytes**; SHA-256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`.

Live v1.9 backup stays in the separate protected `V20-Phase3E-current-v19-before-v20\\labmate.fap` folder; 101468 bytes; SHA-256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2`; the owner already confirmed the active-device MD5 matches this local file.

### Device stage safety nuance

The new FAP's repository `application.fam` still declares `appid="labmate"`, `name="LabMate"`, `fap_version="1.9"`. Merely giving the binary a different **filename** does NOT create a new unique app identity or isolate `/ext/apps_data/labmate`. App menu ambiguity and shared app data are possible when two LabMate FAPs coexist. The separate filename protects the currently installed app *bytes from path overwrite* but is not a fully independent/sandboxed test installation. A separate appid/data-root would require explicitly reviewed code/build changes and a NEW FAP hash, never silently reuse this exact Phase3D binary.

Before any attempted side-by-side device stage: obtain scoped explicit owner consent, check the exact destination filename does not exist by read-only `storage stat`, verify the qFlipper upload destination and existing `/ext/apps/Tools/labmate.fap` hash, and ensure the test plan does NOT claim shared SD data is isolated. qFlipper may overwrite files with identical names without warning (per vendor docs). Re-read candidate digest and live old app digest after transfer; do not auto-rename/delete/restore on an ambiguous result.

Current stage: **PC copy PASS; device trial upload not authorized or performed**.


## Phase 3E trial sidecar destination — real device READ-ONLY stat result

Owner provided a screenshot of the current Flipper Lab CLI on the E11-patched firmware (`HEAD mntm-dev d3f89dfe-dirty built on 16-10-2026`). Its read-only output is:

```text
>: storage stat "/ext/apps/Tools/labmate-v20-phase3d-trial.fap"
Storage error: file/dir not exist
```

**Interpretation:** The proposed exact sidecar pathname was absent at the time of this one read-only probe. This does not prove that the name will remain free at a future upload; check again immediately beforehand. No install, no file stage, no flash and no on-device rename have occurred.

**Device write authorization:** STILL PENDING. Require owner's explicit authorization for exactly one FAP upload as a *new* `/ext/apps/Tools/labmate-v20-phase3d-trial.fap`, preserving `/ext/apps/Tools/labmate.fap` and its previously matched 101468-byte backup. No implicit permission for launching, cleanup, rollback, firmware updates or profile/CSV writes. Both FAPs still use the same application ID `labmate` and storage namespace, so test launch is NOT isolated from the existing app data, and must be a separately reviewed decision.

## Owner authorization — one new sidecar FAP upload ONLY

In this conversation, following PC trial-copy SHA-256 PASS and read-only device `storage stat` confirming the destination was absent, owner explicitly replied **"Onaylıyorum."** to the narrowly scoped question authorizing upload of the new 115104-byte Phase3D candidate as a *separate device file*, not to replace current v1.9DEV.

**Authorized ONE operation:**
- PC source: `V20-Phase3E-PC-ONLY-53afa54b/labmate-v20-phase3d-trial.fap` (SHA-256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`)
- Remote NEW target: `/ext/apps/Tools/labmate-v20-phase3d-trial.fap`, only if still absent immediately prior to transfer.

**Not authorized:** rewriting `/ext/apps/Tools/labmate.fap`, rename, delete, firmware flash/update/reboot, executing the trial app, modifying existing `/ext/apps_data/labmate`, altering backups, reinstall/retry after an ambiguous transfer, or assuming two same-appid LabMate apps are isolated.

**Do not claim actual upload or device test PASS until the owner provides the results.** After the GUI file transfer, independently verify new target `storage stat` is 115104 bytes and its on-device MD5 matches the candidate PC copy. Check old `labmate.fap` stays 101468 bytes and MD5 `066f017c695bb5a17158a7b26c8f4838`. Device upload/verification currently **PENDING**.


## Owner-prepared Phase3D PC candidate: last pre-upload MD5 and SHA256 PASS

Owner ran `stat`, `md5sum`, `sha256sum` in WSL on the PC-only copy before carrying out the approved single new-file upload:

```text
SIZE: PASS
PC MD5:
7333aea05d157e915ee5a9c4de0a2296  .../labmate-v20-phase3d-trial.fap
PC SHA256:
53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737  .../labmate-v20-phase3d-trial.fap
```

**Pinned candidate on-PC:** 115104 bytes, MD5 `7333aea05d157e915ee5a9c4de0a2296`, SHA256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`. This is a local file verification ONLY, not a claim that the device now contains it.

**After separately approved qFlipper one-file upload:** independent Flipper CLI `storage stat` and `storage md5` must show the candidate path `/ext/apps/Tools/labmate-v20-phase3d-trial.fap` as size 115104 and MD5 `7333aea05d157e915ee5a9c4de0a2296`. The old `/ext/apps/Tools/labmate.fap` must remain size 101468 and MD5 `066f017c695bb5a17158a7b26c8f4838`. Abort on any mismatch; no retries, overwrites, deletes, renames, firmware flash or app launch. Device transfer and post-transfer readback are **PENDING** until owner provides their results.


## Phase 3E — Approved one-file microSD upload and post-upload independent CLI checks PASS

Owner uploaded the Phase3D trial via qFlipper under the exact NEW pathname. Subsequent Flipper Lab CLI screenshot shows:

```text
>: storage stat "/ext/apps/Tools/labmate-v20-phase3d-trial.fap"
File, size: 115104b
>: storage md5 "/ext/apps/Tools/labmate-v20-phase3d-trial.fap"
7333aea05d157e915ee5a9c4de0a2296

>: storage stat "/ext/apps/Tools/labmate.fap"
File, size: 101468b
>: storage md5 "/ext/apps/Tools/labmate.fap"
066f017c695bb5a17158a7b26c8f4838
```

**Trial transfer / device MD5 parity: PASS**, matching the owner’s PC-only 115104-byte candidate MD5 and SHA-256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`. **Existing active v1.9DEV FAP preserved:** 101468-byte MD5 unchanged and previously cross-checked against PC rollback copy SHA-256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2`.

**Authorization consumed:** The user approved only this one-file trial upload; this operation is now completed. No evidence of launch, app runtime, measurement tests, firmware flash, SD data migration or rollback. Both applications still use `appid="labmate"` and the same application data namespace, so trial launch is NOT an independent sandbox, even though FAP file byte paths are separate.

**Next decision:** Obtain a distinct informed approval for the first bounded **launch / UI-only smoke test**, preferably after checking current live `/ext/apps_data/labmate` coverage against saved data. No measurement generator, logger, profiles write, hardware pin rewiring, app install or firmware change under the upload consent. Do not assert v2.0 stable.


## 2026-10-22 — Separate owner consent for first trial UI-only launch

After owner-provided CLI `stat` and `md5` screenshots confirmed:
- New `/ext/apps/Tools/labmate-v20-phase3d-trial.fap`: **115104 bytes**, MD5 `7333aea05d157e915ee5a9c4de0a2296`.
- Existing `/ext/apps/Tools/labmate.fap`: **101468 bytes**, MD5 `066f017c695bb5a17158a7b26c8f4838`.

The owner separately replied **"pnaylıyorum"** to a direct request for permission to **launch only the new trial FAP for first-launch / UI-only smoke tests T01–T03**. Typographic spelling does not change the clear affirmative response.

Permitted scope: launch exact sidecar `/ext/apps/Tools/labmate-v20-phase3d-trial.fap` via a path-explicit loader; inspect root menu, MEASURE→Signal Doctor, source/reference controls and initial SET REF FIRST / NO SEALED DATA behavior; navigate BACK and exit. No GPIO/PWM/Logger/Profiles operation, capture/IRQ hardware manipulation, firmware install/flash, new SD file transfer, rename/delete or implicit consent for later metrology tests. Shared `appid=labmate` and data-root remains a known caveat; avoid all data-writing screens.

**Device launch and visible UI results are STILL PENDING**. The current owner approval is recorded as permission only, NOT PASS evidence. If launch fails, shows an unexpected version/menu, hangs, resets or creates a concerning state, STOP without retries.


## Phase3E T01 initial user observation — duplicate v1.9DEV label (unresolved identity)

After explicit authorization for an initial UI-only launch, the owner entered:

```text
loader open /ext/apps/Tools/labmate-v20-phase3d-trial.fap
```

Owner reported: the app opened, the Tools menu now shows two LabMate entries, and both display `v1.9DEV`. This does **not** establish that the new binary failed to launch: the development source intentionally leaves both `src/labmate_internal.h` `LABMATE_VERSION_TEXT "v1.9DEV"` and `application.fam` `fap_version="1.9"`, and the menu app name/ID is identical. As an acceptance discriminator, the actual Phase3D binary includes `Signal Doctor` in MEASURE and About's `16 tool guides`, whereas the previously installed app shows 15 tool guides. No T01/T02/T03 GUI PASS was supplied yet.

**Next authorized UI-only observation**: with the path-launched app open, inspect MEASURE for Signal Doctor and About for 16 guides; then BACK/EXIT. Do not issue more upload/rename/delete, metrology, firmware update or data writes. If both discriminators are missing, capture original CLI loader response and screenshot, classify T01 as FAIL, and pause troubleshooting without assuming either app path was run.


## Phase3E T01 — real-device development FAP launch confirmed; global UI polish outstanding

Owner confirmed on the physical Flipper after the path-specific trial launch:
- `About` displays **16 tool guides**.
- `MEASURE` includes **Signal Doctor**.
- The label still says **`v1.9DEV`**.
- The overall presentation is visually the **old LabMate UI**, not the promised application-wide v2.0 professional design.

**Assessment:** T01 app identity / menu presence **PASS** for the Phase3D candidate. This uniquely distinguishes it from the formerly installed 15-guide v1.9 build. This does not imply successful Pulse/Frequency diagnosis, T02/T03 controls, device resource stress, or stable acceptance.

**Outstanding v2.0 commitments:** change manifest and About version coherently to `v2.0DEV` in a future separately built artifact (current candidate SHA must remain pinned); complete consistent polished UI across tools, not merely add the Doctor screen; run geometry and on-device screenshot review. **Visual design acceptance remains PENDING/NOT MET.** No current device file changes authorized beyond the already completed one-file sidecar upload. No firmware flash.

**Next authorized observation:** open the already running Signal Doctor page, inspect initial `SET REF FIRST`, reference controls and second page without using measuring/generator/logger/profile hardware/data operations. Close with BACK. If unexpected display or glitch, capture screen and STOP.


## Phase3E T02 — physical 128x64 Doctor screen screenshots: operational navigation, visual FAIL

Owner uploaded **two Flipper LCD screenshots** from the path-launched Phase3D 115104-byte sidecar FAP. Observations:
- `DOCTOR` header, `1/2` badge, `SRC FREQ`, `REF 0Hz x1` and `F TOL 5.0%` visible.
- First screenshot highlights `SRC`, second highlights `REF` after right navigation. **Field selection works** in this limited observation.
- Bottom advisory `SET REF FIRST` is visibly crossed by the horizontal footer rule. This is a **confirmed UI geometry FAIL**: older production `src/labmate_doctor_screen.c` had status text baseline **y=52**, and shared `src/labmate_ui_layout.h` uses `LABMATE_UI_FOOTER_RULE_Y=52`.
- No `100Hz` reference or `NO SEALED DATA` result appears in these two screenshots, so **T03 is PENDING**.
- On-device `2/2` page, BACK/exit and all capture metrology are also still pending from these specific screenshots.

**Source corrective action** in commit `e11192a18e5b47713a37c0281fc821a6780afd23` on **development branch only**:
- New `src/labmate_doctor_layout.h` centralizes safe 128x64 row baselines **22,31,40**, status baseline **50**, and checks relation to the unchanged y=52 shared footer divider.
- `src/labmate_doctor_screen.c` uses the constants for both pages and status; no evaluator, HAL, IRQ, SD, capture or input logic changed.
- Added `tests/test_v20_doctor_layout.c` layout/status regression, run by `scripts/test-v20-phase3b-doctor-panel-host.sh` under GCC and Clang in the next full host gate.
- Corrected the **NEXT candidate** source label to `v2.0DEV` and manifest `fap_version="2.0"`, updating E11 source preflight, native verifier and compile-only CI version assertions accordingly.

**Strict acceptance boundary:** This commit changes the GitHub source, NOT the already installed/trusted Phase3D FAP (115104 bytes; SHA-256 `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`). No new E11 FAP/host runtime results yet for the corrected source. Do not falsely carry forward the old PASS/hash or claim the physical UI is fixed. Any new FAP upload or app launch requires a fresh scoped procedure/consent. Global v2.0 UI redesign remains outstanding; this targeted change only repairs the demonstrated footer collision and version identity.
