# E11.1w — Native infrared RX worker BUSY and thread rollback

**Development:** `dev/v1.8-completion`, Draft PR #13.  
**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Main/Stable/device:** not changed. **Physical:** DEFERRED/HARDWARE PENDING.  
**Global E11:** remains PARTIAL/OPEN.

## Implemented source contract

`scripts/patch_momentum_native_infrared_rx_worker_lease.py`
applies only to the exact approved, prior-patched Momentum file inventory
after the source stages for infrared RX TIM2 and TX TIM1/DMA2/PA7.

Original native HAL `void furi_hal_infrared_async_rx_start()` is retained
as a wrapper over new `bool furi_hal_infrared_async_rx_try_start()`.
The new entrypoint returns `false` on TIM2/lease BUSY **before** GPIO,
TIM2, ISR, clock or native RX state mutations. Successful ownership
returns `true` after timer/capture initialization. The native worker's
original `void infrared_worker_rx_start()` remains a wrapper
over `bool infrared_worker_rx_try_start()`. Both new symbols
are declared and added to the paired firmware API symbol manifest.

The worker must start its thread before native RX START because the
RX capture ISR may post thread flags as soon as TIM2 enables. On
`false` from the HAL, the worker clears its two callback pointers,
signals `INFRARED_WORKER_EXIT`, joins the already-created thread,
resets the stream and leaves state `InfraredWorkerStateIdle`.
It **does not invoke HAL STOP or disable a foreign TIM2** after denied
start. On successful native acquisition it enables RX timeout and
marks the worker running; existing worker STOP applies to a true
RX owner.

## Evidence and boundaries

[Fast exact pinned native host CI #38901479365](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38901479365)
**SUCCESS**. `tests/test_v18_native_infrared_rx_worker_lease.py`
extracts and compiles the actual patched worker C START and STOP under
strict instrumented C11 HAL mocks; it exercises failed first START,
failed legacy wrapper START, callback and thread unwind, successful
START, and owned STOP. The same workflow also runs earlier actual
infrared RX TIM2 and TX TIM1/DMA2 C/allocator regression suites.

[Complete firmware/FAP/JS/updater CI #38901590432](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38901590432)
runs the exact new source and host tests within a whole matched
MNTM-012 candidate. **Only a completed SUCCESS result establishes
the firmware package gate**; CI is not physical compatibility.

**Still open:** The original public void RX worker start cannot
report BUSY to existing application callers unless they switch to
the new bool API. Native RFID/Sub-GHz direct TIM1/TIM2/IRQ/DMA clients
and other shared GPIO/EXTI owners are not yet migrated. Even a full
firmware build does not prove hardware timer/ISR interleaving.
No software patch here installs a silent global bus veto; firmware-wide
resource ownership is not complete until the remaining native
lifecycles are coordinated and independently verified.

All firmware bundles are review-only **DO NOT FLASH**.
