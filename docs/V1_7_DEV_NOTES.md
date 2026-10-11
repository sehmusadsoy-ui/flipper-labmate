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
- **CI checkpoint:** GitHub Actions `38130677078`, source `1fc24a81998ae6f197a0717e9beb4ef69057244d`, both compile/portable-test and Windows installer jobs succeeded; `labmate` FAP artifact and SHA256SUMS were created.
- **Physical-device checks not yet performed:** 1/100/1000 Hz known-source event counts over timed windows, STOP/UP RESET behavior, BACK/exit release, Frequency HIGH/PULSE resource transitions, and simultaneous independent PA7 PWM. Do not treat CI as metrology calibration.

## Button Analyzer: first PC1 dry-contact analyzer (2026-10-11)

- Added `Button Analyzer` as tool ID 9 in the MEASURE group, without renumbering original tools or changing Profiles data. MEASURE's 5 items use the existing scrollable three-row menu.
- Input is **PC1 / EXTI1**, armed for both edges with an internal pull-up (LOW = contact closed). Testing is intended for a dry contact between PC1 and GND or an independently verified 3.3 V-compatible digital input; never connect higher voltages. EXTI3/6 reserved system-button lines and PA7 generator output are not used.
- `LabMateCaptureButton` is distinct from Pulse/LOW PC1/HIGH PB3/Counter capture owners. START requires full exclusive acquisition; STOP/BACK detaches callback, clears both EXTI triggers, restores analog pin mode, and releases ownership.
- ISR records timestamped level changes only. `labmate_button_logic.c/.h` is a portable debouncer that confirms transitions after a selectable 5/10/20/50 ms quiet interval, reports bounce edges, DWT-cycle bounce width, first-edge-to-stable settling latency, confirmed presses/releases and stable press-hold time. Bounce glitches that return to the original level are rejected.
- **Meaning of response:** electrical first-contact-edge to debounced stable-state detection, **not** mechanical actuation-before-first-contact or human reaction latency. DWT edge timing is subject to interrupt timestamp latency and requires physical validation; the settle timestamp also depends on the app polling cadence.
- Controls: OK START/STOP, LEFT/RIGHT set debounce while STOP, UP reset while STOP, BACK stops/releases and returns to menu. The UI is read-only and uses an IRQ-safe published snapshot.
- Added host-native tests for clean presses, multi-edge bounce, rejected glitches, counter and CPU-cycle timer rollover, and an extended capture-ownership matrix; CI run `38131174602` at source `45d658c65e74a3cf78aeea41831a018a31a886f5` completed both build and Windows installer jobs successfully.
- **Device gate still open:** verify real PC1 contact handling, measured bounce/settle timing, STOP/BACK release, interactions with LOW PC1 and Pulse PC1, and independent PA7 PWM with 3.3 V-compatible signals.

## Threshold Alerts: initial visual alert engine (2026-10-11)

- Added `Threshold Alerts` to OUTPUT as appended tool ID 10. Original tool IDs, existing menu groups, Stable tags and legacy profile data remain unchanged.
- `labmate_threshold.c/.h` is a hardware-independent alert state machine, armed explicitly via OK. LEFT/RIGHT choose source while disarmed, UP/DOWN change the bound within conservative limits; DOWN acknowledges a latched event while armed. OK disarms and clears history; BACK leaves the configuration screen without implicitly disarming.
- Four selectable sources: Frequency Meter rate threshold (1..50,000 Hz, 10-Hz steps), Pulse duty percentage (5..95%, 5% steps), true 64-bit Event Counter rising edges (1..1,000,000 edges, 10-edge steps) and Button Analyzer first-edge-to-stable settling time (1..1,000 ms, 5-ms steps). Changing source restores its default threshold.
- App thread monitors only the **live and valid** corresponding instrument: Frequency and Pulse in LIVE rather than HOLD, Event Counter only while its PB3 TIM2 capture owns RUN, and Button only after its PC1 EXTI1 capture has produced a debounced transition. Other screens or invalid measurements do not generate new trips. Frequency mHz and duty permille are converted by truncating to whole Hz/percent before comparing to user-facing thresholds; a value below the limit never trips.
- The first valid threshold crossing latches TRIPPED; while the signal remains above the bound it does not repeatedly increase the trip counter. Dropping below and returning above counts a new crossing. Invalid data stops the active indication but preserves the latch until explicit acknowledgement or disarm.
- An on-instrument `ALERT` indicator appears in the top right for the selected measurement source when a trip is latched; the configuration screen shows ARM/OFF, source, limit and TRIPPED status.
- **Visual-only**: no buzzer, vibration, automatic PWM changes, GPIO side effects, SD modifications or persisted thresholds. Alert settings survive menu navigation only while LabMate is running.
- Added `tests/test_threshold.c.inc` for arming, source locks, bounds, valid/invalid data, latching, crossing and acknowledge semantics, plus source-boundary assertions and a dedicated CI job step.
- **Automated checkpoint PASS:** GitHub Actions `38131696438`, tested code commit `1f1de6d6aa70350ea135856026333e16bcdb69ce`, both native/Momentum build and Windows mock installer jobs passed; `labmate` artifact generated. This does not replace electrical device checks.
- **Physical device validation pending**: threshold at/below/above on each of Frequency/Pulse/Counter/Button, HOLD/STOP signal invalidation, source changes when disarmed, acknowledgement and visual badge legibility on the monochrome display.

