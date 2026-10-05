# Flipper LabMate

**LabMate v1.2** is a compact digital-signal diagnostic toolkit for Flipper Zero running Momentum Firmware.

It combines GPIO monitoring, low/high-frequency measurement, pulse analysis, and hardware-PWM signal generation in one external FAP.

> **3.3 V GPIO ONLY.** Do not connect 5 V, 12 V, automotive wiring, mains voltage, or unknown-voltage signals directly to Flipper Zero GPIO.

## Features

- **GPIO Monitor** — digital HIGH/LOW state, edge activity, selectable GPIO pins, LIVE/HOLD
- **Frequency Meter** — dedicated LOW and HIGH measurement modes
- **Pulse Analyzer** — HIGH time, LOW time, period, duty cycle, LIVE/HOLD
- **Signal Generator** — hardware PWM square-wave output on PA7 with 50% duty cycle
- **Instrument-style UI** — pixel icons, state badges, selected-row highlighting, compact key hints

## Screenshots — v1.2

### Flipper Zero / LabMate menu

| Tools | LabMate in Tools |
|---|---|
| ![Tools menu](screenshots/v1.2/01_tools_menu.png) | ![LabMate in Tools](screenshots/v1.2/02_labmate_in_tools.png) |

### Main menu

| GPIO selected | About selected |
|---|---|
| ![Main menu GPIO](screenshots/v1.2/03_main_menu_gpio.png) | ![Main menu About](screenshots/v1.2/04_main_menu_about.png) |

### GPIO & Pulse tools

| GPIO Monitor | Pulse Analyzer |
|---|---|
| ![GPIO Monitor](screenshots/v1.2/05_gpio_monitor.png) | ![Pulse Analyzer](screenshots/v1.2/08_pulse_analyzer.png) |

### Frequency Meter

| LOW / PC1 — 199.99 Hz | HIGH / PB3 — 4.99 kHz |
|---|---|
| ![Frequency LOW](screenshots/v1.2/06_frequency_low_199hz.png) | ![Frequency HIGH](screenshots/v1.2/07_frequency_high_5khz.png) |

### Signal Generator

| STOP — 1 Hz | RUN — 5 kHz |
|---|---|
| ![Generator stopped](screenshots/v1.2/09_signal_generator_stop.png) | ![Generator running](screenshots/v1.2/10_signal_generator_run_5khz.png) |

### About

![LabMate v1.2 About](screenshots/v1.2/11_about.png)

## Frequency Meter

LabMate v1.2 provides two dedicated measurement paths.

### LOW mode — PC1

- period-based frequency measurement
- GPIO rising-edge interrupt capture
- high-resolution timing using `DWT->CYCCNT`
- period averaging / filtering for a stable display

### HIGH mode — PB3

- PB3 mapped to `TIM2_CH2`
- TIM2 counts incoming rising edges directly in hardware
- avoids a GPIO interrupt for every edge at higher frequencies

Controls:

```text
LEFT  -> LOW / PC1
RIGHT -> HIGH / PB3
OK    -> HOLD / LIVE
```

## Signal Generator

Output: **PA7**  
Duty cycle: **50%**  
Generation: **hardware PWM / TIM1**

Available presets:

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

Controls:

```text
LEFT / RIGHT -> change frequency preset
OK           -> start / stop generator
BACK         -> return to menu; generator may remain active
```

## Architecture

```text
Frequency LOW mode:
PC1 rising-edge IRQ
    -> DWT->CYCCNT
    -> period measurement / filtering
    -> frequency

Frequency HIGH mode:
PB3 / TIM2_CH2
    -> hardware edge counter
    -> timed counter delta
    -> frequency

Signal generation:
Hardware PWM
    -> TIM1
    -> PA7
    -> 50% duty square wave
```

## General Controls

- **Up / Down** — navigate menu items
- **Left / Right** — change supported options / measurement mode
- **OK** — open, hold/resume, start/stop depending on screen
- **Back** — return to the previous screen

## Build From Source

Place the app in the Momentum Firmware tree:

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

Installed FAP path:

```text
/ext/apps/Tools/labmate.fap
```

## Tested Platform

- **Device:** Flipper Zero
- **Firmware:** Momentum Firmware
- **Firmware API:** 87.1
- **Application type:** External FAP

## v1.2 Status

The current v1.2 build has been exercised on-device with:

- application/menu navigation
- GPIO Monitor
- LOW / PC1 Frequency Meter
- HIGH / PB3 hardware-counter Frequency Meter
- Pulse Analyzer
- PA7 generator start/stop
- generator frequency selection
- LIVE / HOLD states
- About screen
- operation after disconnecting USB from the development PC

Development after this stable checkpoint can continue as **v1.3-dev** while v1.2 remains the rollback/release baseline.

## Project Structure

```text
flipper-labmate/
├── application.fam
├── labmate.c
├── labmate_10px.png
├── screenshots/
│   └── v1.2/
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
