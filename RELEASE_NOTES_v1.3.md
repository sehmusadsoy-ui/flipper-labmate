# LabMate v1.3 — Release Notes

Date: 2026-10-08

LabMate is a compact GPIO and digital-signal toolkit for **Flipper Zero with Momentum Firmware**.

## Highlights

- **GPIO Monitor:** refreshed digital HIGH/LOW status display and edge counter with LIVE/HOLD.
- **Frequency Meter:** LOW/PC1 high-resolution period mode and HIGH/PB3 TIM2 hardware counter mode; the latter now updates about every 100 ms.
- **Pulse Analyzer:** rising/falling IRQ capture for HIGH/LOW/PERIOD/DUTY and multi-sample smoothing at high frequencies; supported capture pins are PC0, PC1, PB2 and PA4.
- **Signal Generator:** PA7 hardware PWM with 50% duty and presets from 1 Hz to 50 kHz; safe RUN frequency switching without timer stop/restart.
- **UI:** updated measurement screens, LIVE/HOLD and RUN/STOP indications, and calmer refresh under high interrupt load.
- **Stability:** resolved crashes during Pulse Analyzer pin switching and signal-generator freezes during running frequency changes; cleaned up GPIO interrupt edge settings.

## Functional verification

Tested using Flipper Zero with Momentum Firmware API 87.1 and a **PA7-to-input 3.3 V loopback jumper**. Signal Generator and Frequency Meter measurements were checked through 50 kHz. Pulse Analyzer produced the expected nominal HIGH/LOW/per-period readings at 1 Hz, 20 kHz and 50 kHz. At 50 kHz its measured duty ranged approximately 49.8%–50.2% during one test.

These checks are **functional**, not independent calibration. Accuracy for arbitrary external signals, every frequency, and long-duration stability remains unverified. GPIO Monitor's polled edge count is not a high-frequency counter; use Frequency Meter HIGH/PB3 instead.

## Installation

Use the release asset `labmate-v1.3.fap` (or `dist/labmate-v1.3.fap` in the repository). Check the checksum in `dist/SHA256SUMS.txt` if desired. The external app is installed to `/ext/apps/Tools/labmate.fap` in the tested setup.

Firmware/API compatibility varies by build. Rebuild from source using Momentum's FBT if your firmware ABI differs.

## Safety

**3.3 V GPIO ONLY.** Never directly connect 5 V, 12 V, automotive electrical lines, mains or unknown-voltage signals to the Flipper Zero GPIO header. Use appropriate protection/conditioning for external circuits.

## Changes since v1.2

See `CHANGELOG.md`. The v1.2 Stable tag/release remains available as a fallback.
