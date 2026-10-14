# LabMate v1.8 — Single-App Stable Candidate Acceptance

**Decision: 2026-10-14 — operator-authorized scope deferral.**
**Status: RC1 exact-source CI PASS; physical acceptance PENDING.**
This is the *actual* `labmate.fap` built from `src/*.c`, not a UI demo
or separate tool application. Do not publish Stable while a required
gate remains open. The existing immutable published v1.7 Stable is
preserved for rollback.

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
- [ ] **C2:** User downloads and SHA256-verifies *labmate.fap*, installs
  by one PowerShell+USB workflow over the **existing**
  `/ext/apps/Tools/labmate.fap` and does NOT create a duplicate.
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
- [ ] **C6:** Final exact-source Stable `v1.8` label/manifest build
  and post-build installation checksum / 4-point device smoke PASS,
  only then tag/publish v1.8 Stable and update README to Stable.
  Source/binary provenance and known exclusions are documented.

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
Test 18-R3 5/5 PASS was subsequently reported. Stable publication
remains blocked by the final exact-source/binary and device gate C6.

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
burst statistics. **Do not publish yet:** the final `v1.8`-label
binary is different from the RC1 FAP and must itself pass exact
source SDK/host CI, checksum check, USB installation, and a distinct
last-device smoke before Stable publication (C6).

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
