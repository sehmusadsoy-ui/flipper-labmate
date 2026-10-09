# LabMate v1.5 Stable — Release Notes

Release date: 2026-10-09

LabMate is a GPIO and digital signal diagnostics app for Flipper Zero running
Momentum Firmware. Version 1.5 adds microSD CSV logging and a read-only Log
History browser while retaining GPIO Monitor, Frequency Meter, Pulse Analyzer
and Signal Generator from v1.4.

## New in v1.5

- **Data Logger** samples processed readings approximately once per second,
  recording FREQ/PC1 LOW, FREQ/PB3 HIGH, or PULSE/PC1.
- **Control**: LEFT/RIGHT chooses a source when stopped, OK starts/stops
  recording, and BACK stops, saves and returns to the main menu.
- **CSV**: `elapsed_ms,source,pin,valid,frequency_hz,high_us,low_us,period_us,duty_pct`.
  Elapsed time is relative to the session start, **not a wall-clock date**.
  `valid=0` denotes an unavailable measurement.
- **Storage**: logs are saved under `/ext/apps_data/labmate/` as
  `log_0001.csv` through `log_9999.csv`. New-file creation prevents
  intentional overwrites; numbering advances within a session.
- **Log History**: browse the latest 32 numbered CSV files read-only, see
  measurement type, row count and elapsed duration. Older files remain on
  microSD even if not shown in the list.
- **File handling**: SD operations run outside GPIO interrupt handlers and
  outside the GUI mutex. Records are synchronized every ten rows and again
  at STOP/BACK. Read/write error indicators are provided when failures are
  detected. UI responsiveness remains subject to SD latency.

## Validation performed

The user's Flipper Zero tests of the preceding v1.5 development build
reported successful logging and review in Log History, including repeated
START/STOP and BACK/save, plus regression checks of the four original tools.
Reviewed CSVs and user-reported checks included:

- FREQ/PC1: 600 valid rows over approximately 10 minutes at nominal 1 kHz.
- FREQ/PB3: nominal 1 kHz, 20 kHz and 50 kHz short test captures.
- PULSE/PC1: about 500 µs HIGH, 500 µs LOW, 1000 µs period and 50% duty.
- Live PC1 signal interruption and recovery recorded validity changes
  `1 → 0 → 1`.
- CSV imported into LibreOffice Calc on Windows.

The final version-label-only change from `v1.5d` to `v1.5` is included in
this Stable source and CI-built release. A successful CI build proves
compilation and artifact generation; it does **not** by itself independently
verify that the final CI-produced FAP was reinstalled on hardware.

All loopback measurements used the internal PA7 signal generator with
3.3 V-compatible GPIO inputs. This is functional testing, **not independent
measurement calibration**.

## Known limitations and safety

- **Real microSD failure scenarios were not tested on hardware.** Recovery
  from an unmounted, corrupted or full card, actual read/write errors,
  unexpected power loss, and indefinitely blocking SD calls is not certified.
  Synchronizing every ten rows mitigates potential data loss but cannot
  guarantee recovery. **Do not remove microSD while LabMate is running**:
  the app itself is stored on the card.
- Concurrent host-side USB writes to a CSV that is actively being logged
  were not tested. Microsoft Excel import was not independently tested.
- Log History is read-only and displays at most the latest 32 numbered files.
- **3.3 V GPIO logic only.** Never connect 5 V, 12 V, mains voltage,
  automotive wiring or unknown-voltage signals directly.
- The release FAP targets the Momentum SDK/API used by GitHub Actions.
  Builds for other firmware APIs may require recompilation.

## Installation and verification

Download `labmate-v1.5.fap` and `SHA256SUMS.txt` from this GitHub Release.
Verify the checksum if desired, then copy the FAP to
`/ext/apps/Tools/labmate.fap` on a compatible Flipper Zero.
Open **Apps → Tools → LabMate**.

GitHub Actions builds the release from the exact commit tagged `v1.5`,
uploads the compiled FAP and its SHA-256 checksum, and records the
Momentum SDK API version alongside the release artifact.

The earlier [v1.4 Stable release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.4)
is preserved as a fallback.
