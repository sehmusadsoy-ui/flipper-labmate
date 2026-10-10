# Changelog

## [1.6] - 2026-10-10 (Stable)

### Architecture, resources and navigation
- Released LabMate v1.6 Stable on GitHub from the verified
  `4a890002fea0acf8d524b7c772db3bbd3e239848` source snapshot;
  `v1.5` remains downloadable.
- Added grouped MEASURE / OUTPUT / RECORDS / INFO navigation, and
  modular view, GPIO resource policy and profile codec files.
- Protected the PA7 Generator PWM pin from conflicting monitoring
  while RUN, with release on STOP and application exit.

### Frequency, Pulse and saved Profiles
- Corrected HIGH PB3 TIM2 low-rate estimation via adaptive
  edge-aligned gating; real-device generator checks passed at
  1, 2, 10 Hz and 1, 5, 10, 20, 50 kHz.
- Retained precise LOW PC1 capture; confirmed Pulse Analyzer PC1
  100 Hz and 1 kHz HIGH/LOW/PERIOD/DUTY, STATS MIN/MAX and HOLD.
- Added three CRC32-protected, redundant A/B microSD Profile slots
  with SAVE/LOAD/DELETE, confirmation/cancel and preserved settings;
  LOAD refuses active PWM and does not start an output.

### Logging, verification and limitations
- Rechecked CSV Data Logger and Log History on PC1 LOW, PB3 HIGH
  and PULSE PC1, including old files after reopening LabMate.
- Real Flipper RC1 and final v1.6 smoke checks passed; Momentum SDK,
  native-C unit tests, SHA256 packaging and Windows mock transport
  passed [GitHub Actions run 38007158577](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38007158577).
- Self-measurements using Flipper's own generator are not independent
  calibration; full/corrupt/absent-SD and sudden power-loss testing
  remain unverified. See [v1.6 release notes](RELEASE_NOTES_v1.6.md).


## [1.5] - 2026-10-09

### Data Logger and Log History
- Added microSD CSV recording for low-frequency PC1, high-frequency PB3 and pulse PC1 measurements, sampled once each second.
- Added START/STOP and BACK-to-save, unique non-overwriting log filenames, periodic sync, and read-only browsing of up to 32 recent log files.
- Reduced repeated START/STOP stalls by moving file-system operations outside the GUI mutex; cleaned up file handles after unsuccessful opens.
- Kept all four existing tools. Regression checks were user-confirmed on Flipper hardware; ten-minute/600-row PC1 logging, PB3 1/20/50 kHz samples, pulse samples and signal-loss recovery were tested.
- Imported a sample CSV successfully with LibreOffice Calc; Microsoft Excel has not been independently verified.

### Stable acceptance and limitations
- The user confirmed final v1.5-dev checks: development labels match in menu/About, USB-connected STOP/save, BACK-to-save and opening both new files in Log History.
- Final stable-labeled source displays v1.5 in the main menu and About. The Stable publishing workflow verifies the final FAP, checksums, source commit and Momentum SDK provenance.
- Real microSD fault recovery, simultaneous host writes to a live CSV, Microsoft Excel import and external-reference calibration remain unverified; see [v1.5 Stable release notes](RELEASE_NOTES_v1.5.md).

## [1.4] - 2026-10-08

### Frequency Meter
- Added live MIN/MAX statistics for LOW/PC1 and HIGH/PB3, with UP reset and HOLD/LIVE history preservation.
- Preserved history across signal loss, but reset on entering a new measurement session or changing input modes.
- Fixed value formatting so live readings and MIN/MAX truncate consistently at Hz/kHz boundaries.
- Added breathing room after the MAX label.

### Pulse Analyzer
- Added a separate HIGH, LOW, PERIOD and DUTY MIN/MAX page (UP to toggle, DOWN reset).
- Preserved history across HOLD/LIVE; retained the v1.3 IRQ capture and live measurement path.
- Added a five-snapshot median filter for high-speed Pulse MIN/MAX statistics to reduce transient outliers.
- Refined labels, row spacing and footer layout to avoid overlapping 128x64 text.

### Stability and tests
- Reduced unnecessary redraws in non-Pulse views, improving USB-connected menu stability.
- On-device loopback checks at 1 kHz, 20 kHz and 50 kHz; high-speed filtered DUTY MIN/MAX approximately 49.5%-50.1% at 50 kHz in the observed test.
- Verified selected MIN/MAX reset and HOLD/LIVE behaviors, lost-signal history retention, and a five-minute USB-connected navigation test.
- Observed LOW/PC1 999.82 Hz for a nominal 1 kHz internal generator output. The self-test does not constitute independent calibration.
- Compatible binary requires a matching Momentum Firmware API; see v1.4 release notes.

