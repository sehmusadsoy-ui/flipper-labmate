# LabMate v1.8 E11 — final release decision (2026-10-17)

**Verdict: E11 FINAL-FAP FUNCTIONAL PWM AND OPERATOR-REPORTED ISOLATED LOGGER/PROFILE PERSISTENCE PASS; IN-PLACE/PUBLIC STABLE REPLACEMENT NO-GO.**
**Branch:** `dev/v1.8-completion`, [Draft PR #13](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/13).
**No action authorized by this document:** firmware flashing, FAP installation, CSV/profile modification, merge, tag move, public release asset replacement, or rollback.

## Separate the two v1.8 binaries

| Build | Exact artifact / provenance | Status |
| --- | --- | --- |
| Published public `v1.8` Stable (2026-10-14) | GitHub tag `v1.8` -> `02b05639364d6dd71f5eb70456eca379c59218cb`; `labmate.fap` SHA256 `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0` | **PRESERVE, NO CHANGE** |
| Expanded E11 **final-label** `v1.8` *candidate* | Source/overlay review CI `#39035056937`, commit `99cb65d0194dc59d423cfa439c90618ac6b9f114`; FAP SHA256 `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61` | **Tested on the matched custom E11 firmware, NOT public Stable** |
| E11 matched firmware and native resources | Built on patched Momentum source base `d3f89dfe2ef6b01839201598e9be1590cba80322`; candidate `firmware.dfu` SHA256 `e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b`; `js_gpio.module` SHA256 `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a` | **Custom ABI/dependency: never market as standalone universal FAP** |

The E11 final-label candidate was installed on the already paired custom firmware by a narrowly authorized **FAP-only** replacement; previous FAP retained in `/ext/apps/Tools/labmate.e11-pre-final.bak`. This does **not** certify installing the candidate on stock Momentum `MNTM-012`. The matched full updater can alter firmware, bundled microSD resources and startup/compatibility behavior, and exact rollback was **not rehearsed**.

## Device evidence accepted for the exact E11 final FAP

- On-device initial About/menu/PWM STOP/exit/reopen **5/5 PASS**; passive Log History/Profiles S1/UART STOP/BACK **3/3 PASS**; no-signal Frequency/Pulse/Counter/Button screen/exit **4/4 PASS**. These are screen/lifecycle acceptance, not storage durability or signal-calibration evidence.
- ESP32-S2 at **115200**: received `ESP32_READY`, observed `ESP32_OK` in the session, `AT` armed the existing ST2 stress fixture, `STRESS_ARMED`, burst and `BURST_END` observed; UART STOP/BACK and subsequent non-peer tool resource release operator-reported **PASS**. No fresh exact byte-loss/error benchmark; last AT-to-OK timestamp association not proved.
- PA7 -> PC1 **100 Hz / 50%**: PC1 `100.00 Hz`; HIGH/LOW `5.00 ms`, period `10 ms`, duty `50.0%`; PWM STOP PASS.
- PA7 -> PC1 **1 kHz / 50%**: PC1 `1 kHz`; HIGH/LOW `500 us`, period `1.00 ms`, duty `50.0%`; PWM STOP PASS.
- Same installed candidate: separate user-reported **STOP -> no new pulses; RESTART -> 1 kHz restored; final STOP/BACK PASS; BUSY/ERR not reported**. Frequency screen retention of the last displayed numeric value after STOP was not specified.
- These complete **the bounded digital PWM/Frequency/Pulse/STOP/RESTART physical gate**. They do **not** establish externally calibrated accuracy, measured STOP-pin voltage, actual simultaneous firmware-global second-client BUSY or independent TIM2/EXTI/third-party coexistence.

The earlier E11 `v1.8DEV` matched trial's **36/36** A–G operator-reported observations and **H0/H2** native JS PA7 reads are retained as historically valid for **a different candidate binary**, not silently transferred to the new final FAP.

## Final-label Logger/Profile persistence — operator result (2026-10-17)

Immediately after the targeted exact-final-FAP real-device test checklist, the owner explicitly replied **"hepsi pass"** (all PASS). The accepted checklist was: create a **new short CSV Logger** capture and open the new file from **Log History**; with profile data backed up, **SAVE** to an otherwise empty profile slot, exit/reopen the application and **LOAD** it successfully; leave the existing **S1** profile and earlier CSV files unchanged. **All items: operator-reported PASS.** No prior file deletion, occupied S1 write, firmware flash or update was requested. The reply contains no exact filename, CSV row count, restored-file hash or independent backup/restore proof, and none is inferred. This closes the **normal fresh-write/readback/reopen** storage acceptance for the tested final-label E11 FAP, but not destructive media faults or general firmware compatibility.

## Source freeze and build evidence

GitHub read-only comparisons performed on 2026-10-17:
- Tested E11 source `ba379f20fb29369501e1057f570a911f71ac83f8` -> development head after 1 kHz recording `78a3ad2004d318fba816915d89365163c1575ddc`: **no changes under `src/`, `application.fam`, `labmate_10px.png`, or `scripts/patch_momentum_*`**.
- Final-label review source `99cb65d0194dc59d423cfa439c90618ac6b9f114` -> same head: **no production/patch-source changes**. The later edits are test tools, workflows and documentation, not modifications to built production source.
- The repository reports previous matched-source, host and SDK checks in the E11 acceptance documents. This audit independently checked source continuity via GitHub compare; the current session could **not** independently re-read Actions workflow run conclusions (Actions API was unavailable/returned no runs). **Do not claim a fresh CI build on this documentation-only head.**

## 2026-10-17 — public release immutability and source-freeze gate (READ ONLY)

An independent live GitHub connector read compared the **actual** public
release/tag endpoints against historical pinned identity (no device or
release mutation):

- `v1.4` tag still targets `84e1d8979d0631c003f9ae5f3e25596f9cb496e6`;
  published `labmate-v1.4.fap` SHA256 remains
  `b5be0a27709ea2c4fe8d63269404d50a4e7d8863c1e8e773063764f9f607cf25`,
  and the two original asset sizes/hashes match the pinned release.
- `v1.8` tag still targets `02b05639364d6dd71f5eb70456eca379c59218cb`;
  published `labmate.fap` SHA256 remains
  `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`,
  and the two original asset sizes/hashes match the pinned release.
- `99cb65d0194dc59d423cfa439c90618ac6b9f114` to branch HEAD
  `a3c6b946082e21ad4552f52eeedbbe9a53ebcd80`:
  GitHub comparison returned 103 commits / 43 changed-file records,
  no `src/`, `application.fam`, `labmate_10px.png` or
  `scripts/patch_momentum_*` production/patch-source path changes.
  Draft PR #13 remains open. The compare payload is below its file/commit
  pagination limits; this is a read-only source continuity finding.

**New prevention control (development branch only):**
`scripts/check_v18_e11_public_release_preservation_ro.py`,
`tests/test_v18_e11_public_release_preservation_ro.py` and
`.github/workflows/check-v18-e11-public-release-preservation-ro.yml`.
The runner, when available, fetches live tags/releases and a bounded
source comparison from GitHub, tests malformed/modified release evidence,
and uses local `git diff` on the exact pinned source tree. It performs
**no merge, tag edit, GitHub release creation, firmware write or upload**.
The independent live read-only GitHub inspection above **PASSed**;
the new Python test suite and Actions workflow conclusion were
**NOT independently executed/verified by this session**, since live
Actions readout was unavailable. Do not mislabel authored tests as
completed CI evidence. A future changed production code or released
asset must fail this historic-preservation gate.

**Scope limit:** preserving old releases and the E11 source is not a
firmware installation plan, ABI attestation for other devices, exact
custom-firmware restore rehearsal or owner approval for replacing the
public v1.8 Stable asset. Those safety blockers stay OPEN.

## Explicit remaining gates before replacing public v1.8

1. **Custom-firmware distribution/restore plan — BLOCKER.** Decide a supported, recoverable installation route for *both* patched Momentum firmware/native resources and exact final FAP, with device-specific compatibility/rollback proof. A FAP-only universal Stable update is prohibited by current ABI evidence. Backup *availability* is not a restore rehearsal.
2. **Storage regression — CLOSED at operator-reported functional scope (2026-10-17).** After the explicit scratch-only test request, the owner replied `hepsi pass` for new short CSV Logger recording, opening it from Log History, backing up profile data, saving in an empty profile slot, reopening and loading the saved profile, and preserving existing S1 and historical CSV files. This is a real-device owner-reported PASS on the installed E11 final-label FAP; no path-by-path readback/hash transcript, filename/row-count or independent backup restore rehearsal is claimed. Exceptional full/corrupt SD and rollback remain deferred.
3. **Final release provenance and change control — BLOCKER.** Revalidate the exact binary pair, signed/hash-pinned release source and native ABI; decide how historical public `v1.8` tag, existing Stable FAP, and rollback are preserved. No overwriting a historical Stable artifact or retargeting the old tag by implication.
4. **Full compatible release acceptance/approval — BLOCKER.** Owner must explicitly accept the scoped installed-firmware compatibility and remaining functional/storage gates before merge, tag or publish. CI green cannot authorize device writes or remove release gates.
5. **Documented intentional deferrals — NOT PASS:** real H1 concurrent native PA7 BUSY (CLI `loader_lock` prevented exercising this), positive I²C device ACK, external 3.3 V DS18B20, independent timing/electrical calibration and STOP voltage, mechanical button bounce, exceptional microSD fault/restore, third-party/legacy DMA/IRQ/timer overlap and other listed fixtures in `docs/DEFERRED_HARDWARE_TESTS.md`. Leave these open rather than asserting universal safety.

## Decision and continuity

**The final-label E11 digital PWM/STOP–RESTART physical subset and normal fresh CSV Logger/Profile SAVE–reopen–LOAD subset are closed as owner-reported PASS. The broad E11 supported-software implementation and scoped final-FAP functional observations are accepted at their actual evidence level. Public Stable promotion is NOT approved or completed.**

Preserve `main`, historical releases including v1.4, published `v1.8` Stable/tag/assets, the on-device working custom E11 firmware/FAP and backups. Keep [PR #13](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/13) as **DRAFT**. Do not start v1.9 by silently declaring remaining safety/release gates complete. Avoid further hazardous/irreversible device work just to close a checklist.
