# LabMate v1.6 Stable

**Stable release for Flipper Zero running Momentum Firmware.** This
release replaces v1.5 as the *latest downloadable Stable* but keeps the
v1.5 release and its assets available. It is based on the exact build
tested with LabMate's operator.

## What's new

- Grouped **MEASURE / OUTPUT / RECORDS / INFO** navigation and
  clearer tool screens.
- **Frequency Meter:** precise low-rate mode on PC1 and adaptive TIM2
  counter gate on HIGH PB3, correcting the low-Hz counting regression.
  Functional checks cover 1, 2, 10 Hz and 1, 5, 10, 20, 50 kHz presets.
- **Pulse Analyzer:** HIGH/LOW/PERIOD/DUTY, MIN/MAX STATS and HOLD/LIVE
  on supported GPIO input pins; device timing checks at 100 Hz and
  1 kHz on PC1.
- **Signal Generator:** existing PA7 PWM presets (1 Hz–50 kHz at
  50% duty), STOP/RUN control and safe PA7 BUSY interlock.
- **Profiles:** 3 saved slots, SAVE/LOAD/DELETE and confirmation,
  redundant CRC32-validated A/B microSD copies; LOAD refuses while
  the generator is RUN and never starts the output automatically.
- **Data Logger / Log History:** compatible CSV recording for low
  PC1, high PB3 and pulse PC1, and persistent read-only history.
  Existing settings and log storage paths are preserved.

## Validation

The precise released application build is from
[GitHub Actions 38007158577](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38007158577)
on commit `4a890002fea0acf8d524b7c772db3bbd3e239848`. It passed GPIO ownership, navigation, profile
codec, frequency estimator unit tests, Momentum SDK FAP compilation,
artifact SHA256 checks and mock Windows installation tests.

The operator confirmed the **v1.6 Stable candidate FAP** on a real
Flipper: version label, opening Frequency Meter/Pulse Analyzer,
preserved saved Profile S1, accessible existing CSV History, and
Generator default STOP all passed. More detailed instrument and
logger checks passed on preceding development builds with unchanged
signal processing/storage logic.

## Downloads and important limitations

- `labmate.fap` — Flipper Zero application for a compatible
  Momentum Firmware SDK/API.
- `SHA256SUMS.txt` — verifies the downloaded FAP.
- Install to `/ext/apps/Tools/labmate.fap` using a compatible
  Flipper app installer; retain backups of important SD data.

**Accuracy limits:** Measurements using Flipper's own generator are
functional self-tests, *not independent frequency calibration*.
HIGH PB3 was tested at discrete points, not certified at every
frequency. PC1 Pulse Analyzer timing tests at 100 Hz and 1 kHz
do not establish accuracy for every input pin or duty cycle.

**Storage limits:** Normal CSV/profile save and recovery behavior
passed functional tests, but deliberate corrupted/full/unavailable
microSD and unexpected power loss were not device fault-injected.
A/B profile redundancy cannot guarantee recovery from arbitrary
storage failure.

**Electrical safety:** Connect only known, 3.3 V-compatible digital
GPIO signals. Never connect 5 V, high-voltage or unknown signals
directly to Flipper GPIO.

**Previous Stable v1.5 remains available** from the repository's
Releases page, and this tag does not require changing the `main`
branch.
