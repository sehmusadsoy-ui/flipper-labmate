# LabMate v1.6 — GPIO, timer and EXTI ownership audit

**Branch:** `v1.6-dev` only. **Status:** first PA7 resource-policy guard implemented; overall GPIO/EXTI/timer ownership manager remains planned. No physical-device test is claimed.
**Baseline:** LabMate v1.5 Stable remains unchanged.

## Resources observed in `labmate.c`

| Tool / capture mode | GPIO pins | Peripheral or interrupt | Expected cleanup |
| --- | --- | --- | --- |
| GPIO Monitor | PC0, PC1, PC3, PB2, PB3, PA4, PA6, PA7 | Direct GPIO input polling | `gpio_release()` switches the selected pin to analog |
| Frequency LOW | PC1 | Rising-edge GPIO IRQ, DWT timestamp | `frequency_interrupt_stop()` detaches callback; release pin |
| Frequency HIGH | PB3 | TIM2_CH2 external edge counter; TIM2 bus | `frequency_hw_stop()` stops counter/channel, disables bus, releases PB3 |
| Pulse Analyzer | PC0, PC1, PB2, PA4 | Both-edge EXTI callback + DWT timestamp | `pulse_interrupt_stop()` detaches callback and clears both EXTI triggers |
| Data Logger | PC1 or PB3 (frequency) / PC1 (pulse) | Reuses appropriate capture mode | `logger_capture_stop()` invokes capture cleanup before releasing pin |
| Signal Generator | PA7 | TIM1 hardware PWM; deliberately allowed to run after BACK | `generator_stop()` turns PWM off; app exit calls stop |

**Do not use PC3/PB3/PA6 as Pulse Analyzer interrupt pins:**
the board firmware uses EXTI3 for OK and EXTI6 for DOWN; these are
polling-only GPIO Monitor options as documented in the source.

## PA7 background PWM collision — guarded in v1.6-dev (device test pending)

The existing generator intentionally keeps PA7 PWM running after navigating
BACK to the menu. The GPIO Monitor still offers PA7 among eight selectable
inputs, and `gpio_activate()` reconfigures the selected pin to input.
`gpio_release()` likewise configures it analog on exit.

**Previously identified conflict (not independently reproduced on hardware):**
If the generator is running in the background while the user selects PA7
in GPIO Monitor, the GPIO input/analog reconfiguration could disrupt TIM1
PWM while `generator_running` still reports active.

**v1.6-dev code-level mitigation:**
- The portable `labmate_resource_policy.c/.h` returns PA7 as unavailable
  to GPIO Monitor while `generator_running` is true.
- GPIO Monitor entry falls back to PC1 if PA7 was selected previously.
- LEFT/RIGHT navigation wraps through the remaining seven pins, skipping PA7.
- Both `gpio_activate()` and `gpio_release()` are guarded, so an old selected
  PA7 value cannot silently reconfigure an active PWM output.
- The GPIO Monitor shows `PA7 BUSY` while PWM owns that pin. Signal Generator
  continues to run in background until explicitly stopped or the app exits.
- `tests/test_resource_policy.c.inc` checks policy logic on a desktop C compiler,
  while CI builds the full development FAP and runs static boundary guards.
  `application.fam` explicitly uses `sources=["*.c"]` so the host-only
  `.c.inc` test is not linked into the FAP. The original Momentum manifest
  default `*.c*` pattern would also match `.c.inc` files.

This is **not** proof of on-device timing, peripheral-state preservation or
complete resource management. PA7 still requires a physical regression test;
remaining PC1 EXTI, TIM2 and concurrent-resource ownership work is planned.

Additional resource handoff invariants:
- Only one of the LOW PC1 IRQ, HIGH PB3 TIM2 and Pulse IRQ capture modes
  should own measurement resources at a time.
- Stop and detach previous callbacks before pin switches; clear stale
  falling-edge EXTI triggers before PC1 frequency capture.
- Keep the 1 Hz CSV writes outside interrupt callbacks and outside the GUI
  drawing mutex.
- Do not reset MIN/MAX statistics or HOLD behavior as a side effect of
  moving ownership functions.
- Preserve the generator's current background policy until the replacement
  policy is designed and reviewed.
- Releasing the app must stop PWM, stop active capture, synchronize/close an
  open log and close history resources.

## Implementation sequence and outstanding checks

1. **Implemented (development only):** PA7 exclusive-use monitor policy,
   pin-entry fallback, safe navigation, no-reconfiguration guard and busy UI.
2. **Implemented (development only):** host-native policy tests and GitHub
   static boundary checks; the Momentum SDK full-build gate remains active.
3. **Implemented (source refactor, device test pending):** the shared
   `capture_stop_all()` reuses existing LOW PC1 IRQ, HIGH PB3/TIM2 and
   Pulse EXTI stop implementations. Used by mode changes, Logger capture
   stop, BACK and app exit. No capture start/ISR or TIM1 PWM logic changed.
4. **Implemented (initial exclusive-owner stage, device test pending):**
   `LabMateCaptureOwner` tracks the active LOW PC1 IRQ, HIGH PB3/TIM2 or
   Pulse EXTI capture. Each start checks the current owner, every active flag
   and the requested pin before touching hardware, and each stop clears
   ownership. The shared teardown resets the owner to None. Pure policy
   functions and host-native pin/owner/flag matrix tests cover invalid
   claims. Independent TIM1/PA7 generator operation is unchanged.
5. **Pending:** visible error reporting, hardware acquisition rollback,
   and full fail-safe resource cleanup after external HAL errors
   for PC1 IRQ, PB3 TIM2 and active generator resources, including handling
   failed acquisition and cleaning up callbacks on exit.
6. **Pending device regression:** Generator ON → BACK → GPIO Monitor → navigate
   across PA7, then Generator OFF → PA7 becomes selectable again; also test
   switching Frequency/Pulse/Logger views, HOLD/LIVE and app exit. Do not
   connect unknown or unsafe voltages.
7. **Pending:** update broader project roadmap only after device-level
   evidence supports the stability claim.

**Electrical safety:** Flipper Zero GPIO measurements/inputs must use
3.3 V-compatible digital signals only. No mains, 5 V or unknown voltage
connection. **Static source audits and compilation do not validate runtime
pin-sharing behavior.**
