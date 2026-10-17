# LabMate v1.9 — first Logic Scope capture resource gate

**Status 2026-10-18: SOURCE/DESIGN REVIEW + INDEPENDENT HOST TESTS ONLY.**
No 1.9 GUI, Flipper EXTI callback or waveform capture has yet been enabled on-device.
No v1.9 FAP has been installed or published. The final E11 matched custom
Momentum FAP and ordinary v1.8 Stable remain unchanged.

## Verified existing E11 ownership rules

Actual source read from `dev/v1.9-logic-scope`:
- `src/labmate_capture_session.c`: Pulse allowed indices
  `0/1/3/5` = **PC0/PC1/PB2/PA4**. PC3 and PB3 share EXTI3 with
  a system button path; PA6 uses EXTI6 for another system button.
  **Do not register a new interrupt on PC3, PB3 or PA6.**
- `src/labmate_resource_policy.[ch]`: a single local capture owner
  among Frequency LOW, Frequency HIGH, Pulse, Counter and Button.
  `LabMateCaptureScope` **does not exist yet**. Adding it requires
  explicit allowed-pin rules and tests, not assuming there is a free owner.
- `src/labmate_frequency_capture.c` and `labmate_button_capture.c`:
  **PC1/EXTI1** uses `FURI_HAL_LEASE_IRQ_PC1`, a non-asserting
  `furi_hal_gpio_try_add_int_callback` and a cleanup path that only
  changes GPIO/EXTI after checking its own saved firmware lease handle.
  The matching firmware must export
  `FURI_HAL_RESOURCE_LEASE_API_V1` and
  `FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK`. No safe stock-Momentum
  fallback may register the IRQ with the older assert-based API.
- `src/labmate_pulse_capture.c`: lease bits for PC0, PC1, PB2, PA4
  differ and are not interchangeable. Independent custom firmware
  clients may still bypass the experimental leases.
- `src/labmate_capture_session.c`: ownership teardown deliberately
  **does not automatically stop background PWM** on PA7/TIM1.
- `src/labmate_monitor_gpio.c`: pin-only leases protect Monitor
  against participating native clients; old foreign GPIO users may
  still ignore that lease table.

| Proposed capture input | Existing known conflicts | First v1.9 implementation decision |
| --- | --- | --- |
| **PC1 / EXTI1** | Frequency LOW, Button, Pulse, Logger Pulse/LOW; I2C PC1 SDA, pin Monitor; native JS GPIO | **Candidate for single-channel first**, but DISABLED until firmware lease+callback, I2C denial, existing local capture owner enum/STOP integration and tests are implemented |
| PC0 / EXTI0 | Pulse, I2C PC0 SCL, native serial expansion LPUART1 callback | Later after PC1 accepted; no assumed independence |
| PB2 / EXTI2 | Pulse, native NFC PA2/EXTI2, external CC1101, ICM42688P | **Do not enable** without foreign owner arbitration |
| PA4 / EXTI4 | Pulse, OneWire DS18B20, Accessor Wiegand | **Do not enable** before exclusive 1-Wire/Wiegand conflicts resolved |
| PB3 / TIM2, shared EXTI3 | Frequency HIGH, Counter, native TIM2 clients; system EXTI3 | **No scope EXTI3** |
| PC3 / EXTI3 | System button/shared EXTI3 | **No scope EXTI3** |
| PA6 / EXTI6 | System button/shared EXTI6 | **No scope EXTI6** |
| PA7 / TIM1 PWM | Active generator and native PWM; EXTI7/accessor Wiegand | **Not an input to scope** |

## First implemented unit — isolated pure-C edge recorder

`src/labmate_scope_buffer.[ch]` is a bounded producer-append buffer,
compiled by the normal `src/*.c` manifest but **not hooked to application
UI, state or GPIO IRQ** at this stage.

- Caller-supplied storage, capacity **1..256** edges, no dynamic
  allocation and no file writes.
- A real callback must pass the actual observed edge timestamp and
  level; identical consecutive levels are ignored, never fabricated.
- Trigger policies **RISING / FALLING / EITHER**. Starts ARMED,
  stores first matched edge with zero relative duration; subsequent
  edges store raw 32-bit tick and delta from preceding stored edge.
- On full capacity, retains all recorded edges unchanged, sets FULL,
  increments a **saturating** dropped-edge counter for subsequent real
  transitions. Re-arm requires STOP and an owned-IRQ teardown.
- 32-bit wrap is accounted for with unsigned modulo subtraction for
  short intervals. Zero/ambiguous gap over `0x7fffffff` ticks
  fails closed with ERROR. Since an entire counter wrap with no
  observed edge cannot be detected from two samples, a **separate
  app-thread bounded capture timeout is mandatory before hardware
  integration**.
- **Concurrency contract:** single interrupt writer. App-thread
  snapshot and arm/stop must exclude the writer's IRQ/ensure callback
  detach. A GUI mutex is **not** a replacement for EXTI IRQ masking.
