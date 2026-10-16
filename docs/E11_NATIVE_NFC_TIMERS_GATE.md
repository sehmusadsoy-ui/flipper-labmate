# E11.1s — Native NFC TIM1/TIM17 ownership (development only)

**Branch:** `dev/v1.8-completion` / Draft PR #13.  
**Pinned firmware:** Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Firmware-global E11:** PARTIAL, **NOT CLOSED**.  
**Device, physical radio/NFC, Stable, firmware flash:** UNTOUCHED.

## Firmware-native source changes

`scripts/patch_momentum_native_nfc_timers_lease.py` applies only to
the exact pinned Momentum source with an explicitly approved
prior-patch file inventory. It migrates:

- `targets/f7/furi_hal/furi_hal_nfc_timer.c`
- `targets/f7/furi_hal/furi_hal_nfc.c`
- `targets/f7/furi_hal/furi_hal_nfc_i.h`
- the shared resource mask allocator in `furi_hal_resources.h/.c`.

NFC frame-wait timeout uses **TIM1** and block transmit uses **TIM17**.
The patch admits one canonical atomic `TIM1|TIM17` lease mask
(`FuriHalLeaseTim17 = (1U << 24)`). This excludes cooperating LabMate
PWM / native iButton TIM1 claims even when TIM17 has no known conflict.

**START:** NFC low-power resume is already an error-returning
`FuriHalNfcError` API. It now requests both timer resources **before**
configuring NFC GPIO IRQ, TIM1/TIM17, NVIC or starting the oscillator.
It returns `FuriHalNfcErrorBusy` if the claim fails, either clock is
already enabled by a legacy service, or an earlier unresolved owner
fault persists. Temporary lease release failure retains a sticky
opaque owner handle; no peripheral configuration follows.

**ACTIVE:** FWT and block-TX timer START/STOP, counter status and
IRQ callback checks depend on a valid owner and both timer clocks.
Unexpected clock loss retains the reservation and prevents foreign
timer/IRQ writes.

**STOP:** both timers' owned interrupts and clock domains are
deinitialized before releasing the exact lease. Failed release is
sticky; it does not permit reuse or a second cleanup. Oscillator
startup error after acquiring ownership rolls back the NFC GPIO
callback and both timer claims.

**Opt-in NFC timer debug mode:** existing NFC debug code writes
external PA7/PA6 without claiming either pin. The patched firmware
deliberately rejects `FURI_HAL_NFC_TIMER_DEBUG` at compile time
rather than letting a debug build overwrite another owner.

## Actual test evidence

[Fast pinned-source actual-C native NFC + firmware allocator CI
#38890147922](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38890147922)
**SUCCESS** on source `2d8c72b0e6b3cf02e26091112d614c53950e3266`.
The test `tests/test_v18_native_nfc_tim1_lease.py` compiles the
genuine patched native NFC timer C and actual resource allocator C
with fault-injectable host HAL stubs. Checks include:

- denied owner claim and already-enabled foreign TIM1 or TIM17,
  no GPIO/timer/IRQ mutations;
- successful dual-timer activation, ISR callback, frame wait and
  block transmit START/STOP, IRQ teardown and release;
- preflight failed-release, STOP failed-release and unexpected
  timer-clock loss, each preserving sticky nonreusable ownership;
- genuine extracted `furi_hal_nfc_low_power_mode_stop()` production
  C: BUSY before GPIO IRQ, oscillator-failure rollback, successful
  restart and repeated-start denial;
- actual allocator TIM1 collision with PWM and iButton,
  wrong-mask release denial and separate TIM2 coexistence.

**Matched firmware/FAP/updater**:
[CI #38890148015](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38890148015).
Check the **completed** workflow before claiming build PASS or
recording hashes. This is a CI-only uninstalled firmware bundle;
**DO NOT FLASH**.

## Open native safety boundaries

Native Sub-GHz, RFID, infrared and unrelated direct LL timer clients
still bypass the E11 ownership table. Atomicity holds **only across
cooperating clients**; a preflight bus-is-enabled check is not a
global race-free interposition layer. NFC's own GPIO interrupt
registration uses the existing NFC/radio IRQ path and is **not**
yet coordinated against every other firmware EXTI client.
NFC debug mode needs a separately designed atomic PA7/PA6 claim if
ever supported. Existing NFC oscillator/radio recovery has NOT been
physically verified with Flipper's NFC hardware.

Firmware-global v1.6 refactoring is **not complete** while those
native bypasses and STOP/BACK/ISR race paths remain unreviewed.
Equipment-dependent physical acceptance is **DEFERRED / HARDWARE
PENDING**, and no CI PASS authorizes firmware installation without
a separately approved full update and recovery protocol.
