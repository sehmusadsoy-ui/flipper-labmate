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

## Test 18-R1 — physical device acceptance (operator report 2026-10-14)

The operator submitted: `R1=PASS; R2=PASS; R3=PASS; R4=PASS; R5=PASS; R6=PASS`.
All six first-pass UI/control items are marked **6/6 PASS**, in the
same RC1 sequence following the verified successful CI build. R3 proves
UART RUN/STOP screen control, **not** RX/TX with an external peer.
An earlier PowerShell transcript ended `LABMATE v1.8 RC1 USB INSTALL
COMMAND PASS` but did not include the transfer transcript; do not
claim independently verified USB bytes/port or file contents from
that final line alone. The physical RC1 label is user-reported PASS.
No fresh external UART traffic, PWM output validation, Counter
STOP/RESUME, Profile storage or History record recheck has yet been
reported for this RC1. Stable publication remains blocked by C4/C5/C6.

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
