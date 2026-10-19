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

## Device gate remains closed

Before any FAP-only installation, determine the currently installed firmware build/version and **independently verify its exported APIs** (including `furi_hal_resource_lease_try_acquire`, `furi_hal_resource_lease_release`, `furi_hal_gpio_try_add_int_callback`) against the binary's required SDK ABI. A firmware version string alone is insufficient. If incompatible or unknown, **NO INSTALL**; do not flash firmware automatically as a workaround.

Before any later separately authorized FAP-only trial, independently back up and verify the old v1.8 FAP, SD card `apps_data`, Profiles/S1 and CSV logs; establish the exact FAP replacement and rollback path; maintain 3.3V-only GPIO/PA7→PC1 safety. Full physical scope 100 Hz / 1 kHz, START/STOP/BACK, A/B, legacy-tool regression and firmware-wide native TIM2/SubGHz/RFID concurrency remain unresolved for v1.9.

The development PR should remain **Draft**, stable v1.8 preserved. No flash, updater, SD cleanup or release was performed.
