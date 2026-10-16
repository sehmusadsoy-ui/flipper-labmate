# LabMate v1.8 — E11 real-device trial gate (NOT AUTHORIZED TO INSTALL)

**Status:** Offline preflight PASS on 2026-10-17. **Physical trial NOT STARTED.**
**Branch:** `dev/v1.8-completion` / draft PR #13. Stable `v1.8`, tag, release asset and `main` unchanged.

## Immutable evidence before proposing a new firmware trial

- Existing Flipper device via COM7 CLI: Flipper Zero, `mntm-dev`,
  base short hash `d3f89dfe`, `firmware.commit.dirty=true`, firmware API
  `87.1`, radio alive. This is *not* proof of an exact on-device E11
  firmware-diff fingerprint.
- Current installed FAP: on-device USB readback SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`,
  the earlier **EXITFIX** binary, with independent historical E1–E9 physical
  evidence. Do not transfer these PASSes to the new candidate.
- New FULL no-flash matched CI #38966248325, source
  `ba379f20fb29369501e1057f570a911f71ac83f8`,
  CI verifier completed SUCCESS. Independent Windows ZIP contents
  and exact local `preflight_v18_e11_local.py` full review:
  **PASS** with all pinned provenance and four SHA256 values:

  | File | SHA256 |
  | --- | --- |
  | labmate.fap | `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0` |
  | firmware.dfu | `88d12fee4edb4fa0ec042a1b526ddb41b8db36aeb9554c6a9a8aef1c37e4e1b0` |
  | js_gpio.module | `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a` |
  | firmware-full-update.tgz | `11ed3cdf4e99c9c7218973695d349cd946be97d21dfc59231113bde15e94c553` |

- Independent native E11 firmware source patch fingerprint
  `1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80`.
  Its provenance alone does not prove the installed DFU.
- Historical rollback official MNTM-012 update
  `1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7`
  and Stable FAP
  `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`
  SHA256 verified on Windows. Current EXITFIX FAP readback is preserved.
- LabMate local microSD-folder copy: 14 files locally readable and
  nonempty; this does **not** prove all live SD files are preserved
  or that a restore would succeed.
- qFlipper settings archive at operator's **Desktop** (not Downloads):
  1,550 bytes, exactly 14 readable regular files and 1 directory,
  path-safe TGZ validation and SHA256
  `a0487ede35b8cec4cef505faf57363768fc1bc02d5d7c1dd3a8dcfa282c00ef2`.
  Not a complete microSD image; restore has **not** been rehearsed.
- User executed independently pinned source/script
  `preflight_v18_e11_local.py`, successfully reporting:
  `LOCAL E11 INPUT PREFLIGHT PASS - NO FLASH, NO DEVICE ACCEPTANCE`.
  [CI host regression #38969669551](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38969669551)
  completed SUCCESS.

## Blockers before any physical device write

1. **Separate explicit owner permission** for an experimental full Momentum
   firmware trial, including the known full-updater radio/SD/option-byte
   scope. Prior authorization for the 2026-10-14 older candidate is not
   transferable to this new one.
2. **Reviewed recovery plan:** how to enter device recovery/DFU, the verified
   rollback updater + known-good FAP, independently held settings and
   microSD copies, expected failure and power-loss handling. A structural
   backup check is NOT a real restore rehearsal; do not claim recovery
   guaranteed. A destructive restore rehearsal is not authorized.
3. **Exact matched new-build trial procedure** deliberately separate from
   the earlier installer. `scripts/install-v18-full012-dev-firmware.ps1`
   pins three **different** older file SHA256s
   (`5e3267...`, `e69f717...`, `9a276e6...`), and must not be run
   against the latest artifact or made to skip its hash guards.
   The current archive is literally labeled **DO NOT FLASH** and is
   review evidence, not an installation approval. A proposed trial
   needs a vetted, expressly approved candidate/procedure, with staging
   read-only by default and separate firmware-then-FAP gates.
4. **Device/provenance assessment:** reconcile current `mntm-dev`
   dirty firmware with the new actual patched SDK and full updater.
   Partial short-hash coincidence cannot replace binary/protocol verification.
5. **Physical conditions:** disconnect external GPIO peripherals, ensure
   adequate battery, stable USB and uninterrupted maintenance window;
   do not interrupt full updater. These are requirements for a later
   authorized operation, **not** an instruction to flash now.

## Proposed physical acceptance plan (after a separately approved trial)

This is a *test plan*, not claimed results. Record tested exact **firmware
pair SHA256 + FAP SHA256**, device boot/firmware report and no regressions.
Never claim real peripheral correctness from `NONE` on a disconnected bus.

- **E11 baseline:** UI boot, one LabMate FAP, menu order
  `MEASURE → OUTPUT → RECORDS → COMM → INFO` with INFO last;
  verify return to menu, app EXIT/REOPEN and unexpected STOP/BACK cleanup.
- **Resource denial/release/re-entry:** test PWM owner vs COMM
  I2C and PA4 OneWire, normal stop + re-entry, UI BUSY, cancellation
  and abort paths; never drive two output owners onto same pin.
- **Counter, capture and button:** TIM1/TIM2 and EXTI STOP/RESUME
  ownership and refusal/fallback; use no-signal smoke only where an
  external 3.3 V generator is absent. External timing precision deferred.
- **UART:** existing ESP32-S2 at 3.3 V with previously vetted wiring;
  RX/TX count, DROP/ERROR, STOP/BACK with real peer if the accessory
  is available. Historical EXITFIX UART result is not the new-pair result.
- **Records:** read-only History/Profiles inspection first, and careful
  app-owned CSV create/delete only with a separately recorded scope
  and no risk to historical logs. Compare backups before/after.
- **Firmware coexistence:** supported E11 owner paths and intended
  conflict UI, background services after STOP/re-entry. Unsupported
  legacy third-party plugin interactions remain explicitly unproven.
- **Physical deferred exceptions:** real positive-ACK I2C device,
  3.3 V DS18B20 + pull-up, calibrated PWM/pulse edges,
  exceptional fault-injection/storage-power-loss recovery, and
  actual successful rollback. Keep them on
  [`DEFERRED_HARDWARE_TESTS.md`](DEFERRED_HARDWARE_TESTS.md) until equipment
  and non-destructive test method exist.

### Stop / fail-close conditions

Any mismatch in exact source/build/backup/rollback assets, physical
firmware version, device abnormal boot, radio recovery or SD trouble:
**stop**, do not launch incompatible FAP, do not automatically
flash or restore anything. Preserve logs and report exact failing stage
before a separate recovery decision. Never overwrite the original
Stable `v1.8` tag/assets or merge PR #13 based only on CI.


## 2026-10-17 — Separate no-device review staging tool

`scripts/stage_v18_e11_review_only.py` is a **NEW, stage-only** helper.
It MUST NOT be confused with the old historical
`install-v18-full012-dev-firmware.ps1`, and it does not contain an
`-Apply`/firmware upload/FAP install code path.

Before writing any local staging output, it repeats the **actual
Windows-operator input preflight**: four pinned candidate checksums,
exact CI run/source and updater proof, previously verified installed
EXITFIX FAP, official old MNTM-012 rollback, Stable FAP, 14+ LabMate
backup files and the 14-file/1-directory qFlipper Desktop settings TGZ
with SHA256 `a0487ede35b8cec4cef505faf57363768fc1bc02d5d7c1dd3a8dcfa282c00ef2`.
It then validates a strict one-root, **seven-file updater allowlist**,
bounded regular TAR entries only, correct embedded DFU SHA256 and
original official radio SHA256. Unexpected, missing, duplicated, linked
or mismatched files fail closed. It writes the seven staged updater
files and prominent **STAGING_REVIEW_ONLY.txt / DO NOT FLASH** marker to
an operator-selected **new local folder**. Pre-existing output folders
and output paths within original verified artifact, rollback or data
backup directories are refused. It has no USB/COM path or hardware API.

The helper has synthetic positive/negative Python tests in
`tests/test_v18_e11_review_stage.py`. An additional Windows CI workflow
`check-v18-e11-review-stage-windows.yml` checks adversarial rejects,
downloads only public pinned CI #38966248325 review data, verifies the
exact artifact provenance and performs a review-only stage in a runner
temporary folder. **The CI stage tests public data only; it CANNOT
verify private PC backups**. Report completed workflow results before
considering any Windows local invocation.

**Important:** staging is not a firmware update rehearsal. Stage folder
contents are not approved for flash and no firmware/FAP application
will be recommended on the basis of staging PASS alone. Full-updater
radio, SD resources and option-byte policy remain a physical
risk, and recovery is not proven.


## 2026-10-17 — Windows real-artifact stage-only verification PASS

[Windows CI #38970840598](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38970840598)
**COMPLETED SUCCESS** on review staging source
`5226b2b81d87c515a686d120c001fc996480811b`:

- **13/13 Windows synthetic negative/positive stage tests PASS**,
  including wrong embedded DFU/radio, path traversal, symlink,
  duplicate, missing/extra members and local overwrite refusal.
- Windows fetched the actual review-only FULL artifact from
  `#38966248325`, verified four independently pinned SHA256s,
  exact Actions source/run provenance, radio and updater contents,
  extracted exactly the expected seven update components to a
  brand-new **runner temporary review** directory, and verified the
  staged `firmware.dfu` bytes.
