# LabMate v1.8 E11 — distribution scope and restore boundary (2026-10-17)

**Decision: EXACT EXISTING-DEVICE E11 FUNCTIONAL ACCEPTANCE PASS; UNIVERSAL / PUBLIC STABLE REPLACEMENT NO-GO.**
This is a release-planning record, not an installer or permission to write the Flipper, merge PR #13, move any tag, or replace public assets.

## Actual tested identities must not be conflated

| Package / environment | Evidence and scope | Distribution status |
| --- | --- | --- |
| Public original `v1.8` (2026-10-14) | Source tag `02b05639364d6dd71f5eb70456eca379c59218cb`; released `labmate.fap` SHA256 `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0` | **KEEP PUBLISHED AND UNCHANGED** |
| Original `v1.4` Stable | Source tag `84e1d8979d0631c003f9ae5f3e25596f9cb496e6`; released FAP SHA256 `b5be0a27709ea2c4fe8d63269404d50a4e7d8863c1e8e773063764f9f607cf25` | **KEEP PUBLISHED AND UNCHANGED** |
| Expanded **exact final-label E11 FAP** | SHA256 `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`. Installed on **one already-matched custom E11 Momentum device** after a separately authorized guarded FAP-only step. Operator-reported UART, UI, 100 Hz / 1 kHz PWM/STOP/RESTART, and isolated CSV/Profile persistence PASS. | **Device-scoped verified trial ONLY; not universal public Stable** |
| Review-matched E11 firmware | Final-label review `firmware.dfu` SHA256 `e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b`; native `js_gpio.module` SHA256 `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a` | **Pinned offline build, NOT byte-identical live firmware readback or rollback proof** |

## Installation route decision

1. **Normal stock / unrelated Momentum firmware + expanded E11 FAP alone: NO-GO.** The E11 I2C timeout/native resource-owner path requires patched exported native firmware ABI and matching resources. Do not present the new FAP as a universal drop-in `labmate.fap` or expose it through the existing Stable auto-installer.
2. **Already-matched custom E11 firmware + exact final-label E11 FAP: limited physically tested state.** This is what the owner tested. The historical prewrite identity, SHA-pinned PC backup, native resource MD5 checks, guarded FAP-only replacement and function acceptance are recorded in `V1_8_E11_FINAL_FAP_ONLY_TRIAL_DECISION_2026-10-17.md`. This observation does not establish compatibility for another user's firmware image or license a repeated write.
3. **Full matched E11 firmware/resource updater to other devices: NO-GO.** The installed old `/ext/Manifest` deletes listed resources during firmware updates, including prior `apps/Tools/labmate.fap`; the reviewed FAP-excluded derivative leaves a stale new Manifest reference. The original full archive contains a compatible FAP, but old firmware/app/third-party resource replacement, power failure and exact rollback are not proved safe. Do not flash or offer the split package.
4. **No-install source, documentation, native tests and review-only CI artifacts: allowed.** These must retain visible NO-FLASH/NO-PUBLIC-STABLE language and cannot claim device compatibility.

## Recovery is three distinct questions

- **FAP-only rollback on the currently matched E11 firmware:** prior device application retained as `/ext/apps/Tools/labmate.e11-pre-final.bak` and SHA-backed PC backup. Presence and hashes support a recovery *plan*, but do not prove a restored app boots or that future installed firmware is compatible. No automatic restore.
- **Firmware functional fallback:** official Momentum MNTM-012 updater is recorded with its own checksum; it is **not the previously running `mntm-dev dirty` custom firmware** and can change plugin API, settings and SD resources. No functional fallback rehearsal has been accepted.
- **Exact byte-identical restore of previous custom firmware and its live settings:** **NOT DEMONSTRATED.** A source-base hash or a four-byte DFU build-date delta cannot substitute for an independently authenticated actual installed firmware image or proven recovery.

## Concrete release gate (fail closed)

Before any **new** public artifact, installer, merge, release note or general Stable replacement is approved:

- Pin actual target firmware ABI/native resources, one exact FAP checksum, source commit, update Manifest inventory and installation scope; independently validate package contents and target compatibility.
- Demonstrate device-specific recoverability of the proposed distribution route, including a separately approved *tested* rollback/recovery procedure and preservation of the original LabMate CSV/Profile data. Do not use a generic MNTM-012 fallback as an exact restore claim.
- Preserve historical `v1.4` and existing `v1.8` tags/assets. No silent retag, no `v1.8.1`, no alternative demo FAP. Any future strategy for an explicitly limited compatibility channel needs separate owner review and transparent labeling; this record grants no publication approval.
- Obtain exact-source/byte CI checks (not merely authored workflows), explicit release-scope approval and an accurate disclosure of all intentionally deferred H1, I2C ACK, DS18B20, external calibration and exceptional hardware paths.

**Current safe outcome:** Keep the already functioning user's matched E11 FAP/firmware in place, retain verified PC and on-device backups and existing public Stable. All routine final-label functional gates already reported PASS remain closed. Do not require another full firmware flash merely to complete release paperwork.

**Evidence:** [final release gate](V1_8_E11_FINAL_RELEASE_GATE_2026-10-17.md) · [firmware recovery review](V1_8_E11_FIRMWARE_RECOVERY_DECISION.md) · [installation route manifest audit](V1_8_E11_INSTALLATION_ROUTE_DECISION.md) · [deferred physical hardware queue](DEFERRED_HARDWARE_TESTS.md).