## [1.3] - 2026-10-08

### Pulse Analyzer
- Replaced short-pulse polling with rising/falling GPIO interrupt capture and high-resolution cycle timing.
- Added multi-sample averaging for high-frequency HIGH/LOW/PERIOD/DUTY measurements, improving stability around 50 kHz on the tested unit.
- Restricted interrupt-based pin selection to PC0, PC1, PB2 and PA4 to avoid reserved EXTI lines and crashes.
- Limited/redesigned display refresh to improve readability under interrupt load.

### Frequency Meter
- Reduced HIGH/PB3 hardware-counter refresh interval from approximately 500 ms to 100 ms.
- Corrected stray falling-edge EXTI triggering so LOW/PC1 no longer counts both edges after switching from Pulse Analyzer.

### Signal Generator
- Changed RUN frequency switching to update TIM1 PWM parameters in place, avoiding stop/restart freezes.

### UI / Stability
- Redesigned GPIO Monitor, Frequency Meter, Pulse Analyzer and Signal Generator measurement layouts.
- Updated v1.3 app-version metadata and on-device version labels.
- On-device 3.3 V PA7 loopback tests exercised measurement paths up to 50 kHz; the observed 50 kHz duty ranged about 49.8%–50.2% after filtering.
- Functional validation only; not independently calibrated or certified for arbitrary external signals.

## [1.2] - 2026-10-05

### UI / UX
- Added compact dashboard-style main menu.
- Added per-tool pixel icons.
- Added stronger selected-row highlighting.
- Added version indicator to the menu header.
- Added outlined/inverted state badges for LIVE/HOLD and RUN/STOP style states.
- Improved footer key/action hints.
- Improved Frequency Meter visual hierarchy.
- Improved Signal Generator visual hierarchy.
- Reworked About screen during on-device stability testing; current safe layout intentionally uses simple text/line primitives.

### Notes
- v1.2 work is focused on presentation and interaction polish.
- Measurement and generator backend behavior is intentionally kept separate from the UI redesign.

## [1.1] - 2026-10-05

### Frequency Meter
- Added dual measurement modes.
- **LOW mode:** PC1 period measurement using GPIO interrupt timing and `DWT->CYCCNT`.
- **HIGH mode:** PB3 / TIM2_CH2 hardware edge counter.
- Added left/right switching between LOW and HIGH frequency modes.
- Added mode-specific GPIO cleanup and measurement reset handling.
- Improved high-frequency measurement path by avoiding per-edge GPIO interrupt overhead.

### Signal Generator
- Expanded presets to:
  - 1 Hz
  - 2 Hz
  - 5 Hz
  - 10 Hz
  - 20 Hz
  - 50 Hz
  - 100 Hz
  - 200 Hz
  - 500 Hz
  - 1 kHz
  - 2 kHz
  - 5 kHz
  - 10 kHz
  - 20 kHz
  - 50 kHz
- Migrated signal generation to Flipper hardware PWM on **PA7 / TIM1**.
- Generator remains 50% duty cycle.
- Removed the need for a per-edge generator ISR.
- Generator can remain active while returning to the menu.

### Stability / Validation
- Created a stable backup milestone after successful build/install of the 50 kHz hardware-counter stage.
- Tested against Momentum Firmware API 87.1.
- Continued using Flipper Zero GPIO at 3.3 V logic levels only.

## [1.0] - 2026-10-01

### Added
- GPIO Monitor
- Frequency Meter
- Pulse Analyzer
- Signal Generator
- About screen
- App icon support

### Improved
- Frequency measurement stability with GPIO interrupts
- High-resolution timing with `DWT->CYCCNT`
- Timer-based signal generation using TIM2
- LIVE / HOLD behavior
- Application cleanup and resource handling

### Stability decision
- Frequency Meter runtime pin switching is intentionally disabled in v1.0 and the input is locked to PC1 after dynamic IRQ pin reconfiguration proved unstable on the tested Momentum build.

### Validated
- 1.00 Hz stable reading
- 2.00 Hz stable reading
- 5.00 Hz stable reading
- Pulse Analyzer verified with generator loopback
