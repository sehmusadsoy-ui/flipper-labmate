# Changelog

## [1.0] - 2026-10-01

### Added
- GPIO Monitor
- Frequency Meter
- Pulse Analyzer
- Signal Generator
- About screen
- App icon support

### Improved
- Frequency measurement stability with GPIO interrupts
- High-resolution timing with `DWT->CYCCNT`
- Timer-based signal generation using TIM2
- LIVE / HOLD behavior
- Application cleanup and resource handling

### Stability decision
- Frequency Meter runtime pin switching is intentionally disabled in v1.0 and the input is locked to PC1 after dynamic IRQ pin reconfiguration proved unstable on the tested Momentum build.

### Validated
- 1.00 Hz stable reading
- 2.00 Hz stable reading
- 5.00 Hz stable reading
- Pulse Analyzer verified with generator loopback