## Stage 7 — focused 128x64 UI cleanup (2026-10-11)

- **Button Analyzer** now has two read-only pages: SUMMARY (PC1/debounce/contact state/presses/releases) and TIMING (bounce width, electrical settling, contact hold, bounce edges). DOWN flips the page in RUN or STOP without touching EXTI; entering the instrument starts on SUMMARY. LEFT/RIGHT debounce changes remain STOP-only and UP reset remains STOP-only.
- Full UINT32 decimal values use dedicated rows rather than concatenated multi-counter strings that clipped at 128 pixels. Secondary-font baselines are separated and the footer is bounded.
- **Threshold Alerts** now differentiates DISARMED, NO LIVE SAMPLE, BELOW LIMIT, ABOVE LIMIT and TRIPPED. An alert takes the already existing status badge slot in the selected Frequency/Pulse/Counter/Button screen (ALRT), rather than drawing an extra badge that covered a title or state.
- **PWM Studio** custom-edit hints are shorter and explicitly display BACK cancellation, with frequency-step controls retained.
- **Event Counter** abbreviates its STOP footer; the full UINT64 decimal display is preserved.
- Added `scripts/check_v17_ui_layout.py` to CI. It tests worst-case decimal string widths against a conservative 6px compact-font approximation and checks key interface labels/controls. Physical display inspection remains necessary; this is not pixel-perfect font raster validation.

## Physical on-device validation — Test 1 (2026-10-11)

- Installed the **exact CI-tested** v1.7 development FAP from workflow `38132070727`, source `8aebe8ae1a41a7ddfad8f6de1babc9479aa3638c`, on Flipper Zero over Windows/COM7. User's console confirmed matching GitHub Actions run SHA, SHA256 `AC521C13040B82657FE798C6CBFC3E432A663749B6BAE7CED9FBEABF7456345E`, full transfer and successful launch request.
- **Device Test 1: 6/6 PASS**, user physically confirmed: v1.7d home version, Event Counter entry, Button Analyzer entry, Threshold Alerts entry, PWM Studio initially STOP, BACK/navigation without freeze.
- This validates only menu/boot/safe-initial-state behavior. It is **not** PWM output measurement, GPIO capture metrology, alert crossing verification, or a completed v1.7 release gate.
- **Device Test 2A: 4/4 PASS**, user physically measured TIM1/PA7 PWM looped into PC1 Pulse Analyzer: 100 Hz at 50% duty HIGH=5 ms, LOW=5 ms, PERIOD=10 ms, DUTY=50%; and 100 Hz at 25% duty HIGH=2.5 ms, LOW=7.5 ms, PERIOD=10 ms, DUTY=25%. User reported the displayed values matched all expected figures, PWM persisted across BACK navigation, and explicit STOP worked correctly. Verified 3.3 V-compatible self-loop digital test only, not externally calibrated timing accuracy.
- **Device Test 2B: 4/4 PASS**, user physically confirmed 1 kHz at 50% duty HIGH/LOW/PERIOD/DUTY correct, STOP-only CUSTOM 1235 Hz edit and save successful, 1235 Hz at 50% duty Pulse Analyzer readings correct, and PWM remained active across menu navigation until explicit STOP. Together Tests 2A+2B total **8/8 PASS** for targeted PWM Studio checks; not a calibration claim for the entire 1–50 kHz range.
- **Device Test 3A: 4/4 PASS**, user physically verified Event Counter PB3/TIM2 with PA7 PWM output at 10 Hz: count grew during RUN, 103 rising edges displayed for an approximately 10-second manually timed window (ideal 100; compatible with ~10.3-second observation, not calibrated), STOP froze the count, UP reset to 0 while STOP, and RUN restarted counting. User-confirmed result; no 1 kHz event-count or cross-tool ownership claim yet.
- **Device Test 3B: 4/4 PASS.** User confirmed Event Counter RUN/BACK, Frequency Meter HIGH PB3 at approximately 10 Hz without ERR, Event Counter restart, and Frequency Meter HIGH PB3 working again. Tests 3A and 3B: 8/8 PASS. These observations validate resource handoff, not calibrated accuracy.
- **Device Test 4A: PASS**, user physically confirmed Button Analyzer PC1 using the 1 Hz / 50% PA7 digital stimulus behaved as expected, with BOUNCE = 0 us, BOUNCE EDGES = 0, and reported SETTLE readings of 11, 18 and 19 ms using a 10 ms quiet-time configuration. Poll cadence after the minimum quiet interval explains varying displayed settle values. User says remaining controls behave as expected; HOLD's exact numeric reading was not separately reported. This test does not validate mechanical contact bounce or human reaction time.
- **Device Test 4B DEFERRED:** user currently has no mechanical momentary button; real PC1 switch contact/bounce behavior is still unverified. Test 4A remains the passing digital-stimulus check. No extra hardware is required to continue the other validation gates.
- **Device Test 5A: 4/4 PASS**, user physically confirmed Threshold Alerts FREQUENCY at 100 Hz: PA7-generated 50 Hz measured through PB3 without alarm, 200 Hz caused ALRT on Frequency Meter, the configuration screen retained TRIPPED, and DOWN acknowledged the alert. PWM was stopped after the check. This validates frequency-source alert threshold crossing and visual latch/acknowledgment on device, not every source.
- **Device Test 5B: 4/4 PASS**, user physically confirmed PULSE DUTY threshold at 50%: no alert at 25% duty; ALRT at 75% duty; retained TRIPPED in the Threshold Alerts screen; DOWN acknowledgment, OFF and PWM STOP all worked. Together Test 5A + Test 5B: 8/8 PASS for Frequency and Pulse Duty threshold alerts; Counter and Button Settle threshold sources remain unverified.
- **Device Test 5C: 4/4 PASS**, user reported all steps completed without issues: EDGE COUNT default 100 edges, PA7 PWM at 20 Hz into PB3; no warning below 100 edges; ALRT at/after threshold; TRIPPED retained; acknowledgment, OFF and PWM STOP behaved correctly. Tests 5A+5B+5C total **12/12 PASS** across Frequency, Pulse Duty and Event Counter alert sources. The Button Settle alert source is not yet physically verified.
- **Device Test 5D: PASS (4/4 targeted checks)**, user physically confirmed configuring BUTTON SETTLE 5 ms, PC1 Button Analyzer detecting first stable PRESS:1 while RELEASE:0, immediate ALRT on valid press settling time above threshold, retained TRIPPED in Threshold Alerts and DOWN acknowledgement. This confirms alert triggers from the first confirmed press without waiting for release. User reported displayed TRIPPED and successful clearing in a follow-up. The test used clean PA7 digital stimulation and does not validate a mechanical contact's bounce.
- **Threshold Alerts physical checkpoint: 16/16 PASS** across Frequency 5A, Pulse Duty 5B, Event Counter 5C and Button Settle 5D. Real-switch Test 4B remains deferred due to unavailable mechanical button.
- **Next device gate: legacy v1.6.1 feature regression on v1.7d**, including Frequency LOW PC1 / Pulse LIVE-HOLD-STATS, Logger modes, History and Profiles S1; make no change to v1.6.1 Stable release.

