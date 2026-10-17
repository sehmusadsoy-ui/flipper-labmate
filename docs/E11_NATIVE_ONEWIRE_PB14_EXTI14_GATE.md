# E11 — Native 1-Wire slave PB14 + EXTI14 callback ownership

**Development scope:** pinned Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`, LabMate
`dev/v1.8-completion` / Draft PR #13.
**Status:** Original-C GPIO callback/OneWire START/STOP plus genuine
allocator **HOST PASS**; latest full firmware/FAP/updater build is a
**separate CI gate**. NOT an on-device iButton emulation or universal
firmware EXTI PASS.

## Native HAL change

`scripts/patch_momentum_native_onewire_slave_exti_lease.py` updates
the pinned original sources rather than building a separate FAP:

- Adds **PB14 + EXTI14** as one exact atomic firmware resource mask.
  The pinned internal iButton GPIO is `gpio_ibutton` = PB14.
  This stage explicitly **refuses arbitrary pin choices** (future
  expansion needs a separate verified per-pin/EXTI lease).
- Reuses the existing E11.1c `furi_hal_gpio_try_add_int_callback` and
  adds a complementary `furi_hal_gpio_try_remove_int_callback`. Both check the
  existing callback slot under the GPIO critical section. If another
  callback is registered, a native OneWire START **cannot overwrite it
  or crash via the legacy furi_check assertion**; denied callback
  acquisition does not write GPIO/EXTI registers.
- Adds `onewire_slave_try_start(bus)` returning a truthful boolean.
  Existing `void onewire_slave_start` ABI remains callable and uses
  the same safe START underneath.
- The actual `OneWireSlave` object owns its opaque claim. Missing
  callback/lease, double START/STOP and BUSY stop are handled
  without GPIO reset or foreign callback removal. It removes exactly
  its own callback/ctx **before** GPIO mode reset.
- Unexpected callback replacement or failed lease release leaves a
  sticky failure state. `onewire_slave_free` refuses to free an
  object that still holds a claim, avoiding an EXTI use-after-free at
  the cost of a deliberate fail-closed memory leak in exceptional
  recovery scenarios.
- Dallas protocol group consumes bool START and logs BUSY while
  preserving the upstream iButton group callback ABI. **It cannot yet
  report BUSY through the old `void emulate_start` protocol contract
  to every iButton UI.** That upper-layer status gap remains OPEN.

## Actual source-C fault evidence

[Original C and allocator host CI #38915115152 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38915115152)
executes extracted native `onewire_slave_alloc/free/try_start/start/stop`
and actual firmware `furi_hal_gpio_try_add/try_remove` bodies,
not rewritten substitutes. Cases cover:

- Denied resource claim, denied stale occupied native callback and
  unmatched callback replacement with **no foreign register writes**.
- Unsupported GPIO fail closed; supported PB14 normal START/STOP,
  repeated START and duplicate STOP.
- Failed release retains sticky owner (prevents unsafe restart or
  use-after-free); original firmware allocator refuses duplicate or
  wrong-mask claim release and preserves separate EXTI2 alias.

The first combined full build [#38915167375](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38915167375) caught duplicate E11.1c TRY-ADD declarations and correctly FAILED. The patch was corrected to reuse the existing tested TRY-ADD; the follow-up [#38915550293](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38915550293) was verified **SUCCESS**, including full firmware, one integrated LabMate FAP, native JS GPIO and MNTM-012 updater/policy. This is a software build gate only, not hardware acceptance.

## Still OPEN

NFC IRQ PA2/EXTI2, Serial PB7/EXTI7, external CC1101 TIM17/EXTI,
SignalReader EXTI+DMAMUX, any uncoordinated native GPIO registrations
and callback ordering, non-PB14 OneWire GPIO clients, iButton upper
UI BUSY propagation, exceptional recovery strategy, and all actual
hardware coexistence tests. A noncooperating firmware service may
still register an EXTI callback outside this cooperative lease table;
the compare-and-register function protects the native callback slot
without claiming firmware-global interception of all legacy drivers.

**No Stable/main merge, no release, no firmware flash, no USB/SD
changes, no v1.9 until software gates close.**
