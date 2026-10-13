# LabMate v1.8 — Single-App Stable Candidate Acceptance

**Decision: 2026-10-14 — operator-authorized scope deferral.**
**Status: RC1 SOURCE COMMITTED; CI and physical acceptance PENDING.**
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

- [ ] **C1:** GitHub strict host/native regressions and Momentum
  development SDK build PASS at one exact source SHA. Windows installer
  mock PASS. Artifact is named **labmate** and contains **labmate.fap**.
  FAP SHA256 must be taken from the job build log, not the ZIP digest.
- [ ] **C2:** User downloads and SHA256-verifies *labmate.fap*, installs
  by one PowerShell+USB workflow over the **existing**
  `/ext/apps/Tools/labmate.fap` and does NOT create a duplicate.
- [ ] **C3:** Physical Flipper shows RC1 version, previous instrument
  navigation and COMM → UART Terminal; there must be **no unimplemented
  I²C/1-Wire menu placeholder**.
- [ ] **C4:** Device smoke: UART RUN, receive/explicit transmit,
  STOP/BACK and re-entry remain responsive; retest UART 115200
  against the earlier known-good setup when available.
- [ ] **C5:** Regression smoke: PWM starts/stops; Counter
  STOP/RESUME is sane; Profiles and existing CSV History open;
  no unexpected deleted data or resource conflict.
- [ ] **C6:** Final exact-source Stable `v1.8` label/manifest build
  and post-build installation checksum / 4-point device smoke PASS,
  only then tag/publish v1.8 Stable and update README to Stable.
  Source/binary provenance and known exclusions are documented.

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
