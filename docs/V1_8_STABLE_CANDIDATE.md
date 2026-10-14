# LabMate v1.8 — Single-App Stable Candidate Acceptance

**Decision: 2026-10-14 — operator-authorized scope deferral.**
**Status: RELEASED — [v1.8 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) published 2026-10-14. RC1 15/15 + exact final FAP 4/4 operator-reported physical PASS; compiled binary, checksum, USB install and published release assets VERIFIED.**
This is the *actual* `labmate.fap` built from `src/*.c`, not a UI demo
or separate tool application. All planned release gates were satisfied
before GitHub Stable publication. The previously published v1.7 Stable
is preserved for rollback.

## Release scope — only implemented, useful features

- Retain all v1.7 Stable instruments: GPIO Monitor, Frequency Meter,
  Pulse Analyzer, PWM Studio, Event Counter, Button Analyzer, Threshold
  Alerts, Data Logger, Log History and Profiles. Preserve original
  capture/resource policy, pin rules, SD records and saved profiles.
- Retain v1.8 app modularization, unified capture/STOP resources,
  Counter STOP/RESUME integration and the **real integrated UART
  Terminal** in COMM: 9600/38400/115200 baud, bounded RX queue and
  display, 12-character editable TX, explicit STOP/BACK and USART
  ownership/refusal. Hardware UART test results (user-reported)
  are recorded in `docs/V1_8_UART_ACCEPTANCE.md`.
- ONE FAP installed at exactly `/ext/apps/Tools/labmate.fap`.
  RC label `v1.8RC1` until accepted; `v1.8` only upon release.
- License attribution `Sehmus (SauronLAB)` maintained.

## Explicitly deferred, not falsely completed

**I²C Explorer — DEFERRED, NOT AVAILABLE IN THIS RELEASE.**
Momentum upstream external I²C acquisition uses a resource mutex
waiting with `FuriWaitForever`. The normal public external SDK does
not currently expose a verified bounded/cancellable acquisition
contract. An app-side mutex, casual pin-state read, speculative
borrowed internal pointer or force-killed blocked worker does NOT
provide bus ownership/cancellation. Its Draft PR #8 models and
standalone demos are not part of `labmate.fap`. The real scanner
was never validated on a 3.3V device. Omit the menu entry entirely
rather than exposing an unusable `HW SCAN DISABLED` placeholder.
Revisit only if an actual safe HAL coordination strategy can be
reviewed and device-tested.

**Optional 1-Wire DS18B20 — DEFERRED, NOT AVAILABLE IN THIS RELEASE.**
PB14 pin is also touched by firmware iButton/RFID facilities, and
no verified firmware-wide atomic pin-owner resource arbiter exists
for an external app. PR #9 decoder/host tests are not evidence of
live sensor integration. No 1-Wire driver, power enable or separate
demo is included. Do not claim sensor temperature readings.

These deferrals are **scope changes approved by the operator** and
must be disclosed in the eventual v1.8 release notes. The original
roadmap aspirations are not misrepresented as completed. No
advancement to v1.9 before actual v1.8 Stable publication.

## Candidate gates

- [x] **C1 PASS — exact source** `d2e3fe8b41599289464db077f1d4a9d26dc442e7` at [run 38482399817](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38482399817), compile job `115587842090` and Windows installer mock job `115587842270` both successful; Stable publishing job intentionally SKIPPED. SDK compiled the real `labmate.fap`, all bundled host regressions and boundary guards passed. Artifact `labmate` ID `11858875740`, source SHA matches run. CI's explicit **FAP file SHA256** `3d33cca37e9c59927e42f101b7cea118677e457eaefae1306aab741999c97d63`; the artifact ZIP digest `5584e52bf3287402ce3c929076f4c2b6340fec0939365103bf320f8a948bba10` is not the FAP hash. No physical USB/Flipper results claimed yet.
- [x] **C2 PASS — final FAP SHA256 and one existing LabMate target (operator terminal log, 2026-10-14 13:06 local).** User downloaded artifact `labmate` from run `38546662091`; local SHA256 matched `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`. First USB attempt at 13:04 showed `100%, chunk 9 of 9`, but stopped with exit code 4 when the already-open LabMate refused `loader close` (must close manually). Following manual exit, the second installer invocation at **13:06** re-verified the exact SHA256, used COM7, targeted only `/ext/apps/Tools/labmate.fap`, printed `Launching app: /ext/apps/Tools/labmate.fap` and `SUCCESS: runfap.py exited 0 and requested app launch.` with process exit code **0**. The device's post-install app contents/label and tool behavior **have not yet been physically rechecked for final v1.8**; installer success is not a substitute for C6 final-device smoke. No duplicate FAP install destination or data deletion was requested.
- [x] **C3 PASS — user-reported on-device Test 18-R1, 6/6**, 2026-10-14:
  R1 app opens + `v1.8RC1` badge; R2 COMM/UART present; R3 UART screen
  RUN/STOP responsive; R4 BACK returns to menu; R5 PWM Studio,
  Event Counter and Records entries present; R6 no I²C or 1-Wire
  placeholder. **This is actual Flipper UI/control evidence, not
  independently captured transaction data or full legacy regression.**
