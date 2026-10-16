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


## 2026-10-17 — FAP-SEPARATED E11 review derivative built and verified on CI (NOT FLASHABLE)

A new *strictly review-only*, deterministic
[`derive_v18_e11_split_review.py`](../scripts/derive_v18_e11_split_review.py)
was implemented to address the concrete static blocker identified
above: the original full updater ships the LabMate FAP within
`apps/Tools/labmate.fap`, so a firmware-before-FAP verification
sequence was not enforceable with the ORIGINAL full bundle.

**Observed real Linux CI and exact original artifact**:
[Workflow #38973708904](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38973708904)
**COMPLETED SUCCESS**. It fetched actual full `#38966248325`
review bytes and official pinned MNTM-012 rollback updater, ran
adversarial resource and derivative tests, then generated ONE
**derived review** TGZ. In-memory and post-write checksum validation
showed:

- **ONE path removed from the nested update resources:**
  `apps/Tools/labmate.fap`, matching independently SHA256-pinned
  `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0`.
- The **remaining 2,115 resource files are byte-digest equivalent**
  to those from original candidate #38966248325, including exact
  native `js_gpio.fal` SHA256
  `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a`.
  No original LabMate persistent-data path was part of either source
  resource inventory.
- **All seven full updater component payload bytes were preserved**
  except the inner `resources.tar.gz`. Firmware DFU, official C2 radio
  binary, updater manifest, option-byte policy, loader, firstboot
  and splash remained the exact original component bytes.
- The resulting archive was independently unpacked/audited again:
  **LabMate FAP ABSENT from updater**, JS native module retained,
  seven members exactly, option-byte policy and radio bytes match
  official MNTM-012, no private device or microSD access.
- The matched `labmate.fap` and `js_gpio.module` were copied into
  the **same review-only CI artifact as SEPARATE files**, along with
  freshly verified `SHA256SUMS.txt`, `PROVENANCE.txt`, and a prominent
  **READ_ME_FIRST / DO NOT FLASH** warning.

**New derivative identity (never confuse with original):**

- Review-only artifact:
  [`v18E11-SPLIT-REVIEW-DO-NOT-FLASH`](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38973708904/artifacts/12077104037),
  artifact ID `12077104037`, configured for **7 days** retention.
- Derived exact `firmware-full-update-SPLIT-REVIEW-DO-NOT-FLASH.tgz`
  SHA256:
  `7a57b8e630c95b0346e7681ffac84c2400d84b274d97ead977c15813c2abe923`.
- Original full TGZ SHA256
  `11ed3cdf4e99c9c7218973695d349cd946be97d21dfc59231113bde15e94c553`
  **is unchanged** and still exists separately.
- This is a **deterministic derived review archive**, NOT a new native
  Momentum/FAP build, NOT a tested boot image, and NOT an approved
  installer. The FAP is separated at packaging level only; we have
  *not* proven actual firmware/resource activation ordering on
  Flipper hardware.

**Current decision: NO-GO for physical flashing remains.**
The coupled-FAP-in-original-updater problem is technically isolated
in a *non-installed review variant*, but a complete
compatible *trial*-grade package still needs separate product
review, accurate device state/SD backup parity and independent
recovery planning. Importantly the 20 added, 54 removed and 382
changed files vs official older Momentum resources (126 changes in
other `apps_data/` resource paths) **still exist** in the derivative
apart from the one now-excluded FAP. Third-party app/plugin
compatibility and user-customized microSD resources remain
unverified; do not claim a full-SD backup merely because 14 LabMate
files were saved.

**No hardware tests or writes** occurred, no `selfupdate.py`,
`runfap.py`, `-Apply`, flash/restore/SD mutation was run.
PR #13 remains draft; Stable/main/tag/assets unchanged.


## 2026-10-17 — Live LabMate data-copy parity gate (prepared, no USB test yet)

The immediate backup-coverage issue is distinct from full-updater
source-integrity verification:

- Official MNTM-012 and E11 updater resource inventories are only
  *bundled firmware resources*. The E11 split-review derivative omits
  the LabMate FAP, but does **not** establish what currently exists
  under the real Flipper microSD `/ext/apps_data/labmate`.
- The operator's older LabMate folder backup contains **14 locally
  readable files**. Prior history evidence showed some earlier
  `log_0041.csv`–`log_0049.csv` entries were missing from a later
  device listing; there is no demonstrated reason for this, and
  **no recovery/delete/sync action is authorized**.
- The original qFlipper `1,550-byte` settings TGZ is *not a full SD
  backup*. Neither the verified rollback updater nor its archive
  structure proves that a recovery actually restores user data.

**New fail-closed read-only inspection (not yet executed on the
operator's actual COM port):**
[`scripts/audit_v18_e11_live_labmate_sd.py`](../scripts/audit_v18_e11_live_labmate_sd.py)
reads only the LabMate SD subtree `/ext/apps_data/labmate`,
using Momentum's existing Flipper CLI transport with
`device_info` startup, `storage list` and `storage md5`
only. The script inspects the existing local historical backup
without modifying it, computes local MD5 + size/path, and compares
each inventory entry, reporting **counts only**:

- `historical_files_now_absent`: files in historical backup but
  missing on the live SD (e.g. possibly missing past logs).
- `new_device_files_not_in_backup`: fresh logs/profiles which must be
  separately preserved; do not equate an old 14-file backup with
  this actual data.
- `changed_files_not_covered_by_backup`: same path, different byte
  count or MD5, indicating potential drift.
- `same_path_same_size_md5`: screening matches, not authenticated
  SHA256 readback proofs.

**Fail-close policy:** any gap results in a nonzero status and
`BACKUP COVERAGE GAP CONFIRMED`, without deleting or restoring
anything. Even a complete size/MD5 match is limited to LabMate's
own subtree: MD5 is a screening hash, not an independent SHA256
proof and certainly **not an entire microSD backup or restore
rehearsal**. Invalid CLI responses, unexpected paths, symlinks,
case-collisions, missing/empty directories or the wrong root
are refused.

For the operator's existing Windows environment, after successful
CI/peer review of this new script, read-only device verification
could be invoked using a pinned local GitHub source copy and the
previously used COM7:

```powershell
py -3 .\scripts\audit_v18_e11_live_labmate_sd.py `
  --port COM7 `
  --momentum-scripts "$HOME\Momentum-Firmware\scripts" `
  --backup-dir "$HOME\Downloads\LabMate-Backup-20261014-201529"
```

**This is a proposed operator command, not a completed check.**
Run it only with explicit operator intent and a readable, trusted
local `Momentum-Firmware/scripts/flipper/storage.py` tree and
with other programs (such as qFlipper) not holding COM7.
Do not modify code to auto-copy, prune, clear, restore or flash.
Even if the LabMate-only result is a size/MD5 screen match,
other SD folders and updater resource changes remain open.


## 2026-10-17 — Two independent LabMate PC data copies secured (firmware NO-GO)

The operator completed a real **read-only Flipper `storage read_chunks`
→ new PC folder** snapshot for every currently live file under
`/ext/apps_data/labmate`. Terminal result:
`snapshot_files_verified: 10`,
`snapshot_file_bytes: 1791`,
`new_device_files_preserved: 5`,
`changed_device_files_preserved: 2`,
`historical_files_not_on_device: 9`,
`old_backup_preserved: YES`,
`flipper_files_modified: NO`,
with final
`LIVE LABMATE PC READBACK SNAPSHOT VERIFIED - NO FLASH / NO RESTORE`.
The new PC copy was length/MD5-screened against device, locally
SHA256 verified from disk, and the live source re-inventoried after
the copy. The earlier 14-file backup is preserved as a separate,
unaltered historical state. This **closes the LabMate-own-folder
current snapshot gate** but not the full-device SD gate.

**Remaining mandatory release trial barriers:**
1. Preserve or explicitly review current user/app/plugin data and
   customized resources in the **rest of `/ext`**, including
   `apps_data` other than LabMate, before an update whose official
   resource delta is known to affect many plugin and app files.
   A current 10-file LabMate folder snapshot is NOT a full SD copy.
2. Independently review the recovery route and rollback
   compatibility; a downloaded official updater, old FAP copy
   and qFlipper settings-only TGZ do not demonstrate a
   **successfully tested restore**.
3. Exact split FAP-excluded derived updater is **REVIEW ONLY**;
   no tested firmware boot, no owner flash authorization,
   no verified installation sequence/compatibility acceptance.
4. Live E11 GPIO/TIM1/TIM2/EXTI, button/PWM and STOP/BACK
   denial/reacquisition verification on current/new hardware
   remains open. Hardware fixtures explicitly marked DEFERRED
   retain that state until present.

**Decision: NO-GO for firmware flashing despite successful
LabMate folder snapshot.** Do not reuse historical installer
or merge PR #13 / touch Stable.


## 2026-10-17 — Actual non-LabMate SD exposure confirmed; verified whole-card backup tool READY

Real read-only operator COM7 scope survey on the installed EXITFIX
firmware completed PASS. Top-level card structure:
`/ext: 27 directories + 1 file`;
`/ext/apps: 14 directories + 0 files`;
`/ext/apps_data: 57 OTHER application-data directories plus the
LabMate directory, 0 top-level files`. The two preserved PC
LabMate states (14 historical and 10 current files / 1791 bytes)
are **not** full-SD backups. The existence of these other
directories does not establish damage or alteration.

Prepared new [PC reader-mounted SD content preservation
helper](../scripts/backup_v18_e11_sd_reader_to_pc.py)
with [operator/read-only protection handoff](V1_8_E11_FULL_SD_PC_BACKUP_HANDOFF.md).
It requires separately confirmed SD drive root, physically stopped
Flipper and a reader; uses **source FILE READ ONLY** and a
brand-new folder on a different PC drive. Copies all reachable
ordinary/hidden nested files and empty directories, checks
source/destination SHA256 and second source inventory,
refuses root mismatch, special linked paths, insufficient free
space and drift; incomplete PC copies are prominently marked.
The tool is NOT a raw image/metadata clone or real restore test;
Windows volume mounting may still alter device filesystem metadata.
**No physical card was accessed by new CI tests** and no automatic
format/mount/restore is performed.

- [Windows no-device regression #38979716149](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38979716149)
  **SUCCESS**: 11 mock source/destination/rollback-guard tests,
  plus earlier Windows read-only survey/snapshot suites.
- [Integrated software regression #38979716180](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38979716180)
  **SUCCESS**.
- Verified script source pin
  `bb43b8a935cc09b78accc0a44a78c668a779ca01`.
- **Actual operator full-SD copy: NOT YET RUN.**

**NO-GO for firmware flash** continues until a fresh true full-SD
content backup (or an explicitly documented deferred/exception
decision), separately assessed recovery/rollback procedure and
newly authorized trial-grade firmware/FAP pair. Successful
LabMate folder backup and top-level SD survey do not satisfy
these barriers. PR #13 DRAFT, Stable/main unchanged.


## 2026-10-17 — Owner's low-priority non-LabMate data; optional no-reader USB precaution

With real device evidence `/ext/apps_data` has 57 OTHER app-data
directories outside the preserved 14 historical and 10 current
LabMate PC backup files. **Owner has stated remaining card data is
not important** and they have no microSD card reader. Do not turn
buying a card reader or making a full card data snapshot into a
technical dependency for **safe offline software development**.

To offer an additional low-impact path, added optional USB
[`backup_v18_e11_usb_sd_to_pc.py`](../scripts/backup_v18_e11_usb_sd_to_pc.py),
documented in
[`V1_8_E11_USB_SD_OPTIONAL_HANDOFF.md`](V1_8_E11_USB_SD_OPTIONAL_HANDOFF.md).
Default mode prints an actual read-only full `/ext` inventory
without copying. The independent `--copy` action writes exclusively
to a new PC folder; after SHA256 readback it repeats all device MD5
checks. The program refuses unrepresentable paths, unsafe
filesystem names, transfer budget overruns and unexpected CLI
responses, and never silently skips files and calls them backed up.

Software: [Windows synthetic #38980845491](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38980845491)
**SUCCESS** with 11 USB transfer/no-overwrite/fail-closed
tests; [integrated regression #38980820652](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38980820652)
**SUCCESS**. Real on-device complete USB inventory/copy has NOT
run: actual full SD backup still NOT proven.

**Decision logic:** The owner may explicitly accept a specific
non-LabMate app-data loss risk (those data are low-priority)
and continue device **trial planning**, independently of a full
card backup, but that choice **cannot waive** verified firmware
provenance, radio/option-byte security, rollback/boot recovery,
separate new trial-package approval, or E11 source coexistence
physical acceptance. Neither old FULL nor FAP-separated review
archives are flash-authorized. PR stays draft and main/Stable
remain unchanged. A complete SD backup may always be obtained
later over USB or reader if the owner chooses.


## 2026-10-17 — Recovery equivalence checked: official 012 fallback is NOT exact prior mntm-dev

[Recovery/DFU decision memo](V1_8_E11_FIRMWARE_RECOVERY_DECISION.md) establishes a safety distinction overlooked by a simple archived-backup SHA check. The running device is `mntm-dev`, base `d3f89dfe`, dirty=true; the local verified rollback TGZ is official `mntm-012`. No independently trusted SHA256 of the currently installed **entire firmware image** nor identical restorable old custom firmware package is established. Recovering to official MNTM-012 could be a viable **release fallback**, but is not the same as returning to the current customized firmware. The old Stable FAP is not the on-device EXITFIX FAP, although a matching EXITFIX readback copy is preserved.

Flipper's [manufacturer recovery documentation](https://docs.flipper.net/zero/basics/firmware-update/firmware-recovery) describes qFlipper USB DFU recovery **as a recovery path, not a non-destructive preflight**. Its firmware Repair can erase internal storage; settings recovery from the saved qFlipper TGZ is not rehearsed. Never instruct immediate DFU/Repair to prove a future rollback.

[Automated offline NO-GO audit](../scripts/audit_v18_e11_recovery_readiness.py) with 13 adversarial tests distinguishes these cases. [Host CI #38981611042](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38981611042) **SUCCESS**; [independently pinned update resource/radio/OB verification #38981663476](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38981663476) **SUCCESS**. The resulting label is `E11 OFFLINE RECOVERY EQUIVALENCE AUDIT PASS - TRIAL NO-GO`, **not** permission to flash. Device-level recovery equivalence and independent firmware install/boot consent remain OPEN, even though non-LabMate full-SD backup is optional given the operator's stated data priorities. PR #13 draft; original and split artifacts DO NOT FLASH.


## 2026-10-17 — Old /ext/Manifest deletion during firmware update: source proof, live device pending

**Additional independently verified updater hazard:** the pinned Momentum
post-update worker restores internal backup, then removes old resource files
listed by the CURRENT on-device /ext/Manifest BEFORE unpacking the NEW
resources.tar.gz. Files are removed by old manifest paths, not by a
compare of current byte hashes. Therefore our review-only updater
derivative which removes the NEW bundled LabMate FAP does NOT alone
guarantee survival of the ALREADY installed EXITFIX FAP. The old
manifest may or may not list apps/Tools/labmate.fap; this cannot
be inferred from official old release archives because the
currently installed firmware is custom dirty mntm-dev.

Added a narrowly scoped [read-only real-device old-resource
manifest probe](V1_8_E11_LIVE_UPDATER_MANIFEST_HANDOFF.md) and
[source/audited binary parser](../scripts/audit_v18_e11_installed_resource_manifest.py).
It reads ONLY /ext/Manifest with storage md5 + read_chunks, verifies
source-screen checksum before/after, reports ONLY counts and known
LabMate flags and refuses to create install permission in all
outcomes. **OPERATOR HAS NOT RUN THIS PROBE ON ACTUAL COM7 YET.**

CI: [exact upstream source #38982495403](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982495403)
**SUCCESS** (10 static semantic tests and 11 manifest tests);
[Windows simulated device #38982495374](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982495374)
**SUCCESS**; [full host suite #38982495377](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982495377)
**SUCCESS**. Source-level resource deletion is confirmed;
actual old installed Manifest entries remain UNKNOWN. Keep E11
firmware trial, stable merge and any FAP overwrite **NO-GO**.
