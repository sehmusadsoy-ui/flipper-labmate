# LabMate v1.4 Stable — Release Notes

Date: 2026-10-08

LabMate is a GPIO and digital-signal diagnostics application for Flipper Zero running Momentum Firmware.

## What's new since v1.3

### Frequency Meter — measured MIN/MAX

- Records the minimum and maximum **valid measured frequency** within the current measurement session.
- LOW/PC1 (GPIO interrupt period timing) and HIGH/PB3 (TIM2 hardware edge counting) are both supported.
- UP resets frequency history; OK toggles LIVE/HOLD while preserving history. Changing the input mode or reopening the meter starts a new history.
- Losing an input signal invalidates the *current* frequency without destroying already recorded extrema.
- Corrected mixed rounding/truncation between the live reading and MIN/MAX display, and improved value spacing.
- Throttled normal-screen refresh to reduce USB-connected menu stalls.

### Pulse Analyzer — measured MIN/MAX

- New statistics page (UP to show/return) for HIGH time, LOW time, PERIOD and DUTY.
- DOWN resets Pulse statistics in LIVE mode; OK switches HOLD/LIVE without deleting recorded extrema.
- Four cleanly aligned statistics rows, readable headers and shorter action hints on the 128 x 64 display.
- From approximately 8 kHz upwards, statistics use a median of five spaced measurement snapshots to reduce the influence of isolated timestamp spikes. The LIVE signal capture, ISR, period and duty calculations remain unchanged; the displayed statistics represent **filtered extrema**, not raw single-sample extrema.
- Supported Pulse Analyzer input GPIOs remain PC0, PC1, PB2 and PA4.

## Functional verification

The developer compiled and launched v1.4 on a Flipper Zero with Momentum Firmware. A single **3.3 V GPIO loopback** from PA7 (Signal Generator) to PC1 or PB3 (selected measurement input) was used.

- Frequency Meter LOW/PC1 and HIGH/PB3 tested at 1 kHz; 20 kHz and 50 kHz tested on HIGH/PB3.
- Frequency MIN/MAX reset, HOLD/LIVE history, mode selection, and history retention after the signal is removed were observed on-device.
- A LOW/PC1 measurement of **999.82 Hz** was observed for a 1 kHz internal generator setting (difference 0.18 Hz, 0.018% relative to the selected nominal value).
- Pulse Analyzer normal and MIN/MAX pages observed at 1 kHz, 20 kHz and 50 kHz. At 50 kHz, nominal HIGH/LOW/PERIOD readings were about 10/10/20 microseconds.
- In the reported 50 kHz loopback test, Pulse Analyzer DUTY MIN/MAX narrowed from approximately **47.2%-52.7%** before the statistics filter to **49.5%-50.1%** after filtering. These are measurements on one unit, not a universal guarantee.
- Five minutes of navigation and meter interaction over USB completed without a reported freeze.

These are **functional self-tests**, not independent calibration. The internal signal generator and meter share the same hardware timebase, so agreement does not establish traceable frequency accuracy. External signals, all firmware builds, and long-duration stability are not independently certified.

## Compatibility and installation

Download the published [`labmate-v1.4.fap`](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.4/labmate-v1.4.fap) from [LabMate v1.4 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.4). Copy it to `/ext/apps/Tools/labmate.fap`, then open **Apps > Tools > LabMate**.

The on-device development builds and the GitHub Actions binary both used Momentum Firmware **API 87.1**, verified in the successful release workflow logs. A future firmware/API update may require rebuilding from source. Rebuild with your installed Momentum Firmware checkout if needed:

```powershell
Copy-Item .\labmate.c "$env:USERPROFILE\Momentum-Firmware\applications_user\labmate\labmate.c" -Force
Copy-Item .\application.fam "$env:USERPROFILE\Momentum-Firmware\applications_user\labmate\application.fam" -Force
Copy-Item .\labmate_10px.png "$env:USERPROFILE\Momentum-Firmware\applications_user\labmate\labmate_10px.png" -Force
cd "$env:USERPROFILE\Momentum-Firmware"
.\fbt launch APPSRC=applications_user\labmate
```

## Safety

**3.3 V logic GPIO only.** Never directly connect 5 V, 12 V, automotive wiring, mains or signals of unknown voltage to Flipper GPIO. Use appropriately engineered input protection and signal conditioning for other systems.

The release includes `SHA256SUMS.txt`; GitHub also reports the published v1.4 FAP SHA-256 as `b5be0a27709ea2c4fe8d63269404d50a4e7d8863c1e8e773063764f9f607cf25`. The v1.3 Stable tag and release remain available as a fallback.

### Release artifact provenance

The official v1.4 FAP (18,692 bytes) was built successfully from the `v1.4` source on GitHub Actions with Momentum Firmware dev SDK (API **87.1**), not copied from an older build. Source-to-device loopback tests were done with the developer's local Momentum API 87.1 checkout. CI build success verifies compilation, but the CI-produced downloadable binary itself was not separately installed on the device during this session.
