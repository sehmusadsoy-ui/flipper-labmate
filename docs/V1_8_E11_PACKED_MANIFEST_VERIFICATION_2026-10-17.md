# LabMate E11 — independent nested updater resource Manifest check

**Date:** 2026-10-17. **Scope:** original E11 development full-updater and
FAP-excluded derivative **offline**, using exact pinned existing CI artifacts.
**Neither package has approval to be flashed or installed.**

## Why this second cross-check matters

Previous real-device COM7 read-only evidence showed the OLD installed
`/ext/Manifest` explicitly lists `apps/Tools/labmate.fap`.
The Momentum updater deletes the files in this old Manifest before
unpacking the new resource archive. Therefore an update containing
resources can remove today's working EXITFIX regardless of whether
the new resource archive contains a LabMate FAP.

Separately, the *NEW* resource archive also includes a resource
`Manifest` declaring MD5, byte lengths and relative paths. Our first
FAP-excluded review derivative removed just the LabMate FAP file,
preserving all other new resource bytes — **including this Manifest**.
An omission-only binary comparison was insufficient to detect that
the new Manifest would still declare a file which had been removed.

## Observed verified E11 package content

Verified using archived review-only GitHub Actions build
[#38966248325](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38966248325),
independently pinned source commit
`ba379f20fb29369501e1057f570a911f71ac83f8`
and downloaded real updater resources. They are not on-device
hardware data.

| Property | Original FULL development archive | Existing FAP-excluded SPLIT derivative |
| --- | ---: | ---: |
| Other files in packed resources excluding `Manifest` | 2,115 | 2,114 |
| File records declared in packed `Manifest` | 2,114 | 2,114 |
| Resource Manifest files referencing physically absent packed files | **0** | **1 — LabMate FAP** |
| Actual `apps/Tools/labmate.fap` packed | YES | NO |
| `Manifest` still declares LabMate FAP | YES | **YES, stale entry** |
| Manifest MD5/size mismatches for resources present | 0 | 0 |
| Other resource files present but unlisted | 0 after exact firstboot exception | 0 after exact firstboot exception |
| Installed previous EXITFIX preservation proven | NO | NO |
| Physical firmware install/boot PASS | NO | NO |
| Installation authorized | NO | **NO — REJECTED as trial package** |

`dolphin/firstboot.bin` is the **single explicitly recognized**
unlisted file in both source archives. Its generation occurs during
Momentum's `scripts/update.py` resource packaging; it may follow the
earlier `Manifest` generation stage. Rather than treating all
unlisted paths as acceptable, we allow **only this exact known path**.
Every other undeclared member or altered MD5/length still fails
validation. Only the original resource TAR's total file count
includes this special file.

**Independent SHA256:** The original full FAP embedded at the
resource path also matches the separately pinned E11
`labmate.fap` SHA256
`2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0`;
the JS plugin in both update resource archives matches exact
`js_gpio.module` SHA256
`fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a`.
No general authenticity of firmware flash or radio programming is
proved by this resource consistency check.

## CI and fail-closed changes

Added `scripts/audit_v18_e11_packed_manifest_integrity.py`
and `tests/test_v18_e11_packed_manifest_integrity.py`. They verify
actual TAR member names, file sizes/MD5, duplicate/path sanitization,
Manifest metadata and independent SHA256 of specifically pinned FAP
and JS binaries. 16 synthetic positive/negative tests include
wrong-but-valid-format SHA fingerprints and the sole firstboot
exemption.

- [Original+split real artifact audit #38984202194](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38984202194):
  **SUCCESS**, including actual nested resource Manifest reconciliation.
- [Integrated host #38984217069](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38984217069):
  **SUCCESS**, 16 new tests and previous v1.5–v1.8 native/model regressions.
- [Final no-artifact-publish workflow](https://github.com/sehmusadsoy-ui/flipper-labmate/blob/dev/v1.8-completion/.github/workflows/check-v18-e11-resource-impact.yml)
  now computes the rejected FAP-SPLIT derived package **only in an
  ephemeral CI working folder**; because the real old Manifest
  and split-new Manifest together demonstrate an unusable route,
  it no longer uploads a fresh downloadable derivative.

Previously generated [REVIEW-ONLY run #38973708904](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38973708904)
may retain an older derivative artifact until automatic retention
expiry. It remains **DO NOT FLASH**, not retroactively repaired or
approved. Future local generation warning text explicitly states
the real-device old cleanup and rejected trial condition.

## Decision

**`ORIGINAL_FULL_RESOURCE_PAIR=CONSISTENT`** only about checked
packed file bytes, Manifest MD5/size and separately pinned app/JS
hashes. **`ORIGINAL_FULL_DEVICE_TRIAL=NO_GO`** until independently
authorized matched firmware–resource–app–recovery plan and real
device tests.

**`SPLIT_NEW_MANIFEST_STALE_FAP_REFERENCE=YES`** and
**`SPLIT_EXITFIX_PRESERVING_TRIAL=REJECTED`**. Do not try to
"fix" the package by merely deleting the manifest record:
the OLD installed Manifest still targets EXITFIX for removal and
such a change would produce an additional new binary requiring
a separate source-build/recovery/safety review.

The owner has already preserved 14 historical and 10 current LabMate
data files on PC, and no Flash/SD writes have been authorized. Stable,
working installed EXITFIX and PR #13 DRAFT remain unchanged. GPIO/
TIM1/TIM2/EXTI live E11 physical acceptance is still OPEN.
