# LabMate

**A portable digital signal toolkit for Flipper Zero — built for Momentum Firmware.**

[![Latest release](https://img.shields.io/github/v/release/sehmusadsoy-ui/flipper-labmate?label=stable%20release)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Flipper%20Zero-orange)
![Firmware](https://img.shields.io/badge/firmware-Momentum-blueviolet)

LabMate combines **GPIO Monitor, Frequency Meter, Pulse Analyzer, Signal Generator, Data Logger and Log History** in one Flipper Zero external app.

**[Download LabMate v1.5 Stable (.fap)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.5/labmate-v1.5.fap)** · [v1.5 release notes](RELEASE_NOTES_v1.5.md) · [SHA-256 verification file](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.5/SHA256SUMS.txt) · [v1.4 fallback](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.4) · [All releases](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) · [Changelog](CHANGELOG.md)

> [!IMPORTANT]
> **3.3 V GPIO ONLY.** Never directly connect 5 V, 12 V, automotive wiring, mains voltage, or unknown-voltage signals to Flipper Zero GPIO. External signals require appropriate conditioning and protection.

## Features at a glance

| Instrument | What it does | Input / output |
| --- | --- | --- |
| **GPIO Monitor** | Shows digital HIGH/LOW state, edge activity, and LIVE/HOLD status | Selectable digital GPIO |
| **Frequency Meter** | Measures input frequency with dedicated low- and higher-frequency paths | LOW: **PC1** · HIGH: **PB3** |
| **Pulse Analyzer** | Displays HIGH time, LOW time, period and duty cycle | **PC0, PC1, PB2, PA4** |
| **Signal Generator** | Generates a 50% duty-cycle square wave using hardware PWM | Output: **PA7** |
| **Data Logger** | Saves one processed measurement sample each second to microSD CSV | **PC1** low frequency or pulse · **PB3** high frequency |
| **Log History** | Browses up to 32 newest log files read-only | microSD CSV logs |

### What's new in v1.5

- **Data Logger:** captures FREQ/PC1, FREQ/PB3 or PULSE/PC1 measurements to timestamped-by-elapsed-time CSV once per second.
- **START/STOP and BACK-to-save:** non-overwriting numbered logs in `/ext/apps_data/labmate/`; file synchronization every ten samples and at normal close.
- **Log History:** read-only browsing of the latest 32 numbered sessions, with source, row count and duration.
- **Retained v1.4 tools:** Frequency Meter and Pulse Analyzer MIN/MAX and filtering, GPIO Monitor and hardware PWM Signal Generator remain available.
- **Safety disclosure:** handling real corrupted, full, unmounted or failing microSD media has **not** been validated on-device. Do not remove microSD while LabMate is running; consult the [v1.5 release notes](RELEASE_NOTES_v1.5.md).

Previous v1.4 loopback checks showed nominal HIGH/LOW/PERIOD near 10/10/20 µs at 50 kHz and about 999.82 Hz for an internal nominal 1 kHz generator setting. These are functional self-tests, **not independently calibrated measurements**.

## Get started

1. Download the published **[LabMate v1.5 Stable FAP](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.5/labmate-v1.5.fap)** (and optionally [verify its SHA-256](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.5/SHA256SUMS.txt)).
2. Copy the file to `/ext/apps/Tools/labmate.fap` on a compatible Flipper Zero running Momentum Firmware.
3. On your Flipper Zero, open **Apps → Tools → LabMate**.
4. Select an instrument from the main menu. For a safe initial test, use a **single GPIO jumper from PA7 to PC1** and the built-in Signal Generator; do not attach external voltage.

**Tested environment:** Flipper Zero · Momentum Firmware · local external FAP build · **API 87.1**. The v1.5 Stable release binary is compiled by GitHub Actions using Momentum dev SDK; its specific API is recorded in the published release notes. If your firmware uses another API, rebuild from source. Compare the downloaded FAP with the release's own `SHA256SUMS.txt`.

## Instrument details

### Frequency Meter

**LOW / PC1:** GPIO rising-edge interrupt plus `DWT->CYCCNT` high-resolution period measurement.

**HIGH / PB3:** `TIM2_CH2` hardware edge counter, avoiding CPU interrupts for every edge.

Controls: **LEFT** = LOW/PC1 · **RIGHT** = HIGH/PB3 · **OK** = HOLD/LIVE · **UP** = reset recorded MIN/MAX. MIN/MAX survive HOLD and lost input; changing modes or reopening the meter begins a new history.

### Pulse Analyzer

Measures HIGH time, LOW time, period and duty cycle using rising/falling GPIO interrupts. Supported capture inputs are **PC0, PC1, PB2 and PA4**; other GPIOs are not offered in this mode due to interrupt-line and peripheral constraints. High-frequency values are averaged for display stability.

Controls: **LEFT/RIGHT** = select supported capture pin · **OK** = HOLD/LIVE · **UP** = show/hide statistics · **DOWN** = reset statistics in LIVE mode · **BACK** = return to menu. A five-sample median reduces one-off timing spikes in high-frequency MIN/MAX (not in live readings).

### Signal Generator

- **Output:** PA7, hardware PWM (`TIM1`)
- **Duty:** fixed at 50%
- **Presets:** 1, 2, 5, 10, 20, 50, 100, 200, 500 Hz; 1, 2, 5, 10, 20, 50 kHz
- **Controls:** LEFT/RIGHT = select preset · OK = RUN/STOP · BACK = return to menu (generation may remain active)

### GPIO Monitor

Observe digital HIGH/LOW state and edge activity on selectable GPIO pins. This view uses polling and is intended for logic-state inspection, **not accurate high-frequency edge counting**. Use Frequency Meter for high-frequency signals.

### Data Logger and Log History

Data Logger: **LEFT/RIGHT** selects FREQ/PC1 LOW, FREQ/PB3 HIGH or PULSE/PC1 while stopped; **OK** starts/stops; **BACK** saves and returns. CSV values use `elapsed_ms` since START, not wall-clock time. Logs are written to `/ext/apps_data/labmate/` without intentionally overwriting existing files.

Log History: **UP/DOWN** selects from the newest 32 files; **OK** opens read-only session details; **BACK** returns. A real microSD failure/full-card case was not hardware-tested.

## Hardware and validation

| Check | Historical v1.4 on-device observation |
| --- | --- |
| App build / launch | Passed using local Momentum Firmware; prior API 87.1 development environment |
| Frequency Meter LOW/PC1 MIN/MAX | Tested at 1 kHz; displayed 999.82 Hz nominal 1 kHz loopback in one observation |
| Frequency Meter HIGH/PB3 MIN/MAX | Tested at 1 kHz, 20 kHz and 50 kHz with loopback |
| Frequency MIN/MAX history | UP reset, HOLD/LIVE, mode changes, signal removal checked |
| Pulse Analyzer MIN/MAX | Nominal timings at 1 kHz, 20 kHz and 50 kHz loopback |
| 50 kHz filtered duty MIN/MAX | Approximately 49.5%–50.1% on the tested unit |
| USB navigation | Five minutes without reported freezes |
| Generator and GPIO Monitor | Continued from v1.3; no new independent full-range validation |

These checks do **not** establish calibrated accuracy across the full frequency range or compatibility with all firmware builds. Long-duration stress testing and external reference-instrument calibration are not yet complete.

### Screenshots

The repository retains **[v1.2 screenshots](screenshots/v1.2/)** as an archived UI reference. The v1.4 UI is different; the old screenshots are **not** presented as current.

## Build from source

Place these files together in your Momentum Firmware checkout:

```text
applications_user/labmate/
├── application.fam
├── labmate.c
└── labmate_10px.png
```

From the Momentum Firmware root:

```powershell
.\fbt APPSRC=applications_user\labmate
```

To build, install and launch on a connected Flipper Zero:

```powershell
.\fbt launch APPSRC=applications_user\labmate
```

The generated FAP is located under `build/f7-firmware-C/.extapps/labmate.fap` in the tested configuration.

For a basic hookup reference, see [docs/wiring_example.md](docs/wiring_example.md). Always confirm pin assignments and 3.3 V signal levels before connecting hardware.

## Project files

- [Source: labmate.c](labmate.c) · [App manifest](application.fam)
- [v1.5 Stable Release Notes](RELEASE_NOTES_v1.5.md) · [v1.4 Release Notes](RELEASE_NOTES_v1.4.md) · [Changelog](CHANGELOG.md)
- [GitHub Releases and current binary downloads](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) · [Older FAP archive](dist/) · [Archived v1.2 screenshots](screenshots/v1.2/)
- [MIT License](LICENSE)

## Author and license

Created by **sehma** as a portable digital-signal diagnostic utility for Flipper Zero.

Licensed under the **MIT License**. See [LICENSE](LICENSE).
