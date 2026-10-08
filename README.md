# LabMate

**A portable digital signal toolkit for Flipper Zero — built for Momentum Firmware.**

[![Latest release](https://img.shields.io/github/v/release/sehmusadsoy-ui/flipper-labmate?label=stable%20release)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Flipper%20Zero-orange)
![Firmware](https://img.shields.io/badge/firmware-Momentum-blueviolet)

LabMate combines four practical GPIO and digital signal instruments into one Flipper Zero external app: **GPIO Monitor, Frequency Meter, Pulse Analyzer, and Signal Generator**.

**[Download LabMate v1.3 Stable (.fap)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.3/labmate-v1.3.fap)** · [Release notes](RELEASE_NOTES_v1.3.md) · [All releases](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) · [Changelog](CHANGELOG.md)

> [!IMPORTANT]
> **3.3 V GPIO ONLY.** Never directly connect 5 V, 12 V, automotive wiring, mains voltage, or unknown-voltage signals to Flipper Zero GPIO. External signals require appropriate conditioning and protection.

## Features at a glance

| Instrument | What it does | Input / output |
| --- | --- | --- |
| **GPIO Monitor** | Shows digital HIGH/LOW state, edge activity, and LIVE/HOLD status | Selectable digital GPIO |
| **Frequency Meter** | Measures input frequency with dedicated low- and higher-frequency paths | LOW: **PC1** · HIGH: **PB3** |
| **Pulse Analyzer** | Displays HIGH time, LOW time, period and duty cycle | **PC0, PC1, PB2, PA4** |
| **Signal Generator** | Generates a 50% duty-cycle square wave using hardware PWM | Output: **PA7** |

### What's new in v1.3

- **Pulse Analyzer:** interrupt-based rising/falling edge capture and improved smoothing of short-pulse HIGH/LOW/DUTY readings.
- **Frequency Meter:** HIGH/PB3 hardware counter refresh improved to approximately 100 ms; corrected interrupt-edge cleanup when switching tools.
- **Signal Generator:** change the selected frequency while RUN without stopping/restarting the PWM peripheral.
- **Interface:** revised instrument screens, clearer measurement presentation and reduced redraw pressure at higher frequencies.
- **Stability:** safer Pulse Analyzer input selection and fixes for crashes or freezes observed during testing.

**Tested loopback result:** with LabMate's PA7 PWM output connected to PC1 as a **3.3 V logic loopback**, the 50 kHz Pulse Analyzer displayed nominally **HIGH 10 µs · LOW 10 µs · PERIOD 20 µs**, and the displayed DUTY varied approximately **49.8%–50.2%** on the tested unit. This is a functional self-test, **not independent calibration**.

## Get started

1. Download **[labmate-v1.3.fap](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.3/labmate-v1.3.fap)** from the stable release.
2. Copy the file to `/ext/apps/Tools/labmate.fap` on a compatible Flipper Zero running Momentum Firmware.
3. On your Flipper Zero, open **Apps → Tools → LabMate**.
4. Select an instrument from the main menu. For a safe initial test, use a **single GPIO jumper from PA7 to PC1** and the built-in Signal Generator; do not attach external voltage.

**Tested environment:** Flipper Zero · Momentum Firmware · external FAP · **API 87.1**. A binary built for one firmware/API version may not run on another; rebuild from source if needed. Compare the downloaded binary's SHA-256 against [dist/SHA256SUMS.txt](dist/SHA256SUMS.txt).

## Instrument details

### Frequency Meter

**LOW / PC1:** GPIO rising-edge interrupt plus `DWT->CYCCNT` high-resolution period measurement.

**HIGH / PB3:** `TIM2_CH2` hardware edge counter, avoiding CPU interrupts for every edge.

Controls: **LEFT** = LOW/PC1 · **RIGHT** = HIGH/PB3 · **OK** = HOLD/LIVE.

### Pulse Analyzer

Measures HIGH time, LOW time, period and duty cycle using rising/falling GPIO interrupts. Supported capture inputs are **PC0, PC1, PB2 and PA4**; other GPIOs are not offered in this mode due to interrupt-line and peripheral constraints. High-frequency values are averaged for display stability.

Controls: **LEFT/RIGHT** = select supported capture pin · **OK** = HOLD/LIVE · **BACK** = return to menu.

### Signal Generator

- **Output:** PA7, hardware PWM (`TIM1`)
- **Duty:** fixed at 50%
- **Presets:** 1, 2, 5, 10, 20, 50, 100, 200, 500 Hz; 1, 2, 5, 10, 20, 50 kHz
- **Controls:** LEFT/RIGHT = select preset · OK = RUN/STOP · BACK = return to menu (generation may remain active)

### GPIO Monitor

Observe digital HIGH/LOW state and edge activity on selectable GPIO pins. This view uses polling and is intended for logic-state inspection, **not accurate high-frequency edge counting**. Use Frequency Meter for high-frequency signals.

## Hardware and validation

| Check | v1.3 on-device observation |
| --- | --- |
| App build / launch | Passed using Momentum Firmware API 87.1 |
| GPIO Monitor and navigation | Exercised on-device |
| Frequency Meter LOW/PC1 | Exercised with generator loopback |
| Frequency Meter HIGH/PB3 | Exercised up to 50 kHz loopback |
| Pulse Analyzer | Expected nominal timings at 1 Hz, 20 kHz and 50 kHz loopback |
| 50 kHz Pulse Analyzer duty | Approximately 49.8%–50.2% on the tested unit |
| Generator RUN frequency changes | Re-tested after freeze fix |

These checks do **not** establish calibrated accuracy across the full frequency range or compatibility with all firmware builds. Long-duration stress testing and external reference-instrument calibration are not yet complete.

### Screenshots

The repository currently retains **[v1.2 screenshots](screenshots/v1.2/)** as an archived UI reference. **Updated v1.3 screenshots have not yet been added**; the older screenshots are not presented as the current interface.

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
- [v1.3 Release Notes](RELEASE_NOTES_v1.3.md) · [Changelog](CHANGELOG.md)
- [Prebuilt FAP and SHA-256](dist/) · [Archived v1.2 screenshots](screenshots/v1.2/)
- [MIT License](LICENSE)

## Author and license

Created by **sehma** as a portable digital-signal diagnostic utility for Flipper Zero.

Licensed under the **MIT License**. See [LICENSE](LICENSE).
