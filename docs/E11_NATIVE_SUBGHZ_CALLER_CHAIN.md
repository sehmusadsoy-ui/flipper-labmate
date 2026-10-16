# E11 — Native Sub-GHz RX/TX firmware-wide caller and ownership chain

**Branch:** `dev/v1.8-completion` / Draft PR #13.  
**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** Former source audit, now PARTIALLY IMPLEMENTED. RX/TX HAL and built-in RX worker have original-C host gates PASS. Full matching firmware and physical RF are separate gates.
No custom firmware flash, device test, SD changes or release.

## Why Sub-GHz is the next critical blocker

- The genuine `targets/f7/furi_hal/furi_hal_subghz.c` asynchronous
  **RX** uses TIM2, IRQ, and CC1101 G0 GPIO. Its `void`
  `furi_hal_subghz_start_async_rx` changes software state/callbacks
  before configuring the timer. Its STOP disables TIM2, interrupts
  and the shared pin without an owner token. A rejected lease cannot
  safely be represented by a silent return followed by legacy STOP.
- Asynchronous **TX** already returns a bool for regional permission,
  but also uses TIM2, **DMA2 CH1**, and optional **DMA2 CH2** for the
  debug mirror. It allocates its buffer and updates state/GPIO before
  several hardware mutations. There is a genuine **DMA2 conflict
  with infrared TX TIM1+DMA2** and native RFID DMA/field despite
  different timer numbers.
- Exact internal **CC1101 G0 = PA1 (not connector PB3)** and the dynamic
  `async_mirror_pin` must be inspected against pinned board mapping.
  A full pin+timer+DMA claim must precede pin changes. Unsupported
  arbitrary mirror pins should return an explicit status, not silently
  touch an unclaimed GPIO.

## Pinned production callers (not just the native HAL)

1. `lib/subghz/devices/cc1101_int/cc1101_int_interconnect.c`:
   `subghz_device_cc1101_int_interconnect_start_async_rx` has a
   **void** signature and passes its request directly to the HAL;
   the same interconnect has an existing **bool** TX wrapper.
2. `lib/subghz/devices/devices.h` + `devices.c`: the public
   `subghz_devices_start_async_rx(...)` and underlying device
   interconnect RX function pointer are still **void**. Changing
   only the HAL to bool does not give callers a BUSY signal.
3. `applications/main/subghz/helpers/subghz_txrx.c`: the RX entry
   calls `subghz_devices_start_async_rx`, then starts its worker
   and sets `SubGhzTxRxStateRx` regardless of whether the native
   timer could actually be acquired. The RX end later stops a
   worker and invokes `subghz_devices_stop_async_rx`, potentially
   when there was never an owned RX timer.
4. `applications/main/subghz/subghz_cli.c` and
   `applications/debug/subghz_test/views/subghz_test_packet.c`
   call native RX APIs as additional consumers. Native TX also
   has direct call sites in debug test views and unit tests.
   A change to the device interconnect ABI must account for these
   call sites and independent external radio implementations.

## 2026-10-16 implemented and still-open caller chain

The original description above records the unsafe *before* state at
pinned Momentum. It must not be mistaken for today's patched source.

- Native RX now uses `furi_hal_subghz_async_rx_try_start`, an atomic
  TIM2 claim and a guarded ISR/STOP. Debug mirror PA7 or external PB3
  adds the corresponding physical pin; other mirror pins explicitly
  fail closed. Genuine HAL production C + firmware allocator host
  [#38911157761 PASS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38911157761).
- The built-in CC1101 interconnect, `subghz_devices_try_start_async_rx`
  and `subghz_txrx_rx` now propagate BUSY so the normal worker and
  speaker do not start falsely. The existing third-party radio
  interconnect `void` function pointer has **not** changed.
  Genuine production caller C host
  [#38911453319 PASS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38911453319).
  External radio plugins still cannot return BUSY through their
  legacy void ABI and need separate design coordination.
- Native TX now owns TIM2+DMA2 CH1; with the validated PA7/PB3
  external mirror it additionally owns DMA2 CH2 and the actual pin.
  Denied START, completion, native DMA ISR, malloc failure and STOP are
  guarded by the exact opaque lease.
  Genuine native production-C and allocator host
  [#38912471437 PASS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38912471437).
  Optional `FURI_HAL_SUBGHZ_TX_GPIO` build configurations are rejected
  until their GPIO also has a reviewable lease contract.

For detailed source links, limits and mandatory full-package CI see
[`E11_NATIVE_SUBGHZ_RX_TX_GATE.md`](E11_NATIVE_SUBGHZ_RX_TX_GATE.md).

**Still OPEN:** dynamic mirrors beyond PA7/PB3, external-plugin BUSY
reporting, native CLI/debug routes, hopper retry/failure semantics,
additional internal GPIO/EXTI users, RF concurrent recovery,
actual RF/SD/Flipper tests, and final exact firmware/FAP/updater
build verification. The firmware-wide v1.6/E11 contract is NOT closed.

**Development boundary:** No device flash, no Stable/main merge,
no SD/USB touch, no v1.9; hardware checks remain
**DEFERRED / HARDWARE PENDING**.
