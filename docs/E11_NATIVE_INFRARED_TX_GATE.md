# E11.1u — Native infrared TX ownership and worker BUSY lifecycle

**Branch:** `dev/v1.8-completion`, Draft PR #13.  
**Pinned firmware:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Firmware-global E11:** **OPEN/PARTIAL**, no Stable release or device changes.

## Scope implemented in source

`scripts/patch_momentum_native_infrared_tx_lease.py` patches the
pinned native Momentum `furi_hal_infrared.c`,
`infrared_worker.c`, public HAL infrared declarations,
`targets/f7/api_symbols.csv`, and the real firmware resource
allocator. It runs only after the pinned and tested RX TIM2 migration.

The TX state machine has a composite, all-or-nothing claim for
**TIM1 + DMA2 channel 1 + DMA2 channel 2**; when using external IR
output, **PA7 is included in that same atomic mask**. This
interlocks with LabMate/native PWM, NFC TIM1, iButton TIM1, and other
cooperating PA7 clients. DMA2 channel claims do not alias the
distinct DMA1 claims used by DigitalSequence.

The new bool `furi_hal_infrared_async_tx_try_start()` acquires its
lease and rejects pre-enabled legacy TIM1/DMA2 **before allocating
any buffers or configuring timer, DMA, interrupts or GPIO**.
`malloc` and semaphore failures free CPU resources and release
the exact claim without peripheral writes. A second preflight
after buffer preparation prevents starting on an already-active
legacy timer/DMA. Failed temporary release is sticky.

The public original `void` TX start API remains ABI-compatible.
The native TX worker uses the new bool API. A denied START
terminates its worker transmission loop rather than entering
`StopTx` or `WaitTxEnd` where an unallocated stop semaphore would
previously be awaited. Native DMA ISRs refuse to touch hardware
without an active owner and a valid TIM1 clock.

Successful TX completion/STOP frees buffers and semaphore,
deconfigures owned DMA IRQ and output GPIO, disables owned TIM1
and **only then** releases the original claim. Failed release
preserves an opaque sticky handle and prohibits new starts. A
failed TIM1 clock check does not disable potentially foreign
DMA/IRQ/GPIO and a bounded-period semaphore wait detects unexpected
clock loss rather than hanging indefinitely on a missing event.

Native output selection cannot change while TX owns its lease.

## Validation

[**Real original patched native infrared TX C + exact firmware lease
allocator host CI #38897339075](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38897339075)
**SUCCESS**. Original production code is compiled with strict
C warnings and host HAL instrumentation. Source test includes
denied claim zero peripheral writes and zero allocations,
legacy occupied TIM1 and DMA, failed preflight handle release,
allocation failure at each of four DMA buffers with exact cleanup,
success with internal output and external PA7 composite claim,
normal semaphore STOP, failed final lease release, unexpected clock
loss and bounded WAIT, and actual firmware C interlock with PWM,
iButton, NFC and GPIO Monitor PA7. Actual worker source is
checked for ordering and BUSY non-wait control flow.

[**Complete paired full Momentum firmware/FAP/JS/updater CI
#38897419654**](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38897419654)
was started against source `c4585c8948ee25514b68d6f88bf1c7abc9ac9865`.
**Do not claim a full firmware/FAP PASS before its final SUCCESS**.
Never flash a CI-only test package.

## Not yet established / remaining risks

- This native worker test verifies the real START, STOP/WAIT and
  allocator C, but **does not emulate an entire physical DMA
  interruption sequence on a Flipper**. Firmware build alone cannot
  establish no race against other native direct-register clients.
- `furi_hal_infrared_detect_tx_output()` may independently
  reconfigure PA7 while probing an external IR accessory; its
  transient pin-scanning path needs a separate lease or refusal.
- `infrared_worker_rx_start()` uses a legacy void native RX START;
  denied START is hardware-safe but cannot report BUSY to a
  worker that may start its RX thread without capturing data.
- Direct native RFID, Sub-GHz, other EXTI users and low-level bus
  paths have not all been migrated to the firmware-wide contract.
- A hardware loss during TX deliberately retains a sticky fault,
  potentially leaking a session's CPU buffers rather than
  destructively tearing down another owner's registers. This is
  safe-failure containment, **not** successful recovery.
- Equipment-dependent coexistence and STOP/BACK tests remain
  **DEFERRED / HARDWARE PENDING** until materials are available.
  They never count as a physical PASS.

Do not merge `main`, update published v1.8 Stable, install
experimental firmware, or start v1.9 based on host CI.
