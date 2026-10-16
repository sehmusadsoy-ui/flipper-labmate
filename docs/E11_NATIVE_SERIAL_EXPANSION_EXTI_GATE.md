# E11 — Native serial expansion USART1 PB7 / LPUART1 PC0 EXTI ownership

**Scope:** `dev/v1.8-completion`, Draft PR #13; exact upstream
Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** original production-C serial control and firmware allocator
**HOST PASS**, latest matching full firmware + single LabMate FAP + JS
GPIO + MNTM-012 updater **separately pending**. No device/USB/SD use.

## Why two distinct UART RX paths matter

Pinned `targets/f7/furi_hal/furi_hal_serial.c` maps:

| Native serial ID | Peripheral and RX GPIO | Exact E11 expansion claim |
|---|---|---|
| `FuriHalSerialIdUsart` | USART1 RX **PB7**, shared **EXTI7** | `USART1|PB7|EXTI7` |
| `FuriHalSerialIdLpuart` | LPUART1 RX **PC0**, shared **EXTI0** | `LPUART1|PC0|EXTI0` |

The latter intersects LabMate GPIO Monitor PC0, I²C3 PC0/PC1 and
JS/Pulse EXTI0 aliases. USART1 also intersects LabMate native USART1
serial usage and other EXTI7 GPIO ports. Both paths must fail closed;
a PB7-only lease is not a correct general serial-control fix.

## Reviewed original native-source migration

[`patch_momentum_native_serial_expansion_exti_lease.py`](../scripts/patch_momentum_native_serial_expansion_exti_lease.py)
applies a SHA and exact-current-diff guarded change to pinned
`furi_hal_serial_control.c/.h`, `furi_hal_resources.c/.h` and
`api_symbols.csv`.

- The serial control queue's existing expansion handler now reports a
  **truthful bool** separately from the handler's thread-continuation
  return. This is essential: returning false to signify BUSY would
  **terminate the system serial-control thread**.
- New `furi_hal_serial_control_try_set_expansion_callback` posts to
  the same serialized native service queue, retrieves the bool result,
  and retains the original public `void` ABI as a logging wrapper.
- An expansion START selects the exact pin/peripheral/EXTI composite
  mask; fails on incorrect pin, existing lease, callback contention,
  in-use serial handle or logging ownership. No UART RX-direction or
  GPIO mode writes occur on a denied claim.
- It first obtains the firmware resource lease and performs the prior
  E11.1c atomic callback **TRY-ADD**, only then disables UART RX direction
  and configures the selected PB7 or PC0 pin to interrupt input.
  Hardware only reports active once this succeeded, and the service
  publishes its callback/handle afterward.
- STOP removes only the exact callback with matching context via
  E11 compare-and-remove. On a mismatch it returns BUSY, leaves the
  other callback in place, keeps an E11 sticky fault and **does not**
  re-enable serial RX or release someone else's resource.
- On successful STOP it restores RX direction and releases exactly the
  held mask. Failed releases are sticky; no duplicate STOP reconfigures
  a foreign UART.
- Existing logging, serial acquire and serial release transitions
  now refuse destructive handoffs if the expansion owner cannot
  safely disengage. Re-enabling expansion after release/logging
  changes can be BUSY and is logged; these APIs' original void/handle
  ABI is retained. The device-side expansion UI/retry behavior remains
  a separate OPEN workflow.

**Normal operation is not prohibited globally.** The table is
cooperative and native serial-internal control remains the arbiter of
serial handle availability. Peripheral leases guard conflicting
LabMate and other registered clients only.

## Host and complete build gates

Actual native service callback/registration and queue handler bodies
were compiled and **executed** with the genuine firmware allocator,
not rewritten mocks for the functions under test.
[CI #38917845230 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38917845230).
The negative/positive cases cover:

- both USART1/PB7/EXTI7 and LPUART1/PC0/EXTI0;
- denied resource, occupied existing native callback, in-use UART;
- no RX-direction or GPIO writes on denial, no false application
  registration and no control-thread shutdown;
- normal registration, callback event dispatch, exact STOP, duplicate
  START/STOP, callback replacement and failed release sticky;
- allocator mask collisions with LabMate USART1, PC0 Monitor,
  I²C3, PC0/EXTI0 and JS EXTI7.

The newest complete matching Momentum firmware, **one** LabMate FAP,
native JS GPIO module and MNTM-012 updater source-policy/SDK package
gate is [#38917937898](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38917937898).
Its exact final conclusion is **required independently** before this
stage counts as a fully compiled firmware+FAP package.

## Open boundaries

The older `void furi_hal_serial_control_set_expansion_callback`
API cannot return BUSY; clients needing reliable status must opt
into its new bool companion. UI notification/retry across an external
expansion module and state recovery after an interrupted owner remain
OPEN. Existing uncontrolled direct UART registers, native timer/IRQ
clients and the interaction with physical peripherals need fixture
validation (HW-13).

Other firmware-global E11 blockers: external CC1101 plugin TIM17 and
configurable G0 EXTI callback replacement, SignalReader/DMAMUX/EXTI,
legacy native direct GPIO and system service ownership. All physical
acceptance remains **DEFERRED / HARDWARE PENDING**.

**No main/Stable merge, firmware flash, SD/USB mutation or v1.9
transition. E11 is PARTIAL, not firmware-global COMPLETE.**
