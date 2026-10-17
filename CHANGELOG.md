# Changelog

## [v1.8 E11 — Custom Momentum Edition] — 2026-10-17 (public compatibility pre-release)

- [Public E11 GitHub release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum) is a separately tagged **pre-release** of the integrated `v1.8` app. It does **not** replace or alter original v1.8 Stable.
- Source commit `99cb65d0194dc59d423cfa439c90618ac6b9f114`; tested candidate FAP SHA256 `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`.
- Implements I2C Explorer and optional 3.3V 1-Wire features alongside existing v1.8 tools, but requires **matching E11-patched Momentum firmware and native plugins/resources**. Not universally compatible with ordinary Momentum, official Flipper firmware or unrelated custom firmware.
- On a matched device, operator-reported UI, ESP32-S2 UART at 115200, PA7→PC1 100 Hz and 1 kHz 50% PWM/Frequency/Pulse loopback, STOP/RESTART and isolated fresh Logger CSV/Profile persistence PASS.
- Actual I2C ACK, DS18B20 conversion, independent calibration/OFF voltage, broad native third-party conflicts, fault-injection microSD recovery and exact previous custom-firmware rollback remain unverified/deferred.
- Matched firmware package is marked expert-review only. Full updater may alter firmware, bundled SD resources/apps/settings. E11 source remains under [Draft PR #13](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/13) and **has not been merged into `main`**.

## [1.8] — 2026-10-14 (ordinary Stable published)

- [Original v1.8 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8): one integrated FAP with modular coordinator, UART Terminal and Counter STOP/RESUME, preserving earlier Logger, Profiles, PWM, Button Analyzer and diagnostic tools.
- Published FAP SHA256 `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`; exact source tag `02b05639364d6dd71f5eb70456eca379c59218cb`. Release tests include operator-reported 19/19 scope acceptance.
- I2C Explorer and optional 1-Wire were **not shipped in this ordinary Stable** due to native firmware ownership/cancellation concerns; separate E11 custom firmware channel above provides their source and limited hardware-tested build.
- External calibrated measurements and deliberate storage failure tests were deferred; no general original/third-party firmware compatibility guarantee.


## [1.7] - 2026-10-12 (Stable published)

**[v1.7 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7)**
is publicly released (not a prerelease). The original `v1.7` tag
still points to `d0e1bc6a95b257841533f0aa8745e3a79bbc8dcd`. On 2026-10-12 the published FAP
and checksum were replaced **in place**, keeping the same version, to
correct the OUTPUT/ABOUT visible label to **PWM Studio**.
The updated FAP comes from tested source `0aeb0ca7ceba092c8adb6e44add0a2212cae1a74`,
GitHub CI 38290044094 (2/2 PASS) and user-reported on-device
label/regression test 4/4 PASS. **Current FAP SHA256: `A0B305E5FD8D71C85C51480EE06A8B7E5EBD5BEE0E82935B0ED3B7E74E7EBCEA`.**
Original FAP SHA256 `5A7CB0EAE601EEAC8856790211C4D2831A9198C31853631E1DAF0308CE724335` is superseded.
v1.6.1 Stable and v1.7 RC1 tags/assets were preserved.

The refactored Stable Candidate FAP completed operator-reported
on-device regression Test 7A–7F **36/36 PASS** (7B timing screenshots
reviewed): PWM/Pulse, LOW/HIGH Frequency, Event Counter, clean-digital
Button, Thresholds, three Logger modes, History cancel/delete,
Profiles guards, menu/About and app exit/persistence.

The exact final-label FAP passed separate Test 7G **4/4 PASS**;
the last release CI reproduced the same SHA256 and published verified
assets. Real-Windows `-Channel RC1 -VerifyOnly` passed, and the
published Stable-channel `-VerifyOnly` plus actual COM7 USB installation
passed on 2026-10-12 with matching SHA256 and single-FAP destination.
Separate post-reinstall Flipper menu/About, PWM STOP, retained S1 and
old History CSV open checks all passed (operator-reported **4/4 PASS**,
2026-10-12).

**In-place maintenance (same v1.7 tag and release, corrected FAP):**
updated current-Stable pointers, PWM Studio menu/About labels,
release assets/checksum and installer documentation. Microsoft Excel
import remains **NOT TESTED**; LibreOffice Calc import succeeded.

### New tools and signal generation
- PWM Studio adds adjustable TIM1/PA7 PWM duty (5..95%, step 5%) and
  STOP-only CUSTOM frequency (1..50,000 Hz), preserving the original
  15 presets and safe output shutdown on application exit.
- Event Counter counts actual PB3/TIM2 rising edges as a saturating
  64-bit total with RUN/STOP/RESET and elapsed time.
- Button Analyzer measures PC1 pull-up dry-contact transitions, with
  configurable debounce and bounce/settle/hold telemetry.
- Threshold Alerts provides four visual latch/acknowledge thresholds
  for frequency, pulse duty, rising-edge count and button settle.

### Interface and Records
- Added differentiated monochrome icons for 11 tools and a paginated
  13-page About field guide; redesigned Button/Counter/Thresholds/PWM
  and Data Logger, History/detail and Profiles screens for 128x64.
- Log History can remove **one explicitly selected CSV** only after a
  second, file-named confirmation; BACK cancels. Existing log filenames,
  CSV formats and profile storage remain compatible.
- Profiles retain their legacy codec: PWM CUSTOM and duty/threshold
  settings are **not** persisted.

### Fixes and verification boundaries
- Fixed Frequency Meter's saved LOW PC1 entry initially starting the
  wrong PB3 capture engine.
- Fixed Pulse Analyzer's asymmetric duty accumulation bug at 95% and
  5% duty, confirmed against clean PA7->PC1 digital loopback.
- Published pre-release `v1.7-rc1` source `d55eec03` and
  checksum-verified artifact were released independently of prior Stable.
- Stable candidate `bdb1de10` FAP SHA256
  `94883B517D526EAA0F64E2AEAC89F89D181F85FD4F3ABB9056F3EEC2B68123E0`
  passed CI 2/2 plus 36/36 targeted user-reported device checks.
  The final on-screen `v1.7` FAP received a separate 4/4 on-device smoke check.
- Refactoring extracted measurement updates, CSV sample preparation and
  Threshold sample-validity gating from `labmate.c` into separate
  modules without changing the intended acquisition logic.
- One-command version-aware PowerShell+USB installer with release-tag,
  SHA256 and fixed-FAP-path guards passed Windows mock tests.
- **NOT TESTED:** physical mechanical switch bounce and independent
  oscilloscope/voltage/frequency calibration (equipment deferred).
  Full/corrupted SD and other destructive error-path checks, plus
  Microsoft Excel CSV import, remain unverified. See
  `docs/DEFERRED_HARDWARE_TESTS.md` and `docs/releases/RELEASE_NOTES_v1.7.md`.

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
  remain unverified. See [v1.6 release notes](docs/releases/RELEASE_NOTES_v1.6.md).


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
- Real microSD fault recovery, simultaneous host writes to a live CSV, Microsoft Excel import and external-reference calibration remain unverified; see [v1.5 Stable release notes](docs/releases/RELEASE_NOTES_v1.5.md).

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
