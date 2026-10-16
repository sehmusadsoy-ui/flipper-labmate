# E11.1r — Native iButton TIM1 owner gate (development, not a release)

**Branch:** `dev/v1.8-completion`, Draft PR #13.  
**Momentum base:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Installed firmware and published v1.8 Stable:** unchanged.  
**Physical tests:** hardware pending by prior operator decision; NOT PASS.  
**Firmware-global E11:** **PARTIAL — NOT CLOSED**.

## Integrated driver changes

`scripts/patch_momentum_native_ibutton_tim1_lease.py` modifies
the exact pinned `targets/f7/furi_hal/furi_hal_ibutton.c` in
an ephemeral CI checkout. It introduces a canonical **TIM1-only**
firmware mask to arbitrate with LabMate PWM's `TIM1|PA7` mask
without incorrectly claiming that iButton configures PA7.

- Acquire TIM1 before setting the native Running state, callback, IRQ,
  bus clock or timer registers; return without side effects if BUSY.
- After claim, deny if a legacy user has TIM1 bus enabled; failed
  temporary lease release becomes a sticky fault with retained handle.
- ISR callback and set-next-period require valid active owner.
- STOP refuses to touch an unexpectedly disabled foreign timer,
  and only removes the native ISR, disables its own timer, and
  releases its exact handle after successful owned teardown.
- Release failures preserve the nonzero opaque handle and prevent
  all subsequent START, STOP or retune operations for the session.
- These guarantees are limited to **cooperating** owner clients,
  not every source that writes TIM1 registers directly.

**Critical scope boundary:** original iButton HAL `void` start
cannot return BUSY to its existing protocol-group caller, and the
protocol group configures its separate iButton output pin before
calling this timer start. The pin functions and upper-level emulation
state machine have NOT been migrated to the same atomic owner
lifecycle. This is a remaining cross-service risk; do not call
iButton end-to-end safe under contention based only on the lease patch.

## Tests / release boundary

`tests/test_v18_native_ibutton_tim1_lease.py` compiles and
executes the exact patched production C source under instrumented
HAL stubs plus the actual patched firmware-resource C allocator.
Covered scenarios include rejected acquisition without hardware
writes, pre-enabled foreign TIM1, native START, ISR, retune and STOP,
unexpected clock loss and failed owner-release blocking reuse.

The full matched firmware/FAP + JS module + updater workflow is
`.github/workflows/check-v18-full-012-upgrade-package.yml`.
Only completed source-specific CI runs with SUCCESS and exact
checksums are compilation evidence; failures and pending runs
MUST NOT be called PASS. No CI candidate is installable without
separate firmware-flash/rollback approval.

## Still open

Independent native RFID, Sub-GHz, infrared, NFC TIM1, and other
TIM/EXTI/GPIO/DMA consumers bypass some or all E11 leases.
Their void-return starts, interrupts, dynamic pin lifecycles and
existing cleanup must be reviewed and migrated at actual
acquisition boundaries. Merely checking peripheral clocks before
writes does not make the race atomic against noncooperating code.
A global resource-interposition or proven coordinated caller
migration, real-C fault-injection and device acceptance are
required to mark firmware-wide v1.6 resource management **COMPLETE**.
