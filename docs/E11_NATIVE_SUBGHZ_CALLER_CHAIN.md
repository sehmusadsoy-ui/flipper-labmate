# E11 — Native Sub-GHz RX/TX firmware-wide caller and ownership chain

**Branch:** `dev/v1.8-completion` / Draft PR #13.  
**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** SOURCE AUDIT / OPEN. **NOT a native Sub-GHz patch or safety PASS**.
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
- Exact internal **CC1101 G0 / connector PB3 alias** and the dynamic
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

## Required safe migration (in production firmware)

1. **RX:** implement bool native TRY_START with an atomic TIM2 +
   CC1101 G0 physical pin/IRQ owner, no radio/callback/clock/GPIO
   mutations before successful claim and legacy-disabled preflight.
   Preserve existing exported void symbols for ABI compatibility.
   Route BUSY through interconnect/device/main Sub-GHz RX callers so
   no worker or state is started and no STOP occurs after denial.
2. **TX:** one atomic TIM2+DMA2 CH1 plus CH2 when mirror is enabled,
   with the exact GPIO aliases as part of the claim before radio
   switching or buffer allocation. Preserve regional false vs BUSY
   handling. Denied/malloc-failure starts must perform zero hardware
   changes and leave no orphaned software state.
3. **Interrupts and STOP:** the original TX DMA ISR, TIM2 IRQ,
   completion check and RX ISR must verify current owner. Native STOP
   only tears down its own channels, radio GPIO, callback/IRQ and
   timer, then releases its exact handle. Sticky release failure
   or unexpected bus loss must prevent unsafe restart.
4. **Validation:** real original production C fault injection of
   both HAL and device/main callers, with native RFID FIELD/
   EMULATE/READ/CAPTURE and infrared conflicts, denied zero writes,
   dynamic mirror, legacy clocks, allocator faults, clock loss and
   repeated START/STOP. Then a full pinned matched Momentum+single
   LabMate FAP+native JS+MNTM-012 updater CI and official policy/APPCHK
   verification. Physical RF coexistence remains
   **DEFERRED / HARDWARE PENDING**.

This source audit complements
[`E11_NATIVE_SUBGHZ_RESOURCE_GATE.md`](E11_NATIVE_SUBGHZ_RESOURCE_GATE.md).
**E11 firmware-global is OPEN**, no v1.6 COMPLETE, no Stable/main,
no v1.9 and **NO FLASH**.
