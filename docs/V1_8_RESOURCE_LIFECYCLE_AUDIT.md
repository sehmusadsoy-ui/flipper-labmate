# LabMate v1.8 — Resource Ownership and Exit Audit

**Status:** 2026-10-15 source review + regression guard; **NOT a Stable approval**.
**Development branch:** `dev/v1.8-completion`, Draft PR #13.
**Installed device baseline:** pinned Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322` +
earlier UARTFIX `labmate.fap` SHA-256
`eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf`.

## Update: current deployed EXITFIX / actual Flipper checks (2026-10-15)

The initial owner map below describes **earlier UARTFIX** observations
and a source audit *before* the new EXITFIX was physically deployed.
Its historical FAP baseline remains preserved for traceability.

- Current device installation: patched Momentum source
  `d3f89dfe2ef6b01839201598e9be1590cba80322`, matched
  **EXITFIX** `labmate.fap` SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
  USB COM7 single-FAP transfer and requested launch PASS; the
  firmware was not reflashed.
- On-device operator-reported **EXITFIX E1–E9 PASS**, each only for
  the specifically recorded workflow: Button Analyzer, TIM2 counter,
  PWM/Logger coexistence, PWM active app EXIT + STOP on relaunch,
  I2C empty-bus and PWM BUSY/recovery, 1-Wire no-sensor and PWM
  BUSY/recovery, UART run/baud lifecycle, actual ESP32-S2 115200
  UART RX/TX (R=20699, D=0, E=0), and Profiles/History read-only UI.
  See [the physical acceptance ledger](V1_8_PHYSICAL_ACCEPTANCE_GATE.md).
- **E10.2 profile CRC32 PASS**, original/new S1/S2 contents preserved.
  **E10.4 CSV structure PASS**: 8/8 present files, 42 rows, expected
  header and 9 columns. **Full E10 is OPEN**: current SD list directly
  confirms old logs 0041–0049 absent, but the operator cannot recall
  whether they deleted them. All nine remain in the Oct 14 PC
  backup; neither corrupt data nor intentional deletion has been
  demonstrated. No auto-restore or further mutation.
- Normal physical cleanup and local BUSY results do not supply a
  firmware-global TIM1/TIM2/EXTI/PA4 lease API, prove positive
  I2C/DS18B20 devices, exercise an abnormal stale-capture exit
  path or replace electrical waveform verification. Those remain
  explicit v1.8 release gates.
- No merge, tag/release replacement, or v1.9 feature implementation
  is authorized by these device passes alone.

## Audited owner map

| Resource | Production source / entry | Stop and release | Evidence / unresolved scope |
| --- | --- | --- | --- |
| PC1 IRQ frequency / pulse / button | `labmate_capture_core.c`, `labmate_frequency_capture.c`, `labmate_pulse_capture.c`, `labmate_button_capture.c` | `labmate_capture_stop_all` detaches active IRQ; input exits release configured GPIO | Local exclusivity and UI transitions physically tested without signal; actual calibrated input pulses/button bounce remain open |
| PB3 TIM2 frequency and Event Counter | `labmate_frequency_tim2.c`, `labmate_event_counter.c` | TIM2 counter/channel disabled, bus disabled, PB3 reset to analog | STOP/RESUME/time control physically PASS; no demonstrated **firmware-global** TIM2 leasing or calibrated edge accuracy |
| PA7 TIM1 PWM | `labmate_generator.c`, `labmate_resource_policy.c` | `labmate_generator_stop`; monitor excludes PA7 while PWM is active | Physical RUN/BACK/STOP, app exit cleanup, Logger/UART coexistence PASS; frequency/duty waveform accuracy remains open |
| USART 13/14 | `labmate_uart.c` | serial async RX stop/deinit/control release + expansion restore + stream free | Physical ESP32-S2 UARTFIX ST3 115200: R=20543,D=0,E=0,TX PASS; does not prove every traffic pattern or unrelated firmware service behavior |
| PC0/PC1 external I2C3 | `labmate_i2c_runtime.c`, `labmate_i2c_momentum.c` | stop-request + bounded worker JOIN, local lease release; patched firmware external bus mutex | No-device NONE, STOP/BACK/reopen PASS. Real address ACK, real external mutex contention and fault-injection fixtures unavailable |
| PA4 1-Wire | `labmate_onewire_hw.c` | host stop/free + local lease release; explicit conversion cancel on BACK | No-sensor NONE and PWM BUSY refusal PASS; true DS18B20 CRC/temperature and concurrent firmware-service ownership untested |
| MicroSD logger / history / profiles | `labmate_logger_storage.c`, `labmate_history.c`, `labmate_profile_storage.c` | sync/close handles; history read and confirmed delete; dual CRC profile files | Actual CSV receive + Windows 8-row audit + same-file device/PC MD5 PASS; S3 save/load/delete/reboot PASS, old S1/S2 retained. Power-loss/corrupt-SD restore tests open |

## Specific exit hardening (source change, physical retest pending)

Prior `src/labmate.c` called shared capture teardown at final app shutdown
only when `labmate_screen_uses_gpio(app->screen)` was true. Existing UI
routes normally stop capture before returning to the menu, but if a future
route leaves a capture active while exiting from MENU, this conditional
would skip the final shared release.

Development source now **always** calls `labmate_capture_stop_all(app)`
on exit. It snapshots `capture_pin_index` before that call (STOP clears
the identity), then releases the previously armed pin. It also releases
the selected GPIO for GPIO-using screens, avoiding a duplicate release.
The previous `labmate_event_counter_stop` / `labmate_button_capture_stop`
redundant final calls were removed, since `stop_all` already invokes both.

`scripts/check_v18_coordinator.py` and the legacy
`scripts/check_v16_boundaries.py` now assert the unconditional STOP and
pre-STOP capture pin snapshot, preventing the old screen-dependent
teardown from being silently restored.

**Evidence classification:** reviewed code + CI when green are
SOURCE PASS only. Previous physical passes apply to the **older
installed** UARTFIX FAP until the changed source is rebuilt into a new
exact matched FAP, verified and installed by the operator, followed by
the required focused no-external-peripheral exit regression.
Do **not** reuse the earlier pinned UARTFIX installer/hashes for the
new artifact and do **not** flash a new firmware: the patched Momentum
DFU must remain exact and checksummed if this is a FAP-only update.

## E11 preliminary pinned-firmware contract inspection (2026-10-15)

Read-only source inspection of
`Next-Flip/Momentum-Firmware@d3f89dfe2ef6b01839201598e9be1590cba80322`
against the exact production driver files yields specific risks:

| Driver / pinned firmware interface | What the source actually guarantees | Blocker / required fix |
| --- | --- | --- |
| `labmate_frequency_tim2.c` / `furi_hal_bus_enable(FuriHalBusTIM2)` | The HAL bus enable implementation **asserts** its peripheral clock was disabled (`furi_check`) before enabling; there is a boolean `furi_hal_bus_is_enabled` status query | Checking a momentary status is **not an atomic lease**; the direct TIM2 LL register configuration and shutdown can disrupt other users. Cannot claim firmware-wide exclusivity |
| `labmate_generator.c` / `furi_hal_pwm_start(Tim1PA7)` | Patched Momentum `furi_hal_pwm_start` directly configures PA7 and calls bus-enable for TIM1, also depending on a disabled-clock precondition | LabMate's local `generator_running` cannot exclude independent PWM/TIM1 owners; a concurrent owner can cause assertion or reconfiguration |
| `labmate_button_capture.c` / `furi_hal_gpio_add_int_callback` | Pinned `furi_hal_gpio.c` uses `furi_check(gpio_interrupt[pin_num].callback == NULL)` before callback installation; enable/remove touch the shared EXTI line | This is an **asserting API**, not a recoverable try-acquire; shared line use or an unrelated preinstalled callback is a potential crash/ownership conflict |
| `labmate_monitor_gpio.c` / `furi_hal_gpio_init_simple` | A GPIO setup/reset operation changes pin function | The app-local pin index/owner is not a globally coordinated owner/lease, so it can reconfigure a pin used by a different service |

These are **SOURCE-REVIEW findings**, not observed device failures.
E1–E9 physical PASS establishes only the noncompeting conditions
actually tested. Do **not** attempt deliberate concurrent timer/
interrupt-service conflicts on the user's Flipper just to provoke
an assertion. Before any new firmware/FAP implementation, select
and test an actual exported arbiter or design a separately versioned
firmware-side ownership contract and fail-closed caller; ensure that
claim and release are atomic and that failed claims leave all
HAL registers, GPIO pins, EXTI and existing owners untouched.
`furi_hal_bus_is_enabled` alone is insufficient. No approved safe
patch is claimed at this stage; further design/CI and fresh device
acceptance are required.

## Firmware-wide ownership gap: explicitly not closed

`LabMateCommOwner` and `LabMateCaptureOwner` guard **this app's**
resources, not independent firmware services or other apps. The I2C3
adapter uses an actual **firmware** external-I2C mutex, but direct
TIM2/EXTI/PA4 configuration does **not** establish an equivalent
firmware-wide GPIO/TIM2 ownership API. Disabling a timer or EXTI line
from another active firmware user without such a contract would be
unsafe. A truthful firmware-wide completion requires verified exported
owners/leases and **actual competing service tests**, not additional
application-local booleans.

## Gate F4 OTG/5 V

The pinned Momentum Power settings screen does **not** contain a
`5V on GPIO` / `OTG Power` toggle. The operator therefore could
not run the proposed menu-only test. The inspected LabMate driver code
does not request OTG power, and 1-Wire expressly requires no auto 5 V;
this is a limited source observation, **not a physical voltage
measurement**. F4 remains NOT TESTED. Do not enable 5 V to test this.

## Remaining release blockers

- Real known-safe I2C peripheral ACK (I3, ACK portion of I8), real
  DS18B20 CRC/temperature (W2) and conversion cancellation (W3)
  are **blocked by absent safe fixtures**.
- Real TIM2/capture edge accuracy, PWM frequency/duty, button-bounce
  characteristics and threshold-latch triggering are **not** proved
  by no-wire UI tests. Original historical hardware results are
  separate evidence for different firmware/FAP combinations.
- Firmware-global resource exclusion, recovery from SD failures and a
  rehearsed verified firmware/profile backup restore remain OPEN.
- The updated FAP source must pass native CI and exact patched firmware
  + FAP APPCHK/DFU identity verification, **then** new operator
  physical acceptance before any Stable publication.

No changes to `main`, the original `v1.8` tag or Stable release assets.