- [x] **C4 — UART basic functionality PASS (operator-reported Test 18-R2,
  4/4), 2026-10-14:** 115200 RX `ESP32_READY`; explicit Flipper TX
  `AT` followed by ESP32 reply `ESP32_OK` (as indicated by operator's
  R2-2 PASS); STOP→RUN returns to receiving; BACK→re-entry responsive.
  **Important: ST2 peer currently installed. `AT` is also the explicit
  stress trigger**: ST2 sends `ESP32_OK` plus `STRESS_ARMED`, then
  begins a bounded burst approximately 1.2 s later (max 20,480
  payload bytes or 2.5 s); a further `AT` during an active test may
  reply `STRESS_BUSY`. The operator additionally clarified that
  sending AT triggers the stress test. This is **not** evidence of a
  new independent burst byte count or physical queue overflow:
  no fresh R/D/E values or `BURST_END` evidence were submitted for
  this RC1. Basic external RX/TX and UI resource recovery passed.
- [x] **C5 PASS — user-reported Test 18-R3, 5/5**, 2026-10-14:
  R3-1 PWM Studio START/STOP; R3-2 Event Counter START/STOP/RESUME;
  R3-3 existing Profiles S1 opens (no edit); R3-4 historical CSV Log
  History entries list/open (no delete); R3-5 no freeze, unexpected
  BUSY or application crash during this smoke. This is a functional
  operator report; no independent calibrated PWM waveform measurement
  or exhaustive SD failure injection is inferred.
- [x] **C6 PHYSICAL ACCEPTANCE PASS — FINAL `v1.8`-LABEL FAP SDK/host CI,
  COM7 checksum-verified install/launch and real Flipper 18-FINAL 4/4 PASS.**
  At source commit `02b05639364d6dd71f5eb70456eca379c59218cb`,
  GitHub Actions [38546662091](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38546662091)
  compiled the actual single `labmate.fap` with Momentum SDK;
  compile job `115794345536` and Windows installer mock job
  `115794345068` PASSED; v1.7 publishing was intentionally SKIPPED.
  Artifact `labmate` ID `11884807062`.
  **FAP SHA256 `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`**
  from the verified FAP file log (not the artifact ZIP digest).
  Code changes since the tested RC1 are **only the on-device version
  label `v1.8RC1` → `v1.8`**, plus the associated static guards;
  historical/device report Markdown updates do not change the FAP.
  The final artifact passed the installer command and requested app launch
  with exit code 0 on 2026-10-14 after manual closure of previous LabMate.
  The operator subsequently reported **18-FINAL F1–F4 all PASS**:
  on-device `v1.8` label, 115200 `ESP32_READY` RX with STOP/BACK,
  PWM START/STOP and Counter STOP/RESUME, and preserved existing
  Profiles S1 and CSV Log History. Thus the **final exact FAP's physical
  smoke acceptance is complete**. The GitHub `v1.8` release and tag
  were subsequently published with exactly the checked binary and
  explicit I²C/1-Wire exclusions and uninstrumented limitations.

## Test 18-R1 — physical device acceptance (operator report 2026-10-14)

The operator submitted: `R1=PASS; R2=PASS; R3=PASS; R4=PASS; R5=PASS; R6=PASS`.
All six first-pass UI/control items are marked **6/6 PASS**, in the
same RC1 sequence following the verified successful CI build. R3 proves
UART RUN/STOP screen control, **not** RX/TX with an external peer.
An earlier PowerShell transcript ended `LABMATE v1.8 RC1 USB INSTALL
COMMAND PASS` but did not include the transfer transcript; do not
claim independently verified USB bytes/port or file contents from
that final line alone. The physical RC1 label is user-reported PASS.
Test 18-R2 external UART 4/4 PASS was subsequently reported;
see below. PWM output validation, Counter STOP/RESUME, Profile storage
and History record rechecks are still pending for this RC1.
Test 18-R3 5/5 and final v1.8 on-device F1–F4 4/4 were subsequently
reported, allowing verified v1.8 Stable publication.

