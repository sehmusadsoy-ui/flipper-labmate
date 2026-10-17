# LabMate v1.8 — original-scope completion, final-label candidate (DRAFT / NOT RELEASED)

**Status:** Review text only, **not** the already published v1.8 release notes.
**Stable asset today:** Existing v1.8 from 2026-10-14 remains authoritative
until a separately accepted new exact paired firmware/FAP release.
**Source branch:** `dev/v1.8-completion` · Draft PR #13.
**Current exact final-label acceptance (2026-10-17):** A single
SHA256-pinned `v1.8` final-label E11 FAP has now been installed and
physically tested on the owner's already-matched custom E11 Momentum
firmware after a separate guarded FAP-only authorization. Repository
production source retains the `v1.8DEV` macro; the label was built in
disposable CI staging. This is not a stock-Momentum/general Stable
download or permission to flash a firmware updater. Historical public
`v1.8` assets remain unchanged.

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
- **Exact installed final-label FAP UART 115200:** ESP32-S2
  `ESP32_READY`, `ESP32_OK`, ST2 command/stress trigger,
  `BURST_END` and UART STOP/BACK/resource return were operator-reported
  PASS. The most recent `ESP32_OK` was not independently
  timestamp-linked to the last AT and no new byte-loss benchmark exists.
- **Exact final FAP PWM:** PA7→PC1 digital loopback at 100 Hz / 50% and
  1 kHz / 50%, Frequency/Pulse, STOP/RESTART/BACK user-reported PASS.
  This is not independently calibrated output or a voltmeter OFF check.
- **Exact final FAP storage:** new short CSV Logger capture opened from
  History, backed-up empty-slot Profile SAVE/reopen/LOAD and preservation
  of old S1/CSV reported ALL PASS by operator. No file-by-file restore
  rehearsal or independent hash transcript was supplied.

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
- Exact-candidate core UART, digital PWM and isolated Logger/Profile
  functional device acceptance is now operator-reported PASS. The H1
  native concurrent ownership, real I2C ACK/DS18B20, instrument-grade
  calibration, exceptional SD recovery and firmware rollback remain
  OPEN / deferred, not PASS.
- Obtain the owner's specific in-place v1.8 Stable update and
  immutable history/source-tag policy approval, with an evaluated
  firmware/resource compatibility and fallback plan.
- **No PR merge, published asset/tag change, Stable install, firmware
  flash or v1.9 milestone start** on this draft.

References:
[E11 paired device evidence](V1_8_E11_FIRST_LIVE_BOOT_AND_SMOKE_2026-10-17.md),
[H1 exact accepted boundary](V1_8_E11_H1_CLOSEOUT_DECISION_2026-10-17.md),
[release readiness and mandatory gates](V1_8_E11_RELEASE_READINESS_2026-10-17.md).

## Exact final-label **review-only** candidate evidence (2026-10-17)

- Full matched Momentum + single FAP / JS module and update
  archive [Actions #39035056937](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39035056937)
  completed **SUCCESS**, commit
  `99cb65d0194dc59d423cfa439c90618ac6b9f114`.
- Candidate `labmate.fap` SHA256:
  `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`.
  Candidate `firmware.dfu` SHA256:
  `e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b`.
  Native `js_gpio.module` SHA256:
  `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a`.
- Independently downloaded historical device-tested E11 bundle and
  new candidate bundle, [read-only compare Actions #39040017389](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39040017389)
  **SUCCESS** (13/13 negative/positive fixtures): native JS
  plugin bytes identical; the old and candidate DFUs differ only
  at embedded build date `16-10-2026` → `17-10-2026`
  and the validated inverted CRC suffix. This is a strict
  offline DFU bytewise-delta finding, **not actual on-device
  firmware binary readback**. Candidate FAP differs as expected
  from the original `v1.8DEV` trial and requires its own
  bounded on-device acceptance.
- The reviewed final-label archive is
  `v18-FINAL-LABEL-E11-PAIRED-REVIEW-DO-NOT-FLASH`
  (Actions artifact ID `12101802257`, temporary). It is
  **not** a public Stable download, installer, or authorized
  firmware write.

**Subsequent device outcome (2026-10-17):** The owner separately
authorized a guarded FAP-only replacement against the working,
already-matched E11 custom firmware. It completed; the previous FAP
and PC backups were retained. The final-label UART/PWM/storage device
observations above followed. This does NOT authorize a full firmware
update, rollback, public Stable edit, PR merge or tag move. This
device-specific route cannot be repurposed for stock MNTM-012.
