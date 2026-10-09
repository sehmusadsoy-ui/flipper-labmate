# LabMate v1.6 — GPIO, timer and EXTI ownership audit

**Branch:** `v1.6-dev` only. **Status:** source-code inspection and design
notes; no resource-manager implementation or new hardware test is claimed.
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

## Source-level resource conflict to address before v1.6 Stable

The existing generator intentionally keeps PA7 PWM running after navigating
BACK to the menu. The GPIO Monitor still offers PA7 among eight selectable
inputs, and `gpio_activate()` reconfigures the selected pin to input.
`gpio_release()` likewise configures it analog on exit.

**Potential conflict (not independently reproduced on hardware):**
If the generator is running in the background while the user selects PA7
in GPIO Monitor, the GPIO input/analog reconfiguration may disrupt the TIM1
PWM pin while `generator_running` still reports active. A future centralized
pin-resource owner must prevent or explicitly resolve this configuration
collision. Do **not** simply stop a running generator silently.

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

## Implementation sequence (pending, not yet delivered)

1. Add a single explicit owner state for each reservable pin/peripheral,
   not a set of implicit booleans, while retaining existing resource cleanup.
2. Decide and document whether GPIO Monitor displays PA7 as BUSY when the
   generator is active or prompts for an explicit generator stop. Avoid
   GPIO reconfiguration that silently overrides active PWM.
3. Centralize capture switching and rollback on failed acquisition, then
   verify TIME2/EXTI transitions with real device tests.
4. Regression test Generator BACK → GPIO Monitor → PA7, and repeat
   while switching Pulse/Frequency/Logger views and exiting the app.
5. Update `docs/V1_6_ARCHITECTURE.md` only after each small hardware change
   has passed CI and physical Flipper tests.

**Electrical safety:** Flipper Zero GPIO measurements/inputs must use
3.3 V-compatible digital signals only. No mains, 5 V or unknown voltage
connection. **Static source audits and compilation do not validate runtime
pin-sharing behavior.**