- CI printed
  `REAL FULL CI 38966248325 WINDOWS REVIEW STAGE PASS - NO FLASH`.
  Private qFlipper settings and microSD backup files are **not in CI**;
  those were verified previously on the operator's PC using the full
  independent local preflight, which is re-invoked by the operator
  stage script before writing any **new local** staging folder.

**Remaining:** the newly added stage script has not yet been executed
on the operator's Windows PC. Windows CI stage success is NOT an
operator real-device trial, safe-to-flash certification, recovered
settings validation, or an authorization to apply full updater.


## 2026-10-17 — Actual operator Windows seven-file review staging PASS

**USER-REPORTED LOCAL DEVICE-FREE PASS** running the newly validated,
exact-source `stage_v18_e11_review_only.py` against the independently
verified full-review package `#38966248325`, the previous
on-device-readback EXITFIX FAP, and operator-held backups:

```
EXACT E11 CANDIDATE AND BACKUP PREFLIGHT PASS (OFFLINE)
REVIEW-ONLY UPDATER FILES: 7
REVIEW DIRECTORY: Downloads/LabMate-E11-Staged-REVIEW-38966248325/f7-update-mntm-HEAD-d3f89dfe
E11 LOCAL REVIEW STAGING PASS - NOT AUTHORIZED TO FLASH
No Flipper connection, firmware install, FAP overwrite, SD operation or restore.
E11 REVIEW STAGING COMPLETE - NO FLASH
```

