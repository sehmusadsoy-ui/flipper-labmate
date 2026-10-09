# LabMate v1.5 — Draft Release Notes (NOT PUBLISHED)

**Status: release preparation only.** As of 2026-10-09, v1.4 remains the
published Stable release. Do not distribute this document as proof that
v1.5 is officially released. Final version text and checksums must be
generated from the final, tested v1.5 commit and binary.

## New in v1.5

- **Data Logger** — records one sampled measurement per second to CSV
  on microSD, with three measurement sources: FREQ/PC1 LOW,
  FREQ/PB3 HIGH and PULSE/PC1.
- **START/STOP and BACK/save** — write header and measurement rows;
  flush/synchronize every ten rows and at normal file close. The app
  does not write one row per GPIO edge or inside an interrupt handler.
- **Collision-safe file naming** — `/ext/apps_data/labmate/log_0001.csv`
  through `log_9999.csv`. Files use create-new semantics and are not
  intentionally overwritten. Names increase within an app session.
- **Log History** — read-only list of up to 32 newest numeric log IDs;
  inspect the source, complete row count and elapsed duration. The
  underlying older CSV files remain on the microSD card.
- **Error handling** — displays SD/write or SD/read error indicators
  where errors are detected; release of storage resources after failed
  file opening is included in the latest development source.

## CSV format

`elapsed_ms,source,pin,valid,frequency_hz,high_us,low_us,period_us,duty_pct`

- `elapsed_ms`: time since logging started, not a real-world timestamp.
- `valid=0`: no current valid measurement. Invalid pulse measurements
  have zero durations; invalid frequency measurements are reported as zero.
- The frequency and pulse columns not relevant to a selected source
  are left empty.

## Testing to date (user-reported device results and analyzed CSVs)

- Regression checks for the original four v1.4 tools passed:
  GPIO Monitor, Frequency Meter, Pulse Analyzer and Signal Generator.
- PC1 frequency logging: 600 valid samples over about ten minutes,
  around 1 kHz from the built-in generator.
- PB3 logging: short runs at nominal 1 kHz, 20 kHz and 50 kHz.
- Pulse logging: nominal 1 kHz / 50% duty captured about
  500 µs HIGH, 500 µs LOW and 1000 µs period.
- Repeated START/STOP without freezing and newer CSV files
  visible in Log History.
- Signal interruption and restoration: recorded transition from valid
  samples, to invalid samples, back to valid samples.
- LibreOffice Calc on Windows successfully imported an examined CSV
  with nine separated columns and expected validity sequence.
  **Microsoft Excel was not independently tested.**
- Momentum development build passed GitHub Actions. Compilation is not
  the same as a hardware test of the final build.

All frequency checks used the Flipper's internal PA7 generator linked
to a 3.3 V-compatible input. **These checks are not independent
frequency calibration or verification against an external standard.**

## Known limits and precautions

- Only **3.3 V digital GPIO**. Do not connect higher or unknown voltages.
- microSD access can delay the main app event loop. Error indicators
  are implemented but recovery from real SD read/write failures,
  a full/corrupt card, and indefinite SD latency is not certified.
- **Do not remove the microSD while LabMate is running.**
  The application FAP itself is stored on the card.
- Running external USB file transfers against an actively written
  CSV has not been validated and is not a recommended acceptance test.
- Log History shows only the newest 32 numeric log files and is
  intentionally read-only.
- Firmware compatibility depends on the installed Momentum SDK/API.
  A FAP built for another API may need to be rebuilt.

## Release gate — remaining on-device acceptance

- [x] Install and launch the latest development source on device, including
      the SD cleanup and matching development-version text (user report).
- [x] FREQ/PC1 capture with STOP/save; successfully reopen in Log History
      (user report).
- [x] Second FREQ/PC1 capture with BACK-to-save; successfully reopen
      the separate CSV in Log History (user report).
- [x] Record and STOP with USB attached; saved CSV available in
      Log History (user report; no simultaneous host writes tested).
- [x] Original four instrument regressions and Logger final-device
      STOP/BACK/History controls passed (user-reported).
- [ ] Ensure the release candidate installs as a single app entry;
      do not treat this as proof of SD error recovery.
- [ ] Build the stable-labeled release candidate from its exact final source,
      record CI SDK/API version, and produce the FAP plus SHA-256.
- [ ] Confirm release-candidate installation and get explicit go-ahead
      before creating a v1.5 tag or publishing a GitHub Release.

If a test fails, continue on `v1.5-dev`; do not tag or publish Stable.

**Current published release:** [LabMate v1.4 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.4).
