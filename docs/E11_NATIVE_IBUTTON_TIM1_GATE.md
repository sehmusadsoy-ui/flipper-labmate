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

**Extended native Misc protocol integration (2026-10-16):**
`scripts/patch_momentum_native_ibutton_protocol_lease.py` now adds
boolean `furi_hal_ibutton_emulate_try_start_with_pin` and
`furi_hal_ibutton_emulate_try_stop` interfaces. The native
`lib/ibutton/protocols/misc/protocol_group_misc.c` obtains TIM1 before
setting the internal iButton output pin and resets that pin only after
a safely completed STOP. A BUSY start leaves all timer/IRQ/GPIO
registers untouched; failed release retains a sticky owner token and
blocks restart. Legacy HAL `void` start/stop wrappers remain
ABI-compatible but, individually, **cannot** report denial to their
other callers. Native protocol ISR and dictionary mutations remain
guarded by the patched driver and protocol START/STOP lifecycle.

**Remaining scope boundary:** only the native iButton Misc group,
TIM1 and its own internal output pin are coordinated in this change.
Native RFID/SubGHz/infrared/NFC drivers and independent direct
register users are NOT protected. A source/host PASS cannot establish
native/native concurrency or device safety.

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

## Verified CI evidence (2026-10-16, CI ONLY)

- Final host-only, exact patched native iButton C and actual firmware
  allocator with denied START, legacy already-active TIM1, ISR,
  retune, STOP, failed lease release and clock loss:
  [run #38835788840](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38835788840)
  **SUCCESS** at source `4d7f2600717c1ab382fefc118d699d27bcbecf74`.
- Exact production firmware code and single integrated LabMate FAP,
  JS module, complete updater, APPCHK, and the official MNTM-012
  radio/option-byte source/archive comparison:
  [run #38835126596](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38835126596)
  **SUCCESS** at source `ae7b3de3d470aa13a61fcc6e86b07c7f41e19349`.
- **CI-only** `firmware.dfu` SHA256:
  `1b29e91ea03d1d6c42bd9250d4d54784e4ad8177a56f63b4db7d4089641299b3`
- Matching **CI-only** `labmate.fap` SHA256:
  `94d023db7ce50a712d6fcf77d8e19d9fcb2554aca80c2a30170fdc0cf297aff9`
- Review-only complete firmware/FAP/JS package artifact ID:
  `12019730086`, **DO NOT FLASH**.

A full SDK/firmware compile and mocked runtime test are not evidence
that all independent native services comply with E11, or that Flipper
hardware tested/approved the new firmware. **Global E11 remains OPEN.**

## Protocol-level CI evidence (2026-10-16)

- [iButton protocol START/STOP and lease fault test CI #38887921754](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38887921754): **SUCCESS**, exercising actual patched native iButton C and the real Misc START/STOP C with host HAL instrumentation (denied BUSY without GPIO changes, legacy occupied TIM1, successful START/STOP, repeated START, sticky release failure and unexpected timer clock loss).
- [Complete matching Momentum updater, FAP and JS plugin CI #38888012694](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38888012694): **SUCCESS** at tested source `4b3c6c21bba9fb96258ff094f101e356ba476cd9`. Actual native protocol C 2/2 host cases, full Momentum firmware compilation, APPCHK for LabMate FAP + JS plugin, radio/option-byte and full-updater comparison to official MNTM-012 all PASS. **CI-only** firmware DFU SHA256 `2cfd0d7691bbb6144dd1eb6b726163ae018dab54cef4451dea4e84afeb588f1d`; matching LabMate FAP SHA256 `94d023db7ce50a712d6fcf77d8e19d9fcb2554aca80c2a30170fdc0cf297aff9`. Review-only matched full package artifact ID `12040404107`, **DO NOT FLASH**. No physical tests, USB/SD writes or firmware flash.