## Test 18-R2 — external UART, 4/4 PASS (operator report 2026-10-14)

Operator report: `R2-1=PASS; R2-2=PASS; R2-3=PASS; R2-4=PASS`.
- R2-1: 115200 baud/RUN, external `ESP32_READY` received.
- R2-2: UART TX editor transmitted `AT` and `ESP32_OK` was
  observed, according to user-submitted PASS for that criterion.
- R2-3: STOP→RUN recovered live UART receive.
- R2-4: BACK→re-enter UART worked without a lock-up.

**Important operator clarification after the PASS report:**
> "tx den at gönderice stres testi açılıyor bu arada"

This is **the existing installed ESP32 ST2 stress peer behavior**, not a
new LabMate feature or a defect by itself. The checked-in firmware
`tests/esp32_s2_wrover_uart_stress_115200/esp32_s2_wrover_uart_stress_115200.ino`
explicitly uses `AT\r\n` to reply `ESP32_OK\r\nSTRESS_ARMED\r\n`,
and ~1200 ms later `BURST_BEGIN`, a bounded stream of at most
20,480 bytes or 2500 ms, and `BURST_END`. Repeating `AT` while
not idle yields `STRESS_BUSY`; no unprompted stress tests run.
This clarifies that the recent R2-2 was **both conditional UART
reply and stress trigger**; do not classify it as a reply-only
test. No new measured stress-byte total or R/D/E snapshots for this
RC1 were submitted; do not claim an RC1 physical DROP test.
The historical ST2 result (2026-10-13) remains a separate,
previous-device-build observation (R=20,569 then 41,281, D=0 E=0)
and should not be conflated with this RC1 pass.

**Current device acceptance:** R1 6/6 + R2 4/4 functional items PASS
(operator-reported). C5 current RC1 regressions and final C6 Stable
source/binary/device acceptance still outstanding.

## Test 18-R3 — existing instrument regression, 5/5 PASS (2026-10-14)

User's exact operator report:
`R3-1=PASS; R3-2=PASS; R3-3=PASS; R3-4=PASS; R3-5=PASS`.
Mapping to the five previously prescribed checks:

- R3-1 PWM Studio START / STOP: PASS.
- R3-2 Event Counter START / STOP / RESUME: PASS.
- R3-3 Profiles existing S1 opens without modifying saved values: PASS.
- R3-4 previously saved CSV Log History entries list and open without
  deletion: PASS.
- R3-5 no freeze or unexpected error while checking these: PASS.

**RC1 physical functional acceptance: 18-R1 6/6 + 18-R2 4/4 +
18-R3 5/5 = 15/15 user-reported PASS.** No claim of independent
waveform calibration, synthetic SD failure tests or fresh ST2 R/D/E
burst statistics. **At this R3 checkpoint**, the final `v1.8`-label
binary still required separate validation; C6 later passed and the
identical checksum-verified binary was published as Stable.

## Final-labeled FAP handoff (completed, v1.8 Stable published)

- **Actual candidate artifact:** GitHub Actions run
  [38546662091](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38546662091),
  artifact name `labmate`, `labmate.fap` and `SHA256SUMS.txt`;
  source commit `02b05639364d6dd71f5eb70456eca379c59218cb`.
- **Exact verified FAP SHA256:**
  `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`.
  Keep separate from the GitHub artifact ZIP SHA256.
- **Next gate:** checksum-confirmed install replaces only
  `/ext/apps/Tools/labmate.fap` (never demo or duplicate);
  on-device label `v1.8`, COMM UART 115200 RX/TX and STOP/BACK,
  PWM STOP, Counter STOP/RESUME, existing Profiles S1 and CSV History.
  Do not delete user data.
- **18-FINAL now PASS**: user-submitted `F1=PASS; F2=PASS; F3=PASS; F4=PASS` on
  the exact final installed `v1.8` FAP; no fresh AT-triggered stress test
  or independently calibrated waveform validation claimed.
