# LabMate v1.0

First stable release of LabMate for Flipper Zero.

## Highlights

- GPIO Monitor
- IRQ-based Frequency Meter
- DWT cycle-counter high-resolution timing
- Pulse Analyzer
- TIM2 hardware-timed Signal Generator
- LIVE / HOLD measurement modes
- Signal-loss detection
- Stable 1 Hz, 2 Hz and 5 Hz self-test results

## Frequency engine

The Frequency Meter uses rising-edge GPIO interrupts instead of main-loop polling.

Edge timestamps are measured using the ARM DWT cycle counter, providing substantially finer timing resolution than the RTOS tick counter.

## Signal Generator

The original polling-based generator was replaced with a TIM2 hardware-timer implementation.

This eliminated the observable timing jitter present in earlier versions.

Verified measurements:

- 1 Hz -> 1.00 Hz
- 2 Hz -> 2.00 Hz
- 5 Hz -> 5.00 Hz

## Stability

For v1.0, the Frequency Meter input is intentionally locked to PC1.

Runtime Frequency Meter pin switching was disabled after testing showed that dynamically reconfiguring the GPIO interrupt could cause instability on the tested Momentum build.

GPIO Monitor and Pulse Analyzer retain selectable GPIO operation.

## Hardware self-test

Connect:

```text
PA7 / Pin 2 -> PC1 / Pin 15
```

No external voltage source is required for this loopback test.

## Safety

Use only known 3.3 V-compatible digital signals.

Do not connect Flipper GPIO directly to 5 V, 12 V, automotive wiring, or unknown-voltage sources.
