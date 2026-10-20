# LabMate v1.9DEV — Local E11 FAP review build evidence (2026-10-19)

**Status: LOCAL BUILD / FORMAT + SOURCE-SDK CHECK PASS, DEVICE INSTALL NO-GO.** This is a transcription of the developer's **actual WSL2 terminal output** reported in the LabMate project conversation. The assistant has not independently retrieved the binary or reproduced the run. It is not a GitHub Actions attestation, firmware update authorization, or v1.9 release.

## Exact input and toolchain

- LabMate source commit **`3d66658dad6e09df9c011a91a78881bcc16eb25b`** on `dev/v1.9-logic-scope`. This exact source SHA is immutable for the built artifact, even if documentation commits later advance the development branch.
- Momentum source commit **`d3f89dfe2ef6b01839201598e9be1590cba80322`**; previously audited E11 native lease/IRQ patch chain was applied to the local source tree (not to a device).
- Local build host: WSL2 Ubuntu x86_64; GCC/G++ 15.2.0, Python 3.14.4, `./fbt fap_labmate`.
- GitHub Actions did **not** run: account-level Actions dispatch was blocked, and no associated run/artifact was observed. Local evidence must not be called CI PASS.
- Local Python verifier suites, run before the build: `test_verify_v19_e11_sdk_fap.py` **6/6 OK**; `test_check_v19_review_bundle.py` **11/11 OK**.
- E11 patch/test script initially stopped under GCC 15 due to deprecated C++17 `<cstdbool>` included under `-Werror`. Fixed in source commit `05607b1`, then remaining checks finished with `E11 SOURCE PATCH PARITY PASS`, `E11_RESUME_EXIT=0`.
- First FAP build failed under strict enum comparison warnings in scope display and reference-view code. Two source files were updated; final source commit is `3d66658`. Retried build completed `LINK`, `APPMETA`, `FAP`, `FASTFAP`, `APPCHK`, `FBT_EXIT=0`.
- External Momentum app manifest warnings (appid `.cli_gui`, `.f0_mtp`) appeared but did not stop this targeted FAP build. No full patched firmware build/test is claimed.

## User-reported read-only binary checks

The exact command `python3 labmate/scripts/verify_v19_e11_sdk_fap.py momentum-src momentum-src/build/f7-firmware-C/.extapps/labmate.fap` reported:

```text
V19 E11 SDK EXPORTED-API/FAP REVIEW PASS | bytes=97540 | sha256=e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90
REVIEW ONLY — NO DEVICE WRITES OR FIRMWARE INSTALLATION
```

The developer created the local review ZIP in WSL2:

- FAP SHA-256: `e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90`
- Local ZIP path: `/home/adsoy/labmate-build/v19-local-review-3d66658.zip`
- ZIP SHA-256: `2161804ab0939110d79db861106569ea6f20262a20d0578491c40f513b4926f3`
- Reported result: `labmate-v1.9DEV-E11-review.fap: OK`, `V19 LOCAL REVIEW PACKAGE: PASS`.
- Local `PROVENANCE.txt` deliberately uses `BUILD_MODE=LOCAL_WSL2`, `GITHUB_ACTIONS_RUN=NONE`, and records the patched source diff SHA-256; it **does not** assert a nonexistent GitHub Actions run. The GitHub Actions-specific four-file bundle verifier requires a numeric `GITHUB_RUN_ID` and **was not run** on this local ZIP. Locally, FAP hash and ZIP file entries/readability were checked separately. No independent signing/attestation was performed.

**Do not confuse successful matching-source SDK and ELF checks with ABI compatibility of the firmware already installed on a particular Flipper.** The patched E11 firmware ABI used to link the external FAP was not installed or verified on the user's device during this session.

## Installed firmware display — 2026-10-19 (read-only)

The operator supplied a screenshot of Flipper firmware info showing **Momentum mntm-dev [6-10-2026]**, abbreviated base commit **`d3f89dfe`**, and SDK/API **`87.1`**. The abbreviated commit matches the first eight characters of the pinned E11 source base, and the API version matches that unpatched source. **Neither the commit string nor the 87.1 SDK label establishes that the installed firmware includes the E11 resource-lease and nonasserting GPIO callback ABI patches.** Custom firmware compiled on the same base could report those same identifiers.

A read-only authenticated GitHub retrieval of **`Next-Flip/Momentum-Firmware` at exact original commit `d3f89dfe2ef6b01839201598e9be1590cba80322`**, file `targets/f7/api_symbols.csv` (unmodified upstream), confirms that its API 87.1 list contains **none** of these E11-only FAP imports:
- `furi_hal_resource_lease_try_acquire`
- `furi_hal_resource_lease_release`
- `furi_hal_gpio_try_add_int_callback`