- **Release control COMPLETE:** physical acceptance and GitHub Stable
  publication completed 2026-10-14. Only the SHA256-verified final
  artifact/checksum were published, with explicit deferrals and exact
  source provenance.

## Final-label v1.8 USB handoff — checksum/install PASS (2026-10-14)

User supplied the real PowerShell transcript: SHA256 VERIFIED, first
COM7 invocation transferred 9/9 chunks but exited with error 4 because
LabMate was still open (`has to be closed manually`). This first run
is **FAIL** as an installer run and is never counted as a PASS. After
closing LabMate manually, a second invocation verified the same SHA256,
used the existing `/ext/apps/Tools/labmate.fap` destination, printed
`Launching app` and returned exit code 0 (`SUCCESS ... requested app launch`).
The separate `LABMATE v1.8 INSTALL COMMAND PASS` message is consistent
with the captured zero exit code, unlike the earlier user-authored
`Write-Host` in the failed first run.

The installation/launch success alone was not proof of app behavior,
but the operator then submitted the final Flipper test results on the
installed binary: **18-FINAL F1–F4 4/4 PASS**. No separate post-flash
FAP readback hash or independently calibrated waveform test was provided;
this is a verified-source plus operator-reported physical acceptance.

## Test 18-FINAL — exact final `v1.8` FAP on-device PASS 4/4 (2026-10-14)

Operator's exact report after checksum-verified COM7 final FAP installation:
`F1=PASS; F2=PASS; F3=PASS; F4=PASS`.

- **F1 PASS**: Launching the final installed app displays `v1.8`.
- **F2 PASS**: COMM/UART at 115200 receives `ESP32_READY` and STOP/BACK work.
  No fresh stress trigger was required or reported in this final check.
- **F3 PASS**: PWM Studio START/STOP and Event Counter STOP/RESUME work.
- **F4 PASS**: Saved Profile S1 and previously logged CSV History are preserved.

**Release acceptance basis:** full RC1 functional smoke 15/15 user-reported
PASS + final-labeled FAP 4/4 user-reported PASS + true Momentum SDK build and
SHA256 verification + successful existing-target USB installation (exit 0).
User-approved exclusions: I²C Explorer and optional 1-Wire are NOT delivered;
physical UART D>0 drop, independent measurement calibration and exhaustive
storage failure tests are NOT claimed. The separately executed GitHub
v1.8 publication is now VERIFIED and did not precede physical acceptance.

## GitHub v1.8 Stable — publication verified 2026-10-14

- **Release:** [LabMate v1.8 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8)
  is public, `draft=false`, `prerelease=false` and the latest Release.
- **Tag immutability:** `v1.8` references exact tested source commit
  `02b05639364d6dd71f5eb70456eca379c59218cb`.
  The PR #11 merge changed only documentation compared to that compiled
  source; post-merge [CI 38548200859](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38548200859)
  independently produced the **same** `labmate.fap` SHA256.
- **Publishing CI:** [one-time run 38548634392](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38548634392)
  PASS, including source/CI guard, selected artifact download,
  SHA256 verification, publication, GitHub tag checks and an actual
  second download/verification of the published release assets.
- **Assets:** exactly `labmate.fap` (65,580 bytes; GitHub digest
  `sha256:119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`)
  and `SHA256SUMS.txt`, both uploaded.
- **Historical preservation:** published v1.7 tag/release and
  earlier Stable assets remain untouched. The verified v1.8 FAP
  is already installed on the operator's Flipper; no reinstall needed.
- **Sequential gate:** v1.8 is officially CLOSED as Stable and v1.9
  may proceed in normal integrated LabMate development. Unresolved
  I²C/1-Wire hardware ownership remains explicitly deferred, not PASS.

## Removing old demonstrations (not required for build)

Do NOT remove `/ext/apps/Tools/labmate.fap`. Existing standalone
optional test FAPs, if installed, can be removed independently:
`labmate_i2cuipreview.fap`,
`labmate_scopeuipreview.fap`, and
`labmate_busydiag.fap` (historical UART busy probe).
The user may also have downloaded ZIP/FAP demo files in Windows
`%TEMP%`; downloading an artifact did not install it on Flipper.
Do not erase SD profiles, CSV logs, `/ext/apps/Tools` directory
or all FAP files. See the exact-name cleanup instructions in chat,
or use a trusted Flipper/qFlipper file browser.
