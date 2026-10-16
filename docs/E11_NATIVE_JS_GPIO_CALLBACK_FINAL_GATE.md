# E11 — Native JS GPIO callback STOP and module teardown safety

**Development-only:** `dev/v1.8-completion` Draft PR #13, pinned
Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`.
No main/Stable merge, radio firmware update, FAP installation,
USB, microSD or Flipper hardware operation.

## Actual source change

`scripts/patch_momentum_native_js_gpio_callback_cleanup.py` is a
strict pinned SHA + exact stage diff patch to the **real**
`applications/system/js_app/modules/js_gpio.c`. The prior E11
stage had already converted callback ADD to native
`furi_hal_gpio_try_add_int_callback`, but mode transition and
`js_gpio_destroy` still used unconditional native
`furi_hal_gpio_disable_int_callback` and
`furi_hal_gpio_remove_int_callback`.

Those legacy removal calls could disable an EXTI line or clear a
callback registered by another service, particularly a conflicting
port's shared EXTI0/2/4/7 line.

The new `js_gpio_e11_try_remove_callback`:

- Calls the actual E11 GPIO HAL **compare-and-remove** primitive
  with the exact expected `js_gpio_int_cb` function pointer and
  original `interrupt_semaphore` context.
- Operates only when a JS pin instance originally installed a
  callback. A duplicate STOP is a no-op, never an unconditional
  shared EXTI disable.
- Sets sticky `lease_fault` if the expected callback/context
  is missing or replaced; it cannot overwrite, disable or reset the
  foreign owner.
- On mode transition, refuses GPIO reconfiguration when the
  callback cannot be safely removed.
- On module teardown, refuses PWM/pin mode changes, E11 lease
  release, semaphore freeing and pin-manager freeing for a failed
  owner removal. It deliberately retains these resources rather
  than risk callback use-after-free; exceptional hardware recovery
  after such a fault remains operator-controlled, not automatic.
- Keeps native JS module API, interrupt subscription contracts and
  normal mode/STOP behavior unchanged. A `FURI_LOG_E` identifies
  the exceptional sticky teardown condition.

## Exact C and firmware safety gates

[Original extracted JS callback helper C host test
#38935496608 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38935496608).
Tests include no registered callback, correct callback/context,
foreign callback, correct callback with wrong context, double
STOP and sticky owner. Source-contract checks verify that neither
mode changes nor teardown contain legacy raw callback disable or
remove, and that teardown exits before GPIO or semaphore free
when the owner check fails.

[Whole pinned firmware callback inventory
#38935946504 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38935946504)
scans native tracked C/C++ callers after all E11 stages, refusing
any new raw native GPIO add/remove callsite except **the HAL
primitive definition itself and the original reserved system-input
service**. The original Momentum button callbacks are intentionally
preserved, so STOP/BACK buttons are never covered by a global silent
interception mechanism.

The corresponding full pinned Momentum native + one LabMate FAP +
JS GPIO module + single MNTM-012 no-flash updater and archive gate
is [#38936030380](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38936030380).
Its **final conclusion must be independently verified** before
declaring full-build acceptance. Prior no-flash updater runs are
not proof for this newly added JS teardown/IRQ-inventory stage.

## What this does NOT establish

This cooperative model does not intercept arbitrary writes directly
to STM32 GPIO/LL EXTI/DMA/clock registers, non-default optional
debug GPIOs or unknown future apps. It cannot guarantee flawless
recovery after another uncooperative service overwrites the callback
slot; a sticky fault intentionally leaves a resource reservation
and allocated context instead of risking physical hijack/UAF.
Native JS runtime/event loop lifetime concurrency and shared
firmware system-input button UX need actual physical fixtures.

Unresolved external SubGHz plugin v1 interface:
`SubGhzStartAsyncRx` is a **void function pointer** in pinned
`lib/subghz/devices/types.h`, and
`subghz_devices_start_async_rx` in the compiled firmware is also
`void`. Although internal and external native drivers have
truthful bool try-start routines, the older plugin ABI cannot
convey denial through the existing device interconnect and upper
worker without a separately designed **version-negotiated**
interface. Blindly turning that slot into bool would make
existing third-party radio plugin pointers binary-incompatible.
We do not silently change this ABI or report BUSY as START success.

**Result:** JS callback host + inventory gates PASS, full-build
gate separately pending at the time of this document, physical
coexistence and versioned third-party plugin BUSY remain OPEN;
firmware-global E11 is **PARTIAL**. Hardware tests deferred.