Therefore, **if the installed firmware is a normal/unpatched Momentum d3f89dfe build, this v1.9 FAP is NOT ABI-compatible**. Installed patch provenance is currently unknown; do not infer stock vs custom from the screenshot alone. Keep device install NO-GO pending exact installed firmware symbol/patch evidence. Do not flash firmware to overcome this gate without a separate, verified backup and explicit approved plan.

## Historical E11 deployment recovered — correction to screenshot-only uncertainty

The operator correctly recalled that an **E11 full firmware update was actually installed** while completing I2C Explorer and 1-Wire Temp. This is supported by the project's earlier records, not just inferred from the screenshot:

- `docs/V1_8_E11_FIRST_LIVE_BOOT_AND_SMOKE_2026-10-17.md`: first **operator-authorized FULL E11 trial**, pinned source `ba379f20fb29369501e1057f570a911f71ac83f8`, Actions `#38966248325`; **read-only COM7 check** reported installed firmware label/base, FAP, native JS GPIO module and installed resource Manifest match the pinned E11 build, with later real-device functional rounds.
- `docs/V1_8_E11_FINAL_RELEASE_GATE_2026-10-17.md`: an **FAP-only v1.8 final-label replacement** was later tested on this *already installed* custom E11 firmware. Actual 100 Hz / 1 kHz loopback and STOP/RESTART evidence is recorded there.
- `docs/V1_8_E11_RELEASE_READINESS_2026-10-17.md`: independently logged original matched patched E11 source diff SHA-256: **`1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80`**.
- Authenticated GitHub compare, deployed v1.8 source `ba379f20` → v1.9 built source `3d66658`, reports **no changed `scripts/patch_momentum_*.py` files**. Exact blob SHA reads of five critical patch scripts (timed I2C, resource lease, try-add GPIO, native JS lease, SubGHz status bridge) also match between those commits.

**Corrected interpretation:** The operator's installed firmware is backed by historical actual custom-E11 deployment evidence. A hypothetical claim that it *must* be unpatched stock firmware is incorrect. However, the **screenshot by itself** proves only the base commit/API label, not firmware-image bytes or the full custom ABI. Historical readback of matching app/plugin + unchanged patch-source files greatly increases confidence, but does not automatically attest the currently running image after possible later actions.

## Final historical E11 patch fingerprint check — 2026-10-19 PASS

The operator ran a read-only local comparison of the **45 pathspecs** extracted verbatim from `.github/workflows/check-v18-final-label-review-pair.yml` using `git -C momentum-src diff -- <paths>`. Under local Git 2.53.0, the initial digest differed from the older workflow's documented result. A follow-up using **`git -c core.abbrev=7 -C momentum-src diff -- <paths>`**, preserving the exact legacy pathspecs, returned:

```text
GIT VERSION: git version 2.53.0
ABBREV=7: 1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80
HISTORICAL PATCH HASH: PASS
```

This **matches the historical matched E11 final-label firmware source diff SHA-256 exactly**. The `core.abbrev` parameter controls the abbreviated object IDs embedded in unified Git diff headers, and the old and new default outputs were not byte-identical until the historical 7-character abbreviation was selected.

**Result: historical firmware source-diff parity PASS** for the inspected, allowlisted tracked files. The local review ZIP's independent `PATCH_DIFF_SHA256=a0cc3040a9ef41897f3c3d1cd9414e1d7aeb8dfae69244d3d782c88a5cb7ea90` still correctly refers to its own *whole-tree binary diff* and must not be rewritten or falsely labelled as the historical digest. The two provenance fields measure different byte sequences. The FAP and ZIP SHA-256 bytes remain unchanged, and **there is no need to rebuild or repackage** solely for this confirmation.

This is **source parity**, not an independent readback hash of the installed firmware and not installation authorization. Continue with read-only current firmware/FAP identity and exact installed-app backup verification, then separately request operator authorization for any new v1.9 FAP-only replacement. Preserve Stable v1.8 and the installed patched E11 firmware; no updater, flash or SD cleanup.


## Device gate remains closed

Before any FAP-only installation, determine the currently installed firmware build/version and **independently verify its exported APIs** (including `furi_hal_resource_lease_try_acquire`, `furi_hal_resource_lease_release`, `furi_hal_gpio_try_add_int_callback`) against the binary's required SDK ABI. A firmware version string alone is insufficient. If incompatible or unknown, **NO INSTALL**; do not flash firmware automatically as a workaround.

Before any later separately authorized FAP-only trial, independently back up and verify the old v1.8 FAP, SD card `apps_data`, Profiles/S1 and CSV logs; establish the exact FAP replacement and rollback path; maintain 3.3V-only GPIO/PA7→PC1 safety. Full physical scope 100 Hz / 1 kHz, START/STOP/BACK, A/B, legacy-tool regression and firmware-wide native TIM2/SubGHz/RFID concurrency remain unresolved for v1.9.

