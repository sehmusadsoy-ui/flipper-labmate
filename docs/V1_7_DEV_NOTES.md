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

## PWM Studio: first v1.7 functional feature slice (2026-10-11)

- The original 15 TIM1/PA7 presets are unchanged. An additional CUSTOM selection provides 1..50,000 Hz in 1 Hz resolution, with selectable edit steps of 1/10/100/1000 Hz.
- PWM duty is adjustable in 5% steps from 5% through 95%; default 50%. Live parameter changes use `furi_hal_pwm_set_params` without stopping/reclaiming TIM1.
- Normal controls: LEFT/RIGHT cycle presets plus CUSTOM, UP/DOWN adjust duty, short OK START/STOP, BACK returns to menu while the active generator keeps running.
- STOP-only custom editor: long OK enters, LEFT/RIGHT change Hz by the selected step, UP/DOWN select the step size, short OK commits; BACK cancels. Draft changes never reach a running PWM output.
- Generator input intentionally uses key-release SHORT instead of PRESS so long OK cannot accidentally START PWM. The menu-opening OK release is suppressed when entering the screen.
- The app still stops PWM on final exit, preserves PA7 reservation in the background, and retains the v1.6.1 capture/resource policies.
- **Profiles compatibility:** the existing 32-byte CRC codec holds only preset indices 0..14, not duty/custom Hz. CUSTOM SAVE is blocked with `PRESET ONLY`; loading a legacy preset resets duty to 50%. Profiles are not silently re-encoded or corrupted. A future versioned profile schema is needed for full PWM Studio settings storage.
- Added portable bounds/stepping tests `tests/test_pwm_settings.c.inc` to v1.7 CI and extended source-boundary guards.
- Physical Flipper validation of frequency, duty, key behavior, and PA7 ownership is still pending; successful automated builds are not a calibration claim.

## Event Counter: first hardware-counting implementation (2026-10-11)

- Added **Event Counter** as the fourth MEASURE instrument. Historical tool IDs 0..7 are preserved; new Counter is appended as ID 8.
- Counts actual **rising edges** on **PB3 / TIM2_CH2** in hardware external-clock mode, not inferred Hz multiplied by time and not CPU-side GPIO edge polling. Input must be compatible with 3.3 V Flipper GPIO levels.
- `LabMateCaptureCounter` owns the PB3/TIM2 peripheral separately from Frequency HIGH; the common capture core rejects overlapping capture acquisitions. Counter START/STOP holds/releases exactly one owner.
- `labmate_event_counter.c/.h`: STOP-only entry, OK to begin a new count/reset hardware baseline, OK to freeze the counter, UP resets *only when stopped*, BACK always stops and returns to menu.
- Samples 32-bit TIM2 hardware snapshots in the app loop and accumulates an unsigned delta to a saturating **64-bit total**, including a 32-bit TIM2 wrap between successive polls. Requires fewer than 2^32 edges between two polls; under realistic 3.3 V signals this is a conservative limit. Frozen final snapshot taken after counter disable.
- 128x64 display prints the full decimal total (up to UINT64_MAX) using a portable formatter instead of relying on target-libc 64-bit `printf` support, together with elapsed session seconds.
- Expanded exclusive-owner transition tests across LOW PC1 / HIGH PB3 / PULSE / COUNTER and a portable counter wrap/saturation/formatting test; added dedicated CI step and static module-boundary assertions.
- **Physical-device checks not yet performed:** 1/100/1000 Hz known-source event counts over timed windows, STOP/UP RESET behavior, BACK/exit release, Frequency HIGH/PULSE resource transitions, and simultaneous independent PA7 PWM. Do not treat CI as metrology calibration.

## Next

- Review the app-level capture teardown coordinator and complete regression tests for transitions between LOW/HIGH/PULSE/LOGGER and PA7 background PWM.
- Validate the PWM Studio feature slice on the physical Flipper and check PA7 background ownership under navigation/monitoring.
- Implement Event Counter, button analysis and alerts, respecting existing IRQ restrictions (PC3/PB3 EXTI3 and PA6 EXTI6 conflict with buttons; PWM owns PA7).
- Bundle changes into focused on-device sessions, using only verified 3.3 V digital signals.
- Prior to v1.7 RC, verify physical output frequency/duty and switching, menu reentry, frequency/pulse STATS and HOLD, Logger/History and Profiles. Avoid claims of calibrated metrology.
