# Flipper LabMate

**LabMate v1.0** is a compact digital-signal diagnostic toolkit for Flipper Zero running Momentum Firmware.

It combines four practical tools in one external app:

- **GPIO Monitor** — view HIGH/LOW state and edge activity
- **Frequency Meter** — interrupt-based frequency measurement on PC1
- **Pulse Analyzer** — HIGH time, LOW time, period and duty cycle
- **Signal Generator** — hardware-timed 1 Hz / 2 Hz / 5 Hz square-wave output on PA7

> **3.3 V GPIO ONLY.** Do not connect 5 V, 12 V, automotive wiring, or unknown-voltage signals directly to Flipper Zero GPIO.

## Screenshots

| Main menu | About |
|---|---|
| ![Main menu](screenshots/main-menu.png) | ![About](screenshots/about.png) |

| Frequency Meter | Pulse Analyzer |
|---|---|
| ![Frequency Meter](screenshots/frequency-5hz.png) | ![Pulse Analyzer](screenshots/pulse-analyzer.png) |

## Features

### GPIO Monitor
- Digital HIGH / LOW display
- Edge counter
- LIVE / HOLD modes
- Selectable external GPIO pins

### Frequency Meter
- Rising-edge GPIO interrupt capture
- High-resolution timing using `DWT->CYCCNT`
- Moving-period averaging
- Two-decimal frequency display
- Edge counter
- Signal-loss timeout
- Input intentionally locked to **PC1** in v1.0 for stability

### Pulse Analyzer
- HIGH duration
- LOW duration
- Period
- Duty cycle
- LIVE / HOLD modes

### Signal Generator
- Output pin: **PA7**
- TIM2 hardware-timer driven
- 50% duty cycle
- Presets: **1 Hz, 2 Hz, 5 Hz**
- Continues running while navigating back to the LabMate menu

## Verified self-test

For the built-in loopback test, connect:

```text
PA7 / physical pin 2  ->  PC1 / physical pin 15
```

Then start the Signal Generator and open Frequency Meter.

Verified results on the tested build:

| Generator | Frequency Meter |
|---:|---:|
| 1 Hz | 1.00 Hz |
| 2 Hz | 2.00 Hz |
| 5 Hz | 5.00 Hz |

The Pulse Analyzer was also verified with the same generated square-wave signal.

## Architecture

```text
Signal generation
TIM2 -> PA7

Frequency measurement
PC1 rising-edge IRQ -> DWT->CYCCNT -> period averaging -> frequency
```

## Build

Place the app under your firmware tree:

```text
applications_user/labmate/
```

Build:

```powershell
.\fbt APPSRC=applications_user\labmate
```

Build, install and launch:

```powershell
.\fbt launch APPSRC=applications_user\labmate
```

The app appears on Flipper under:

```text
Apps -> Tools -> LabMate
```

## Files

```text
application.fam
labmate.c
labmate_10px.png
```

## Tested platform

- Flipper Zero
- Momentum Firmware
- API 87.1

## v1.0 limitation

Runtime Frequency Meter pin switching was intentionally disabled after testing showed instability when dynamically reconfiguring the GPIO interrupt on the tested Momentum build. Frequency Meter therefore uses **PC1** in v1.0.

GPIO Monitor and Pulse Analyzer retain their selectable-pin behavior.

## License

MIT