Seven regular updater components were written to a *new local Windows
review directory only*. **This closes the exact Windows operator
review-staging gate, not the full firmware installation gate.**
User's old working `EXITFIX` FAP remains on-device; no current
firmware image or serial radio test was changed.

**Formal go/no-go outcome at this point: NO-GO for firmware write.**
The source archive and stage explicitly warn `DO NOT FLASH`;
the historical installer is pinned to different bytes and cannot
be repurposed. No independently verified restoration run exists.
Full updater may affect radio firmware, SD resources, option bytes,
and application ABI. A separate, reviewed and explicitly authorized
new build/procedure must be in place before attempting physical E11
trial. Nothing in an offline PASS is consent to flash.

**Remaining decisions for trial authorization:** (a) review the
full-updater option-byte/radio/SD compatibility and firmware recovery
method for the exact device, (b) independently scope possible backup
gaps and preservation of historical log/profile data, (c) finalize
new exact-match install-and-post-boot procedure with stop rules,
(d) obtain **new explicit operator authorization**. Real E11
GPIO/TIM1/TIM2/EXTI physical acceptance and deferred hardware
fixtures remain open and must not be described as PASS.


## 2026-10-17 — Verified upgrade resource delta; coupled FAP is a NEW trial blocker

**Full independently pinned public binary comparison on real packaged bytes:**
[`#38972918375`](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38972918375)
and follow-on
[`#38973079012`](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38973079012)
completed **SUCCESS**, using exact official MNTM-012 rollback hash
`1d9e1e...` and actual E11 full CI artifact #38966248325.
[`scripts/audit_v18_e11_resource_impact.py`](../scripts/audit_v18_e11_resource_impact.py)
read both TGZs in memory without applying or writing resources to SD.

