# Flipper LabMate

LabMate is a compact digital-signal diagnostic toolkit for Flipper Zero running Momentum Firmware.

The project currently has a **stable v1.1 measurement/generator backend** and an actively polished **v1.2 user interface**.

> **3.3 V GPIO ONLY.** Do not connect 5 V, 12 V, automotive wiring, mains voltage, or unknown-voltage signals directly to Flipper Zero GPIO.

## Tools

- **GPIO Monitor** — digital HIGH/LOW state, edge activity and LIVE/HOLD operation
- **Frequency Meter** — dual low/high-frequency measurement modes
- **Pulse Analyzer** — HIGH time, LOW time, period and duty cycle
- **Signal Generator** — hardware PWM square-wave output on PA7
- **About** — compact hardware/mode reference screen

## v1.1 Backend Improvements

### Frequency Meter

LabMate now uses two dedicated measurement paths:

- **LOW mode — PC1**
  - period-based measurement
  - GPIO interrupt capture
  - high-resolution timing using `DWT->CYCCNT`

- **HIGH mode — PB3**
  - TIM2 hardware edge counter
  - avoids per-edge GPIO interrupt overhead at higher frequencies

Left/right input control in the Frequency Meter switches between the two measurement modes.

### Signal Generator

The generator was expanded from the original 1/2/5 Hz presets to:

```text
1 Hz
2 Hz
5 Hz
10 Hz
20 Hz
50 Hz
100 Hz
200 Hz
500 Hz
1 kHz
2 kHz
5 kHz
10 kHz
20 kHz
50 kHz
```

Current generation uses Flipper hardware PWM on **PA7 / TIM1** with a **50% duty cycle**, removing the need for a per-edge generator ISR.

The generator can continue running while returning to the LabMate menu and can be stopped again from the Generator screen.

## v1.2 UI Work

The v1.2 development pass focuses on making LabMate feel like a finished instrument instead of a debug utility.

Current UI work includes:

- compact dashboard-style main menu
- per-tool pixel icons
- stronger selected-row highlighting
- version indicator in the header
- outlined/inverted state badges
- clearer `LIVE`, `HOLD`, `RUN`, `STOP`, `LOW`, and `HIGH` states
- compact key/action hints in the footer
- improved Frequency Meter hierarchy with measurement mode and main frequency value separated visually
- improved Signal Generator hierarchy with output, run state, frequency and duty cycle separated visually
- simplified About screen designed around stable text/line primitives on the tested build

## Architecture

```text
Frequency LOW mode:
PC1 rising-edge IRQ
    -> DWT->CYCCNT
    -> period measurement
    -> frequency

Frequency HIGH mode:
PB3 / TIM2_CH2
    -> hardware edge counter
    -> timed counter delta
    -> frequency

Signal generation:
Flipper hardware PWM
    -> TIM1
    -> PA7
    -> 50% duty square wave
```

## Controls

- **Up / Down** — navigate menu items
- **Left / Right** — change supported options or frequency mode
- **OK** — open, hold/resume, start or stop depending on screen
- **Back** — return to the previous screen

### Frequency Meter

```text
LEFT  -> LOW / PC1
RIGHT -> HIGH / PB3
OK    -> HOLD / LIVE
```

### Signal Generator

```text
LEFT / RIGHT -> change frequency preset
OK           -> start / stop generator
BACK         -> return to menu; generator may remain active
```

## Build From Source

Place the application in the Momentum Firmware tree:

```text
applications_user/labmate/
├── application.fam
├── labmate.c
└── labmate_10px.png
```

Build:

```powershell
.\fbt APPSRC=applications_user\labmate
```

Build, install and launch on a connected Flipper Zero:

```powershell
.\fbt launch APPSRC=applications_user\labmate
```

Installed application path:

```text
/ext/apps/Tools/labmate.fap
```

## Tested Platform

- **Device:** Flipper Zero
- **Firmware:** Momentum Firmware
- **Firmware API:** 87.1
- **Application type:** External FAP

## Development Status

### v1.1 backend

Stable milestone reached for:

- GPIO Monitor
- LOW-frequency meter mode on PC1
- HIGH-frequency hardware counter mode on PB3
- Pulse Analyzer
- PA7 hardware PWM generator
- generator presets through 50 kHz
- application navigation and resource cleanup

### v1.2 UI

UI polish is currently being validated on-device. The redesign keeps the measurement and generator backend separate from the rendering layer so visual changes do not intentionally alter signal-processing behavior.

## Project Structure

```text
flipper-labmate/
├── application.fam
├── labmate.c
├── labmate_10px.png
├── screenshots/
├── docs/
├── CHANGELOG.md
├── RELEASE_NOTES_v1.0.md
├── RELEASE_NOTES_v1.2.md
├── LICENSE
└── README.md
```

## Author

**sehma**

LabMate was developed as a portable GPIO and digital-signal diagnostic utility for Flipper Zero.

## License

This project is released under the **MIT License**. See `LICENSE` for details.