## Legacy feature regression — Test 6A (2026-10-11)

- User physically confirmed PASS for v1.7 Frequency Meter LOW PC1 (100 Hz), Pulse Analyzer HIGH/LOW/PERIOD/DUTY, and STATS/MIN/MAX while running a 3.3 V PA7 -> PC1 digital loopback.
- User confirmed Pulse HOLD freezes values **while remaining on the Pulse screen**. Upon BACK, editing PWM to 200 Hz elsewhere and reopening Pulse, the reading updates to 200 Hz. This is the **intended existing lifecycle**: `case LabMateToolPulse` sets `app->hold = false`, resets measurement, and starts fresh capture. The prior test instruction incorrectly expected HOLD to persist across leaving/reentering the instrument; **not a device failure**.
- **Test 6A closure: PASS**. User confirmed on-device OK HOLD -> OK LIVE toggling without leaving Pulse Analyzer resumes valid measurement and remains responsive. Together with earlier user reports: Frequency LOW PC1, Pulse HIGH/LOW/PERIOD/DUTY, Pulse STATS/MIN/MAX, HOLD freeze and in-screen resume PASS. Reopening Pulse after leaving resets HOLD by design; no firmware bug reported and no firmware modification required.
- **Device Test 6B: 4/4 PASS**, user physically reported successful SD CSV recording for FREQ / PC1 LOW, PULSE / PC1, and FREQ / PB3 HIGH with PA7 100 Hz / 50% loopback, plus saved nonzero-row counts and no app error in all three modes. Real Flipper on v1.7d; no claim about external calibration.
- **Next physical Test 6C:** read-only Log History check: latest three CSV files corresponding to all three logger modes should appear and open as matching FREQ/PC1, PULSE/PC1, FREQ/PB3 with nonzero ROWS; optionally open an older visible log. Verify BACK transitions without SD error. No changes or deletions to user files; existing Profiles S1 checked separately.
- Legacy Logger 3 modes, Log History and Profiles S1 remain to be retested on v1.7d. No change to v1.6.1 Stable.

## Next

- Review the app-level capture teardown coordinator and complete regression tests for transitions between LOW/HIGH/PULSE/LOGGER and PA7 background PWM.
- Validate the PWM Studio feature slice on the physical Flipper and check PA7 background ownership under navigation/monitoring.
- Review Event Counter, Button Analyzer and Threshold Alerts integration for edge cases, then complete the focused v1.7 UI improvements.
- Bundle changes into focused on-device sessions, using only verified 3.3 V digital signals.
- Prior to v1.7 RC, verify physical output frequency/duty and switching, menu reentry, frequency/pulse STATS and HOLD, Logger/History and Profiles. Avoid claims of calibrated metrology.
