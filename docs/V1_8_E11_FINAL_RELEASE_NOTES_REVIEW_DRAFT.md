# LabMate v1.8 — original-scope completion, final-label candidate (DRAFT / NOT RELEASED)

**Status:** Review text only, **not** the already published v1.8 release notes.
**Stable asset today:** Existing v1.8 from 2026-10-14 remains authoritative
until a separately accepted new exact paired firmware/FAP release.
**Source branch:** `dev/v1.8-completion` · Draft PR #13.
**Candidate label:** `v1.8` in a disposable CI copy of the
production-version header; repository source and currently installed
E11 trial retain `v1.8DEV`. Candidate artifacts, if their build
completes, are **DO NOT FLASH / DO NOT INSTALL** until the separate
review and approval process is finished.

## Features present in the current integrated development app

- Existing v1.5–v1.7: GPIO Monitor, low/high Frequency Meter,
  Pulse Analyzer, PWM Studio with adjustable frequency and duty,
  TIM2 Event Counter, Button Analyzer and Threshold Alerts,
  CSV Logger/History and CRC-guarded Profiles.
- v1.8: real UART Terminal with bounded RX/TX and STOP/BACK;
  Counter resume, Button Analyzer STOP/RESUME without resetting
  measured results on normal STOP.
- Restored v1.8 Communication Tools source:
  **I²C Explorer** scan, response paging and cancellable worker
  with a required bounded, patched Momentum firmware HAL;
  **1-Wire Temp** driver targeting safe externally powered 3.3 V
  PA4 DS18B20 with scratchpad/CRC processing and STOP/BACK.
  Actual positive external I²C ACK and DS18B20 sensor temperature
  are **not** verified.
- Root menu order:
  **MEASURE → OUTPUT → RECORDS → COMM → INFO** (About last).
  No `v1.8.1` and no extra demo FAP are part of this candidate.
- Supported native resource owner integration under the exact
  pinned patched firmware, with cooperative GPIO, timers, EXTI,
  selected DMA and UART/I²C/1-Wire conflict paths; absolute
  third-party/firmware-global exclusivity is **NOT** claimed.

## Real matched E11 test evidence and limitations

- A–G **36/36** operator-reported actual-device function/smoke
  observations on the checksum-matched `v1.8DEV` pair, including
  timer/counter/button UI, PC1/PB3 same-Flipper loopback,
  PWM 100 Hz/50%→25% and 200 Hz/75% live retune readbacks,
  records read-only inspection and missing-sensor screens.
- H0 native JavaScript PA7 read while PWM STOP: **PASS**.
- H1 PWM remains RUN despite an attempted competing CLI command,
  explicit owner STOP: **PASS at UI control level**.
  **Actual simultaneous native JS `GPIO pin BUSY` refusal: NOT
  OBSERVED** because the pinned Momentum CLI application loader
  lock prevents launching a default-flagged `js` command while
  LabMate is open. The real original-C PWM/JS/LabMate ownership
  host regression passes, but is not a substitute for a live
  conflicting native client.
- H2 JS PA7 read after operator STOP and app exit: **PASS**.
- Independent calibrated output and OFF voltage, real mechanical
  switch bounce, positive I²C slave address/ACK, actual
  3.3 V DS18B20 conversion, exceptional microSD/storage power-loss,
  obscure native plugin/IRQ/DMA overlap, physical RF coexistence,
  Excel import and exact firmware rollback remain
  **DEFERRED/UNVERIFIED**, not PASS. See
  [equipment backlog](DEFERRED_HARDWARE_TESTS.md).
- Earlier ESP32-S2 UART physical checks and v1.8 Stable UART
  regression are valid history, **not an exact new E11
  paired external-UART smoke result**.
  Round C History/Profile **read-only** success is not an
  intentional new write-and-readback test on the current pair.

## Installation and compatibility — IMPORTANT

**This draft offers no installation instructions or approved binary.**
The I²C cancellation and E11 ownership paths use a
**specific matched custom Momentum firmware export ABI**
and its matching native resources/plugins. Installing the new FAP
onto an arbitrary stock `mntm-012` build can fail to load or be
unsafe; a FAP-only update is NOT an accepted migration method.
The original FULL firmware updater can change SD application
resources, manifest cleanup scope, radio and option-byte policy.
An existing firmware/FAP installation trial and local backups do
**not** prove successful exact rollback/restore, and no new updater
trial is authorized merely by a green CI build. Preserve older
v1.8 Stable, v1.7 release, existing CSV/Profile data and PC backups.

## Remaining final release acceptance

- Check production candidate `v1.8` badge, exact FAP/firmware/native
  plugin hash/provenance, one-app packaging, source equivalence and
  test-only artifact identity.
- Separately accept an actual exact candidate on device and
  feasible core UART and scratch-only Logger/Profile persistence,
  or explicitly scope unresolved requirements without mislabeling
  them hardware equipment deferrals.
- Obtain the owner's specific in-place v1.8 Stable update and
  immutable history/source-tag policy approval, with an evaluated
  firmware/resource compatibility and fallback plan.
- **No PR merge, published asset/tag change, Stable install, firmware
  flash or v1.9 milestone start** on this draft.

References:
[E11 paired device evidence](V1_8_E11_FIRST_LIVE_BOOT_AND_SMOKE_2026-10-17.md),
[H1 exact accepted boundary](V1_8_E11_H1_CLOSEOUT_DECISION_2026-10-17.md),
[release readiness and mandatory gates](V1_8_E11_RELEASE_READINESS_2026-10-17.md).
