# LabMate v1.8 original-scope completion — E11 release readiness audit (2026-10-17)

**Decision:** **E11 SOURCE / SUPPORTED-SOFTWARE PHASE ACCEPTED; FULL STABLE UPDATE NOT READY.**

**Latest storage gate update (2026-10-17):** On the actually installed E11 final-label v1.8 FAP, the operator reported **ALL PASS** for new scratch CSV Logger recording, open from Log History, backed-up empty-slot Profile SAVE, reopen/LOAD persistence, preservation of occupied S1 and historical CSV files. This supersedes earlier lines below describing new Logger/Profile persistence as still pending; those remain historic snapshots at the time originally written. Exact file IDs/row counts/hashes and physical backup restore were not supplied; no independent file attestation is inferred. The storage **normal functional acceptance is CLOSED at operator-report level**. **Full public Stable update is still NO-GO** until safe matched Momentum firmware/native resources distribution and actual rollback, final provenance/change control and owner release authorization. See [current authoritative release gate](V1_8_E11_FINAL_RELEASE_GATE_2026-10-17.md).


**Branch:** `dev/v1.8-completion` — [Draft PR #13](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/13).
**Current published Stable:** `v1.8` (2026-10-14) is preserved, released from
`02b05639364d6dd71f5eb70456eca379c59218cb` with
`labmate.fap` SHA256
`119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`.
The *original-scope restoration* in this working branch is a later
development candidate and **not the same published application binary**.

## Explicit operator decision, 2026-10-17

The operator agrees to **defer H1's on-device simultaneous second-client
PA7 arbitration test** and tests requiring unavailable safe physical
accessories/instruments until those can be performed on their own
Flipper. Host implementation/regression and actually exercised
on-device functional checks remain valid, with their exact scope.
A deferred check is **PENDING, NOT PASS**; this is not authorization
to eliminate a supported function, bypass Momentum loader protection,
alter firmware/global device state, overwrite stored profiles/CSV,
replace a Stable release asset, merge the draft PR, or start v1.9.

The decision is **specific to equipment/method-limited acceptance**,
not a blanket waiver of source-integrity, actual supported
functionality, compatibility, data-preservation or release-version
requirements. Any remaining release gate that can be safely
completed without extra equipment must still be reviewed.

## Freeze/provenance comparison — source unchanged after deployed E11 pair

- Source commit of the reviewed FULL paired E11 firmware/FAP and
  actually used operator device trial:
  `ba379f20fb29369501e1057f570a911f71ac83f8`.
- GitHub remote recursive trees were compared for this commit and the
  branch on 2026-10-17: **101 / 101 production file records match
  exactly at Git blob identity**, covering `src/`,
  `application.fam` and `labmate_10px.png`; the existing
  `scripts/patch_momentum_*` source patch files also had **zero
  changes** between those two checked revisions.
- This comparison proves there has been **no later change to those
  production/source patch files** in the development branch.
  It does not attest the entire installed firmware image, or
  imply that added CI/checker/documentation files were present
  in the earlier release artifact.
- Paired trial `labmate.fap` SHA256:
  `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0`.
  Paired native JS GPIO module SHA256:
  `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a`.
  Their remote MD5 readbacks plus Event Loop plugin matched
  independently pinned local source package. Actual firmware
  reports `mntm-dev` / `d3f89dfe` base and is dirty; **no
  byte-for-byte flashed firmware readback SHA is claimed**.

## Honest verified milestone summary

| Original scope | Source and evidence | Release limitation |
| --- | --- | --- |
| v1.5 CSV, History and Profiles | Integrated production-C/CI; Round C older logs and S1 profile opened/browsed read-only on exact paired E11; earlier devices had functional writes | No matched E11 intentional new CSV/profile write/readback or destructive media fault test accepted; never alter existing user data just for QA |
| v1.6 ownership/refactoring | Single integrated app/source, app-local capture/resource guards, supported native E11 lease and host tests PASS | Do not assert exclusive ownership against arbitrary third-party/direct-LL clients; on-device H1 concurrent BUSY not observed |
| v1.7 PWM, Counter, Button, Alerts | E11 A–G PWM, PC1/PB3 loops, Counter TIM2, Button STOP/RESUME all functional PASS; G includes actual displayed HIGH/LOW timing matches | Calibrated oscilloscope OFF/frequency accuracy, physical switch bounce and exceptional edge cases deferred |
| v1.8 UART | Existing published v1.8/earlier development ESP32-S2 UART 3.3 V peer tests and native C regressions are recorded | **No separately documented E11 A–G external UART peer result**; require exact-pair evidence or a separate explicit scoped release decision |
| v1.8 I²C Explorer | Genuine bounded HAL worker/scanner and SDK/FAP software build; E11 A/C BUSY-under-local-PWM and no-device scan UI smoke PASS | Positive ACK from a known-safe 3.3 V I²C peripheral and simultaneous native I²C owner/handoff are still hardware pending |
| v1.8 optional 1-Wire Temp | Real PA4 host/CRC and source/UI implementation, production SDK build; E11 A/C local BUSY and no-sensor UI smoke PASS | Actual DS18B20 scratchpad/CRC/temperature and coexistence with unrelated native owners still hardware pending |
| E11 firmware/global service | Matched firmware/FAP/native plugin CI; native source owner tests; Round F sequential NFC/RFID/IR/SubGHz UI smoke; H0/H2 real native JS PA7 read PASS | Exact firmware binary-image attestation/recovery, unsupported optional/legacy direct-LL actors, third-party plugins, H1 concurrent native BUSY unverified |

**Functional paired E11 totals:** A–G **36/36 operator-reported
controls/functional matches PASS** (not independent instrument
calibration); H0 free-state JS PA7 read PASS; H2 post-STOP
read PASS; PWM RUN persisted after refused CLI probe and explicit
STOP worked. Original-C native PWM / JS claimant / LabMate
common-owner host CI and H1 anti-false-PASS ledger CI
[#39033957528](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39033957528)
**SUCCESS**, but H1 on-device simultaneous `GPIO pin BUSY`
**NOT OBSERVED** because the JS/GPIO commands are stopped by
Momentum `loader_lock()` before executing during LabMate RUN.
See [H1 closeout matrix](V1_8_E11_H1_CLOSEOUT_DECISION_2026-10-17.md).

## Remaining release gates (not automatically waived)

1. **Resolve final-version semantics:** The installed development
   application is a `v1.8DEV` trial; the existing published Stable
   binary is the previous reduced-scope `v1.8`.
   A new production `v1.8` badge, FAP and exact checksum
   must be built/tested as a deliberately reviewed final candidate,
   not renamed or relabeled by paperwork. A change to production
   version text changes the candidate bytes and requires a fresh
   package build and appropriate exact-candidate acceptance.
2. **Ensure matched firmware dependency and release/installer plan:**
   original-scope I²C and E11 native lease code depend on the
   matching custom Momentum exported ABI/resources; **do not
   install the new FAP alone onto unrelated stock MNTM-012**.
   Review updater Manifest deletion/replacement behavior,
   previous working resource backup, exact source/FAP/updater
   and rollback/DFU risk separately. A prior FULL operator
   trial occurred, but it was not an exact rollback rehearsal.
3. **Check feasible core-device regressions on the final matching
   candidate** before final Stable replacement, including UART
   external peer where safe/available and deliberate new-data
   Logger/Profile save/load only on **isolated test media or
   separately authorized new filenames**, never destructive
   operations on historical files. The E11 Round C read-only
   observations alone do not establish fresh write persistence.
   Actual pending negative safety edge cases are NOT inferred
   from all-green host tests.
4. **Equipment/method-dependent tests intentionally deferred by
   the operator:** independent scope calibration (HW-02),
   dry-contact bounce (HW-01), positive I²C ACK HW-06,
   actual DS18B20 HW-07, unusual SD and power faults, actual
   native cross-client H1 and legacy firmware-wide IRQ/TIM/DMA
   service conflicts HW-08..HW-19, Excel QA and other
   applicable cases. They remain on
   [DEFERRED_HARDWARE_TESTS.md](DEFERRED_HARDWARE_TESTS.md).
   They cannot be declared supported, safe in all environments,
   PASS or a release safety guarantee based only on deferral.
5. **Explicit publication decision and immutable history:**
   record exact tested final FAP/build hashes and both prior/new
   release binary digests; do not silently retarget the original
   `v1.8` tag/source. Preserve old release evidence and old
   asset/rollback copy. In-place release asset replacement,
   PR merge and v1.9 start each require appropriate separate
   user review/approval; device trial permission is not
   transferable to a new binary/firmware.

## Safe next engineering task (NO DEVICE OPERATIONS)

Prepare a **non-installing, review-only final candidate gate**
that checks production source continuity, firmware dependency and
release badge/scope, creates an exact source/candidate
traceability table, and **fails closed** when release-candidate
version/package/required functional evidence is missing.
Do not synthesize hardware test outputs, label `v1.8DEV`
as `v1.8` by simply editing documentation, or run installers.

**Current decision: software implementation review ACCEPTED for
supported scope; physical accessory backlog DEFERRED; final
in-place v1.8 Stable upgrade NO-GO until real remaining release
conditions are met and specifically approved.** Existing published
Stable/main/release files are unchanged. No v1.8.1 subrelease.
v1.9 is a separate milestone after the v1.8 original-scope
completion/release decision.

## 2026-10-17 — Full matched v1.8 final-label **REVIEW CANDIDATE BUILD PASS (NO FLASH)**

The source-preserving temporary `v1.8DEV` → `v1.8` label
overlay **completed** in GitHub Actions
[#39035056937](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39035056937):
`completed/success`, exact CI source
`99cb65d0194dc59d423cfa439c90618ac6b9f114`.
This advances release-candidate **compilation/provenance**, not
the on-device Stable/release gate.

- Workflow:
  `.github/workflows/check-v18-final-label-review-pair.yml`
  (an independent no-flash full updater + FAP build).
- Strict source staging:
  `scripts/stage_v18_final_label_review_only.py` compares
  exact tested E11 source `ba379f20fb29369501e1057f570a911f71ac83f8`
  against the checkout, refuses any changed production/runtime
  files/firmware patch scripts, requires exact staged source and
  manifest/icon byte parity, and replaces **only**
  `#define LABMATE_VERSION_TEXT "v1.8DEV"` with
  `#define LABMATE_VERSION_TEXT "v1.8"` in the
  **disposable build folder**. The checked-in app and actual
  Flipper continue to identify as `v1.8DEV`.
- Real CI runs completed: source/overlay negative tests, original
  native Momentum patch tests, FAP `APPCHK`, full firmware/SD
  resource updater compile, strict updater/radio/option-byte
  comparison, embedded DFU coherence, exact
  `SHA256SUMS.txt` and `PROVENANCE.txt` validation.
- **Matched review-only package SHA256** (exact log output):

  | Candidate binary | SHA256 |
  | --- | --- |
  | `labmate.fap` | `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61` |
  | `firmware.dfu` | `e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b` |
  | `js_gpio.module` | `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a` |
  | `firmware-full-update.tgz` | `cd12be2a85512dcd360e6b93e027fa2ad9136a76602ba01036dc235b7a804dee` |

- Exact native source diff SHA256:
  `1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80`,
  matching the prior E11 review source-diff fingerprint.
  The `js_gpio.module` SHA256 is **byte-identical** to the
  operator-tested E11 trial plugin.
- GitHub Actions archived **artifact ID `12101802257`**,
  named `v18-FINAL-LABEL-E11-PAIRED-REVIEW-DO-NOT-FLASH`,
  ZIP SHA256 `2c1aa236e566f784c9b94b1da55b6e572e26e8863aeef84972722d1c0eba36bf`
  as reported by Actions. Artifact is temporary, not an
  installer and not released.
- Source stability review since candidate build: comparison of
  exact CI commit `99cb65d0` and current branch head after
  adding release-note documentation showed **137/137**
  source+manifest/icon+native-patch path entries Git-blob identical.
  Later documentation alone does not change build source.

**Important binary distinction:** New `firmware.dfu`
SHA256 `e7460ab...` differs from previously installed/trial
`88d12fee...`; new `labmate.fap` SHA256
`393fe3...` differs from trial `2b31ec...`.
The native source patch fingerprint being the same does **not**
prove byte-for-byte firmware equivalence or safe cross-pair
FAP-only installation. No cause is assumed for the new firmware
binary delta without a dedicated comparison. Do **not**
flash this review package or swap the FAP into another
firmware environment on this evidence alone.

**Still NOT passed on this exact new binary:**
`v1.8` About/UI startup and exit on a device, new-pair external
UART peer, scratch-only CSV/profile write/re-read under approved
non-user-data scope, fully authenticated running firmware
compatibility and reviewed restore plan. H1 real concurrent
native BUSY, actual I²C ACK/DS18B20 and remaining hardware
fixtures stay **DEFERRED / NOT OBSERVED**, not release acceptance
PASS. Draft PR #13 remains unmerged; currently published
v1.8 Stable/tag/release assets are immutable and unchanged.
**No new device command, install or firmware trial has been approved.**

## 2026-10-17 — Two REAL archived review binaries, independent delta/DFU CRC: **PASS (OFFLINE ONLY)**

CI [#39040017389](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39040017389)
**completed SUCCESS** after 13/13 synthetic positive/adversarial
unit cases. This runner fetched the **actual original matched
E11 DEV user-tested review** artifact
`#38966248325` (artifact ID `12075925371`) and the **actual
new final-label review** artifact `#39035056937`
(artifact ID `12101802257`) from GitHub, in an ephemeral
runner directory only. New exact-source tool:
`scripts/audit_v18_e11_final_binary_delta_ro.py`;
test: `tests/test_v18_e11_final_binary_delta_ro.py`;
workflow:
`.github/workflows/check-v18-e11-final-binary-delta.yml`.
It independently checked both seven-file inventories, four
pinned SHA256s per archive, their own checksum manifests,
two separately pinned Actions IDs/commits, exact Momentum base,
native E11 patch diff fingerprint and `DO NOT FLASH` warnings.

**Measured actual binary deltas (not inferred from SHA alone):**

| Image | DEV device-tested review | Final-label review | Byte differences |
| --- | ---: | ---: | --- |
| `labmate.fap` | 81,532 bytes | 81,528 bytes | 30,624 differing positional bytes including size change; not a binary-equivalent FAP |
| `firmware.dfu` | 846,617 bytes | 846,617 bytes | **Four bytes** |
| `js_gpio.module` | 13,796 bytes | 13,796 bytes | **Zero: binary-identical** |

**Exact DFU analysis:** Among the **846,617-byte DFUs**
there is exactly **one changed content byte** at offset
`750231`, changing the embedded ASCII build date string
`HEAD\0 16-10-2026` to `HEAD\0 17-10-2026`.
All remaining bytes through the start of the 16-byte DFU
suffix agree exactly. Three other changed bytes
(offsets `846613`, `846614`, `846616`) are
within the final four-byte DFU suffix checksum field.
Independent CRC32 complement checks passed on BOTH image
footer values:

- Prior: stored `0x45e65c07`, calculated complement
  `0x45e65c07` — **MATCH**.
- Candidate: stored `0x8ae6a3c2`, calculated complement
  `0x8ae6a3c2` — **MATCH**.

The strict gate rejects any extra DFU payload byte change,
missing exact date stamp, invalid DFU footer checksum,
unmatched JS binary, wrong run/commit/hash, or corrupt
artifact inventory. It is strong **bytewise offline evidence
that these two produced DFUs have no other payload
difference besides embedded build date**; it is **NOT**
proof that the installed device firmware has been read
back byte for byte or that a new FAP has actually booted
and survived full UI/SD/UART acceptance.

**Consequence for next safest operator procedure:**
The final-label FAP is built against the same patched
Momentum native source/firmware payload except date metadata,
and the original device-tested JS module is byte-identical.
Consequently a **reviewed, narrow FAP-only trial against
the already installed E11 custom firmware may be worth
considering**, avoiding a redundant full firmware write.
But this procedure is **NOT YET AUTHORIZED**: re-attest
the exact installed firmware API/custom resources plus
current on-device FAP backup, validate final FAP and
original E11 resource compatibility, obtain fresh explicit
operator approval before **any** FAP replacement, and
record final-label device readback and the actual
UART/Logger/Profile functional gates before considering
Stable publication. Do not call this an established
installation path merely from an offline compare.

**Still NO Stable publication:** original tagged `v1.8`
release binary, provenance and assets are preserved.
Candidate build `v1.8` version macro was changed only in
disposable CI staging; branch source and installed app stay
`v1.8DEV`. PR #13 remains Draft; actual concurrent native
H1 and physical equipment-dependent tests remain explicitly
DEFERRED/NOT PASS.
