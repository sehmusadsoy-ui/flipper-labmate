# LabMate v1.2 Development Notes

Date: 2026-10-05

LabMate v1.2 is the UI/UX refinement pass built on top of the stable v1.1 signal-processing backend.

## What changed in the backend before the UI pass

### Dual-mode Frequency Meter

LabMate now separates low- and high-frequency measurement into two dedicated paths:

- **LOW / PC1** — GPIO interrupt + `DWT->CYCCNT` period timing
- **HIGH / PB3** — TIM2_CH2 hardware edge counter

This avoids forcing one measurement method to cover every frequency range.

## Generator improvements

The Signal Generator now offers presets from **1 Hz through 50 kHz**:

`1, 2, 5, 10, 20, 50, 100, 200, 500, 1k, 2k, 5k, 10k, 20k, 50k Hz`

Generation uses Flipper hardware PWM on **PA7 / TIM1** at **50% duty cycle**.

## v1.2 interface direction

The original interface was functional but looked closer to a debug utility than a finished instrument. v1.2 introduces a more consistent visual system:

- icon-based main menu
- compact header and version marker
- selected-row emphasis
- state badges
- clearer LIVE / HOLD feedback
- clearer LOW / HIGH frequency-mode feedback
- clearer RUN / STOP generator feedback
- improved footer button hints
- stronger hierarchy around the primary measurement value
- cleaner Frequency Meter and Signal Generator layouts

## About screen stability note

During the UI polish pass, the About screen was tested separately from the rest of the rendering layer. A minimal text-based layout proved stable on-device, while more complex framed layouts caused freezes on the tested build.

For this reason, the current v1.2 About screen intentionally favors simple text and line primitives until the rendering issue is isolated further.

This does not affect GPIO measurement, frequency measurement, pulse analysis, or signal generation.

## Safety

Flipper Zero GPIO is **3.3 V logic**.

Do not connect 5 V, 12 V, automotive wiring, mains voltage, or unknown-voltage signals directly to the GPIO header. Use appropriate conditioning, protection, level shifting, or isolation for external hardware.

## Tested environment

- Flipper Zero
- Momentum Firmware
- API 87.1
- External FAP build

## Status

- **v1.1 backend:** stable milestone
- **v1.2 UI:** active on-device polish and validation