The development PR should remain **Draft**, stable v1.8 preserved. No flash, updater, SD cleanup or release was performed.


## 2026-10-19 — REAL COM7 installed v1.8 final-FAP readback + independent PC backup PASS

The operator first executed `scripts/run-v18-e11-phase2b-state-readonly.ps1 -Port COM7` (after the pinned local 10/10 helper-blob fallback fixed a private GitHub raw URL 404). The actual device reported `state: AFTER_PROMOTION`, `old_E11_FAP_preserved: PC_BACKUP_AND_DEVICE_BAK`, `new_v18_FAP: ACTIVE_MD5_AND_SIZE_PASS`, `firmware_JS_gpio_eventloop_manifest: PINNED_MD5_AND_LABEL_MATCH` and `device_writes: NONE`. This is live SD application/resource identity, NOT an internal-flash bytewise attestation.

For a separate **real active final v1.8** PC backup, we added `scripts/backup_v19_active_v18_fap_ro.py` and `scripts/run-v19-active-v18-fap-backup-ro.ps1` on the v1.9 development branch. User's Windows Python offline negative tests `test_v19_active_v18_fap_backup_ro.py` reported **8/8 OK**. The operator then executed the exact read-only COM7 wrapper and got:

```text
LOCAL HELPER SOURCE: 11/11 PINNED GIT BLOBS PASS
V19 PRETRIAL FINAL V1.8 LIVE FAP PC BACKUP PASS
SAVED_PC_FAP: C:\\Users\\sehmu\\Documents\\LabMate-FAP-PC-Backups\\V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482\\installed_LabMate_v18_FINAL_E11_before_v19.fap
FAP_BYTES: 81528
FAP_SHA256: 393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61
E11_NATIVE_RESOURCE_SCREEN: PASS
FLIPPER_WRITES: NONE; V19_FAP_INSTALL: NOT AUTHORIZED
VERIFIED LIVE FINAL v1.8 FAP PC BACKUP - PASS.
```

This is **real device-to-PC byte readback**, checked against the independently pinned final v1.8 build and PC disk rehash, with live native resource state rechecked before/after. The historical 81,532-byte `v1.8DEV` PC backup remains preserved separately. `>100%` in a transfer progress line is a known progress-display quirk, not a claim about actual bytes transferred.

**Remaining before v1.9 install:** refresh the PC-only snapshot of `/ext/apps_data/labmate` (Log History/CSV/Profiles/S1) with the existing read-only `scripts/snapshot_v18_e11_live_labmate_sd.py` workflow; verify its completed manifest and marker; review exact FAP-only replacement and rollback plan and obtain **separate explicit operator consent**. Even with matching source patches and working E11 GUI, live firmware image checksum and any v1.9 GPIO/EXTI acceptance are still unverified. No v1.9 installation was performed.


## 2026-10-19 — ACTUAL current LabMate CSV/Profiles app-data backup PASS

The operator ran the previously established **read-only live LabMate data snapshot** on COM7. The actual operator-provided output (not simulated) includes:

```text
snapshot_file_bytes: 2128
new_device_files_preserved: 7
changed_device_files_preserved: 2
historical_files_not_on_device: 9
old_backup_preserved: YES
flipper_files_modified: NO
snapshot_full_microSD: NO
restore_rehearsed: NO
firmware_flash_authorized: NO
LIVE LABMATE PC READBACK SNAPSHOT VERIFIED - NO FLASH / NO RESTORE
LABMATE DATA BACKUP: PASS
SAVED_TO: C:\Users\sehmu\Documents\LabMate-FAP-PC-Backups\V19-LabMate-Data-bbacf95032af4bf2bbb470614eaff1a0
```

Scope is **`/ext/apps_data/labmate` only**, containing the application's current CSV/Profile history; this is NOT a whole-card clone, not firmware backup, and not a restore rehearsal. The 7 added and 2 changed files are recorded in the *fresh snapshot*; 9 historical paths absent from the live tree remain in the *historical* PC backup, and the cause of absence is unknown. The actual file count and individual names are not in the excerpt provided; do not invent them or imply that deleted historical data reappeared.

Current pretrial status: **source-patched E11 identity and local FAP review PASS**, currently installed **v1.8 final FAP** byte-level real-device PC backup PASS, **current LabMate app-data** real-device PC snapshot PASS. Pending: exact v1.9 FAP-only installation choreography with a verified no-overwrite staging path, fail-closed partial-transfer/rollback protocol, final read-only device state reconciliation, any missing native ABI/image attestation, **separate explicit owner consent to DEVICE WRITE**, and v1.9 real-device physical checks. This session authorized no device write or firmware flash. Current published Stable and development PR state unchanged.