**Static evidence:**

| Field | Observed | Interpretation |
| --- | ---: | --- |
| Official previous update resource files | 2150 | Upstream baseline |
| Current E11 update resource files | 2116 | Full app/plugin/resource set differs |
| Newly added resource paths | 20 | File additions |
| Removed resource paths | 54 | File removals |
| Modified resource paths | 382 | Same path, different SHA256 |
| Other changed `apps_data/` resource paths, excluding checked `js_gpio.fal` | 126 | **Bundled extension/plugin resources**, not proof that saved LabMate CSV data was modified |
| New bundled `apps/Tools/labmate.fap` | **YES** | Binary is the exact independently SHA256-pinned new LabMate app |
| Previous official MNTM-012 bundle contains that FAP | **NO** | It is introduced by the new E11 updater |
| Bundled native `apps_data/js_app/plugins/js_gpio.fal` | **YES** | Matches independently SHA256-pinned matched plugin |
| Update contains `apps_data/labmate/` | **NO** | No direct updater payload under LabMate's own persistent-data tree; **not** a guarantee that the overall update cannot affect SD |

**Radio and option-byte comparison:** the new updater's radio
**bytes** and six relevant update manifest fields (target, radio,
radio version, OB reference, OB mask and OB write mask) matched the
SHA256-pinned **official** MNTM-012 updater. It does **NOT**
demonstrate that a full updater will write no option bytes or that
a bootloader/SD migration cannot fail.

**Critical new mismatch with proposed rollout procedure:** because
the E11 `resources.tar.gz` includes
`apps/Tools/labmate.fap`, a full resources update may place the **new
FAP on microSD as part of the firmware operation**. Therefore earlier
"install firmware, verify boot, *then* install the new FAP" wording is
**not a guaranteed two-phase isolation boundary** for THIS artifact.
Do not execute the old flash script, edit its hardcoded hashes, or
silently remove the FAP from an already checksummed archive.

**NO-GO remains in force**. A non-writing reference model
`model_split_resources_without_labmate_fap` verifies that the exact
bundled FAP path can be excluded *conceptually* while preserving the
exact JS GPIO plugin and all other indexed resources. It writes **no
new updater and makes no installation claim**. The real package is
unchanged and still explicitly labeled `DO NOT FLASH`.

**Engineering decision before asking for device update permission:**
produce a **new, independently pinned candidate build** with one
separately delivered matched `labmate.fap` and a firmware updater
resource archive that excludes `apps/Tools/labmate.fap` but preserves
the exact matched native `js_gpio.fal`. Independently verify its
radio/option-byte policy, inner firmware DFU, all resource and app
hashes, source/run provenance, archive safety and review-only
designation, and confirm changed SD resource path scope. Original
#38966248325 and the Windows staging folder are immutable **review
evidence, not transferable installation packages**.

Other changes to updater-supplied applications and plugins (including
the 126 `apps_data/` paths) still require a separate compatibility
review and physical post-boot checks. The stored user settings and
LabMate data backups are readable but **restoration not rehearsed**.
Neither model feasibility nor CI proves device safety.