- Keep heap- or static-allocated event arrays, **not** a 256-edge
  array on Flipper's small application stack. On conventional ABIs
  `LabMateScopeEdge` is around 12 bytes, so 256 events are about
  3 KiB; confirm exact `sizeof()` and available SRAM/stack in the
  actual Momentum toolchain before selecting the allocation pattern.

## Phase 1B — PC1 fail-closed resource model (2026-10-18)

Added new **pure-C-only**, host-testable model modules (the existing
v1.8/E11 capture, I2C, PWM, menu and UI sources were **NOT edited**):

- `src/labmate_scope_gate.h`, `src/labmate_scope_gate.c`:
  `labmate_scope_gate_pc1()` consults the *current* E11 local capture
  policy's **PC1 EXTI1** rule, other capture owners/active flags,
  application I2C/1-Wire communications ownership, GPIO monitor,
  active Logger/UART/counter/button and sticky release faults.
  Unsupported native `resource_lease` or non-asserting GPIO
  `try_add_int_callback` API yields **UNSUPPORTED**, not an assert-based
  callback fallback. Wrong pin yields **BUSY/INVALID**; system button
  EXTI3/EXTI6 and unreviewed other candidate pins are never offered.
  Independent PA7/TIM1 PWM intentionally remains permissible for a
  future PA7→PC1 loopback *only when other resources are free*.
- The model separates a real, nonzero firmware token, a successfully
  registered callback, configured GPIO and actual RUNNING state.
  Each state transition is allowed only after a hypothetical caller has
  **confirmed** the respective native operation. This model does not
  invoke the native operation itself and does not grant physical ownership.
- `labmate_scope_owner_stop_plan()` lists owned resources that would
  require cleanup; `stop_confirmed()` clears the handle only after
  successful callback detach, pin restoration and native lease release
  are **reported by the future driver**. A missing result latches
  `RELEASE_FAULT`, preserving the recorded handle and denying a
  subsequent capture. An incomplete cleanup must not be retried
  blindly or used to erase a foreign callback; native recovery will
  require separately verified handling.
- `tests/test_labmate_scope_gate.c` covers foreign Frequency/Counter/
  Pulse/Button ownership, I2C/1-Wire, Logger, GPIO Monitor, UART,
  stale active flags, invalid PC0/PC3/PA6/PB3/PA7 pins, missing firmware
  features, illegal lifecycle transitions, STOP/restart, failed
  callback registration cleanup, and sticky release failure.
- CI workflow `.github/workflows/check-v19-scope-buffer-host.yml`
  now includes **actual repository** E11 `labmate_resource_policy.c`
  and `labmate_comm_resource.c` in its C11 and ASAN/UBSAN link tests.

**Evidence classification:** Exact newly committed GitHub file blobs
match local C/header/test working bytes; a local strict C11 + ASAN/UBSAN
unit run **PASSED** with signature-compatible local policy doubles.
The **new live Actions job against the complete real E11 policy modules
has NOT been independently observed finishing**, so no CI PASS is claimed.
No firmware, FAP, S1 profile, historical CSV or application menu was
modified. This source-only gate does **not** constitute a native PC1
IRQ lease, physical BUSY or STOP/BACK on a device.

**Next:** add independent no-signal timeout/timebase validity gates to
bounded capture; then write the actual matched-native firmware acquire /
nonasserting callback and owned IRQ teardown path with explicit
low-level failure simulation. New FAP/hardware work needs a separate
owner-approved install scope and compatibility check.

## Objective acceptance before exposing the scope in menu

1. Existing FAP menu and old screen identifiers stay unchanged until
   a dedicated gated UI change is reviewed. The menu stays
   **MEASURE → OUTPUT → RECORDS → COMM → INFO** with About last.
2. Add new `LabMateCaptureScope` local owner enum **only** with
   tests for PC1 selection, denied mixed captures, release-fault sticky
   conditions, native PC1 firmware IRQ lease and owned callback teardown.
3. START must acquire required **firmware lease** before touching
   GPIO registers; use `try_add_int_callback` before pin config, fail
   closed on refusal and ensure no modification of another client.
   EXTI3 and EXTI6 must not be available.
4. Use a verified timebase and **timeout** independent of edge input,
   then test wrap and long idle. Snapshot under IRQ exclusion, render
   on app thread, never UI/storage work in IRQ.
5. Explicit RUN/ARMED/HOLD/STOP/BUSY/ERR and visible FULL/drop counter
   are required; false real-time signal values are prohibited.
6. Run strict C11 host tests with sanitizers and actual CI conclusion
   before claiming build PASS; afterward run matched Momentum FAP build
   and request separate owner approval before a device write.
7. Add regression checks for old Logger/Profile/Counter/PWM/UART paths,
   preserving user's S1 and historical CSV. Do not redo physical tests
   without shared-source changes/actual need.

**Near-term status:** First unit implemented and locally executed in a
sandbox with strict C11 and Address/Undefined sanitizers, PASS; the
new GitHub CI workflow is authored but its live result must be checked
separately. No E11 existing source files were modified by the buffer
implementation. This file is a capability/collision matrix, not a
declaration that firmware-global native service arbitration is solved.
