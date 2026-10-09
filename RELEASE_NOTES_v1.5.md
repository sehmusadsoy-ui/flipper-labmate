# LabMate v1.5 — Data Logger and Log History

LabMate is an external app for Flipper Zero with Momentum Firmware.
v1.5 adds microSD-based measurement recording and a read-only session
browser while retaining the four existing digital instruments.

## New in v1.5

- **Data Logger:** Record one measurement snapshot per second to CSV for
  FREQ/PC1 LOW, FREQ/PB3 HIGH or PULSE/PC1.
- **START / STOP / BACK:** OK starts and stops recording. BACK while
  recording finalizes the CSV and returns to the menu.
- **Non-overwriting files:** CSV recordings are stored under
  `/ext/apps_data/labmate/log_NNNN.csv`. Filenames increment using the
  highest existing numeric ID and never deliberately replace a file.
  Valid IDs range from 0001 through 9999.
- **Log History:** Browse the newest 32 matching recording filenames
  and inspect each recording's source, complete row count and elapsed
  duration. Older recordings remain on the card, but are not listed.
- **Safer storage cleanup:** Write/sync errors are signaled when detected;
  file handles are cleaned up after failed opens as well as normal STOP
  and BACK. Storage writes occur outside capture interrupts and outside
  the GUI drawing mutex.
- **Existing instruments preserved:** GPIO Monitor, Frequency Meter,
  Pulse Analyzer and Signal Generator.

## CSV format

```csv
elapsed_ms,source,pin,valid,frequency_hz,high_us,low_us,period_us,duty_pct
```

`elapsed_ms` counts milliseconds since recording began, **not** a
wall-clock timestamp. `valid=0` means no valid reading at that sample.
Columns not relevant to the selected source are left empty. Data are
sampled approximately every second; the app does not log every GPIO
edge. Files are synchronized every ten rows and at normal close.

## Verification

The development build was tested on a physical Flipper by the project
owner. Device tests confirmed normal operation of all four original
instruments; repeated START/STOP; CSV recording and Log History; and
signal-loss/recovery markers. In one PC1 run, 600/600 CSV records were
valid over about ten minutes. PB3 runs were checked at nominal 1, 20
and 50 kHz. A PULSE/PC1 run at nominal 1 kHz / 50% duty reported about
500 us HIGH, 500 us LOW and 1000 us period.

Final development-build acceptance also passed: matching development
labels in menu/About; USB-connected STOP/save; BACK-to-save; and opening
both resulting CSV files in Log History. The release-candidate source
changes the shared on-screen version text to `v1.5` only.

A sample CSV was successfully imported with nine columns into
LibreOffice Calc on Windows. **Microsoft Excel itself was not
independently tested.**

These tests used the Flipper's internal PA7 signal generator connected
to compatible 3.3 V GPIO input pins. They demonstrate functionality,
**not independent frequency calibration**.

## Known limitations and safety

- Use **3.3 V digital GPIO only**. Never attach 5 V, mains, automotive
  wiring or signals of unknown voltage directly to Flipper GPIO.
- This app needs a microSD card. **Do not remove the card while the app
  is running.** Real microSD failure, full/corrupt card and indefinite
  storage latency recovery were not verified on physical hardware.
- USB-connected logging was exercised, but simultaneous computer-side
  file transfers to an active CSV were **not** tested or recommended.
- Slow SD operations can still temporarily delay button response;
  asynchronous storage I/O is not implemented.
- Log History is read-only and shows only the newest 32 matching files.
- A binary built against one Momentum SDK/API version may not launch
  against another; rebuild with the matching Momentum environment if
  necessary.

## Installation

Use the `labmate-v1.5.fap` asset associated with the **v1.5 GitHub
Release** once published. Verify it using the accompanying
`SHA256SUMS.txt`. Place it at
`/ext/apps/Tools/labmate.fap` and retain only one copy of the app.
If the v1.5 Release is not yet listed, this document is release
preparation and **not proof of an official Stable publication**.

Source: https://github.com/sehmusadsoy-ui/flipper-labmate
