# v1.8 — Read-only FULL candidate preflight (no device access)

This procedure applies to the **full** pinned Momentum MNTM-012-derived
development review artifact, containing the **single** LabMate FAP,
native JS GPIO plugin module, actual DFU and radio/SD-resource updater.
It is NOT the older minimal pair; do **not** use
`scripts/verify-v18-matched-pair.ps1` on the full artifact (different
names and provenance schema).

## Exact existing reproducible artifact

- GitHub Actions [full no-flash run #38955881504](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38955881504):
  verified SUCCESS on **LabMate source**
  `349d717f6cde7d1a117edea0db0058e9f2a5748f`.
- Artifact ID `12069454610`, name
  `v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH`.
- This temporary review artifact is scheduled by Actions to expire on
  **2026-10-23**. Never silently substitute a newer commit/artifact if
  it expires; confirm the new run ID/source first.
- Independent Momentum base must be
  `d3f89dfe2ef6b01839201598e9be1590cba80322`.
  Independent upstream `mntm-012` source
  `e1784e7418d8b074e971983ceb6fef0f37e52ae4`.

## Obtain and verify only (no Flipper attached)

In a local checkout of the development branch with **GitHub CLI
authenticated** and Python 3 available, these example commands download
the exact existing public CI artifact into a dedicated directory.
This reads the public Actions artifact and writes *only that local
temporary folder*. It does **not** use qFlipper, USB, or device storage.

```powershell
$pair = Join-Path $env:TEMP 'labmate-v18-full-review-38955881504'
New-Item -ItemType Directory -Force -Path $pair | Out-Null

gh run download 38955881504 `
  -R sehmusadsoy-ui/flipper-labmate `
  -n v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH `
  -D $pair

py -3 .\scripts\verify_v18_full_review_pair.py $pair `
  --expected-source 349d717f6cde7d1a117edea0db0058e9f2a5748f `
  --expected-run 38955881504
```

The independent verifier rejects incorrect expected source/run, changed
binary SHA256, missing/extra files, symlinks, duplicate provenance,
nonmatching Momentum base/MNTM-012 source, missing warning, an untrusted
radio binary (official known-good MNTM-012 digest), malformed updater
option-byte metadata and a TGZ embedding a different firmware.dfu.
It uses [the existing secure full TGZ parser](../scripts/check_v18_full_update_bundle.py)
and requires exactly four checksummed binaries:
`labmate.fap`, `js_gpio.module`, `firmware.dfu` and
`firmware-full-update.tgz`.

**Important:** SHA256 checks from the artifact itself establish
self-consistency, not authenticity. Trust the originating GitHub Actions
run and expected SHA separately; verify the exact run's conclusion and
source SHA rather than trusting `PROVENANCE.txt` alone.

Automated negative cases are in
[`test_v18_full_review_pair.py`](../tests/test_v18_full_review_pair.py)
and run with the consolidated v1.8 host CI. The **current/new**
full-updater workflow additionally executes this verifier on its actual
generated artifact before publishing the review-only ZIP; successful
CI is required for a new source pair and must be confirmed per run.

## Where this gate stops

A `READ-ONLY VERIFICATION PASS` **does not** authorize firmware
flashing, updater use, an SD restore, a release, v1.9, or claiming
Flipper sensor/radio physical function. It does not perform a restore
trial or prove the physical boot path. The source includes a custom
firmware, bundled SD resources, radio binary and option-byte policy;
review the independent operator-approved recovery and backup checks in
[`V1_8_PHYSICAL_ACCEPTANCE_GATE.md`](V1_8_PHYSICAL_ACCEPTANCE_GATE.md)
before proposing **any** device operation.

Existing stable `main`, historic v1.8 tag/assets and the user's
CSV, profiles and log history remain untouched by these read-only
preflight operations. If source provenance, hashes or archive differs,
**REFUSE**, do not automatically "fix" via device flash.


## 2026-10-17 — Final verified candidate (supersedes old artifact example)

The **latest completed fully matched full-updater build** is
[GitHub Actions #38966248325](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38966248325):
**completed/SUCCESS**, including native firmware/one LabMate FAP/JS
build, comparison to the published MNTM-012 radio and option-byte
policy, and the new **independent real archive** verifier.
The actual tested LabMate source is
`ba379f20fb29369501e1057f570a911f71ac83f8`.
Review-only artifact `v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH`,
ID `12075925371`; scheduled expiry **2026-10-23**.

Exact full-artifact file SHA256 values printed by the full-workflow
verifier:

| File | Verified SHA256 |
| --- | --- |
| `labmate.fap` | `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0` |
| `js_gpio.module` | `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a` |
| `firmware.dfu` | `88d12fee4edb4fa0ec042a1b526ddb41b8db36aeb9554c6a9a8aef1c37e4e1b0` |
| `firmware-full-update.tgz` | `11ed3cdf4e99c9c7218973695d349cd946be97d21dfc59231113bde15e94c553` |

E11 firmware diff fingerprint
`1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80`.
For the **new** artifact, explicitly replace the older example run,
source, and extraction directory in the command above: use
`gh run download 38966248325`, exact source
`ba379f20fb29369501e1057f570a911f71ac83f8`, and
`--expected-run 38966248325`. Never mix metadata between runs.

**Not approved for flash** merely because full CI is green.
On-device latest CLI observation reports base `d3f89dfe`,
`dirty=true`, API 87.1, and `mntm-dev` dated 14-10-2026, but **does
not** establish that the latest reviewed firmware DFU or FAP is already
installed. Read back the actual Flipper FAP and compare its SHA256,
preserve backup/rollback assets, and explicitly authorize any later
installation separately.


## 2026-10-17 — Single-command local E11 operator inputs preflight (OFFLINE ONLY)

The new [`scripts/preflight_v18_e11_local.py`](../scripts/preflight_v18_e11_local.py)
is an **offline/read-only, fail-closed** gate for the already acquired
CI **#38966248325** full candidate. It checks all **four independently
pinned artifact SHA256s**, then calls the existing independent
[`verify_v18_full_review_pair.py`](../scripts/verify_v18_full_review_pair.py)
for the *exact* source commit `ba379f20fb29369501e1057f570a911f71ac83f8`,
run `38966248325`, full updater inner DFU/radio/SD metadata,
provenance and required warnings. It also checks rollback MNTM-012
and original Stable FAP digests, the byte-readback EXITFIX FAP digest,
nonempty LabMate SD **local backup** files, and the existing local
qFlipper settings TGZ against independently observed SHA256
`a0487ede35b8cec4cef505faf57363768fc1bc02d5d7c1dd3a8dcfa282c00ef2`
and **14-file/1-directory** path-safe TAR structure. It will not
connect to COM7, launch qFlipper, flash, restore, install, or copy
anything to the Flipper.

**A local clone of the current development branch is required**, with
Python 3 and its two Python companion scripts in `scripts/`. Run from
that clone's root, after separately checking that the exact full
Actions review artifact and readback copy are located where expected:

```powershell
py -3 .\scripts\preflight_v18_e11_local.py `
  --candidate "$HOME\Downloads\LabMate-E11-Review-38966248325" `
  --rollback "$HOME\Downloads\LabMate-Rollback-MNTM012" `
  --installed-fap-copy "$HOME\Downloads\LabMate-FAP-ReadOnly-Audit\labmate-installed.fap" `
  --data-backup "$HOME\Downloads\LabMate-Backup-20261014-201529" `
  --settings-archive "$HOME\Desktop\Uybelav-backup-20261014-201804.tgz"
```

**Evidence:** [final integrated no-flash host regression
#38969669551](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38969669551)
completed SUCCESS at source commit
`1c7446b19a9340349862a6ee7f96129e835af005`; the integrated
suite includes the new [negative-path/positive-path regression file](../tests/test_v18_e11_local_preflight.py)
and retained prior v1.5–v1.8 native C regressions.
An earlier first CI attempt failed on a *test harness assertion typo*
(`assertRaisesRegex` missing a regex); this was fixed, and the new
run is green. No production Flipper code changed as part of the
local verifier addition.

**Scope boundary:** This script's own PASS is not yet observed on
the operator's Windows folder in the current evidence. More
importantly, even a real local PASS does **not** prove current device
flash byte identity, full SD equality, operational rollback,
successful future firmware boot, firmware cross-service resource
coexistence, physical I²C/DS18B20 performance, or user permission
to install. The older
`scripts/install-v18-full012-dev-firmware.ps1` is pinned to a
*different FAP/DFU/TGZ*. It **must not** be reused or modified to
bypass its original digest constraints. New exact-pair installation
requires a separately reviewed tool/procedure, independently tested
recovery safeguards and explicit operator authorization.
