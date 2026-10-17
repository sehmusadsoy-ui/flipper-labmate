# LabMate v1.8 original-scope completion — E11 release readiness audit (2026-10-17)

**Decision:** **E11 SOURCE / SUPPORTED-SOFTWARE PHASE ACCEPTED; FULL STABLE UPDATE NOT READY.**
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
