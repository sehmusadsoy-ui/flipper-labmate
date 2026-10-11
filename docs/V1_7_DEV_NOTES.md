# LabMate v1.7 Development — implementation checkpoints

Baseline: device-tested v1.6.1 version-label correction source `84f3741da1a083b0acba189d551d3f713e867393`.
Published v1.6.1 Stable remains `bc63271afe572c393c1febd0f0ef7039404bc937`, unmodified.
Only `v1.7-dev` is changed during this work.

## Official scope (ROADMAP.md)

1. Adjustable PWM duty cycle, custom frequency selection, safe persistent generator control.
2. True event/pulse counting using suitable GPIO/hardware timers.
3. Button bounce/response analysis, configurable threshold alerts.
4. Actual-device verification of output frequency, duty and switching behavior.

## Inherited v1.6 incomplete refactoring scope

- Split Frequency LOW PC1 / HIGH PB3, Pulse and Generator hardware operations from `labmate.c`.
- Centralize capture eligibility/pin selection and EXTI/TIM resource cleanup.
- Preserve old measured values, display, logger/profile data compatibility and PA7/TIM1 independent generator ownership.

## Completed in v1.7-dev so far

- `labmate_generator.c/.h`: TIM1/PA7 PWM HAL ownership and unchanged 15 presets at 50% duty.
- `labmate_frequency_tim2.c/.h`: PB3/TIM2 register configuration, read and teardown.
- `labmate_capture_exti.c/.h`: common falling/rising EXTI cleanup.
- `labmate_capture_core.c/.h`: shared physical pin table and exclusive-capture acquire gate.
- `labmate_pulse_capture.c/.h`: Pulse rise/fall IRQ, current averaging windows, START/STOP.
- `labmate_frequency_capture.c/.h`: LOW PC1 IRQ and HIGH PB3 capture lifecycle.
- `labmate_monitor_gpio.c/.h`: GPIO Monitor activation/read/release, including PA7 PWM ownership guard.
- `scripts/check_v16_boundaries.py`: updated source-boundary safety guards.
- `.github/workflows/build-v1.7.yml`: separate v1.7 CI, including Momentum compile, portable tests and mock USB installer.

**Automated checkpoints**:
- Pulse extraction: run `38128588103`, all jobs success.
- LOW/HIGH Frequency extraction: run `38128704441`, all jobs success.
- GPIO Monitor extraction: run `38128855667`, all jobs success.
These are CI/compile results, **not** physical Flipper measurement validations.

## Next

- Review the app-level capture teardown coordinator and complete regression tests for transitions between LOW/HIGH/PULSE/LOGGER and PA7 background PWM.
- Add PWM Studio adjustable duty/custom frequency as *separate* functional changes, testing bounds, ownership and stop behavior.
- Implement Event Counter, button analysis and alerts, respecting existing IRQ restrictions (PC3/PB3 EXTI3 and PA6 EXTI6 conflict with buttons; PWM owns PA7).
- Bundle changes into focused on-device sessions, using only verified 3.3 V digital signals.
- Prior to v1.7 RC, verify physical output frequency/duty and switching, menu reentry, frequency/pulse STATS and HOLD, Logger/History and Profiles. Avoid claims of calibrated metrology.
