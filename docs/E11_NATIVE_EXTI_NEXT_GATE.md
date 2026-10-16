# E11 — Remaining Momentum-native EXTI/IRQ/GPIO owner work

**Scope:** v1.8 development `dev/v1.8-completion` and pinned Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** Source audit with staged CC1101 RX/NFC EXIT and V2 allocator
C gates PASS where linked; SignalReader and CC1101 TX remain OPEN.
This document itself does not confer physical PASS. Main, Stable, hardware and
SD/USB untouched.

## Concrete native EXTI source inventory

| Native producer | Pinned source behavior | Required exclusion / fail-safe |
|---|---|---|
| `targets/f7/furi_hal/furi_hal_nfc_irq.c` | **IMPLEMENTED/HOST PASS**: NFC now claims PA2+EXTI2 before writing PA2, uses native atomic GPIO callback TRY-ADD/compare-and-remove, and boot/low-power resume reports BUSY; host original NFC callback C/allocator [#38916131290](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38916131290). | Still require full firmware matched gate #38916167413, native ISR + other RF concurrency reviews and physical HW-12 |
| `lib/one_wire/one_wire_slave.c` | Native 1-Wire slave START installs a GPIO callback and configures rise/fall pin without E11 claim. STOP changes pin state and removes callback unconditionally. Pinned default `gpio_ibutton` uses **PB14**. | Preserve native iButton emulation TIM1 ownership and separately guard 1-Wire pin + EXTI14; route BUSY and ensure double/denied STOP is not a foreign callback removal |
| `applications/services/input/input.c` | System input service registers ISR callbacks for all board buttons early, with debounce timers. | **Reserved system infrastructure:** never add a global silent EXTI veto or substitute/erase input callbacks. Pin-claim model must explicitly exclude keypad ports and preserve UI STOP/BACK |
| `targets/f7/furi_hal/furi_hal_serial_control.c` | **IMPLEMENTED/HOST PASS:** two selected native USART1 RX **PB7/EXTI7** and LPUART1 RX **PC0/EXTI0** atomic lease masks, callback/ctx compare-and-register/remove, owned UART direction changes, new bool service queue BUSY. Actual original production C + allocator [#38917845230](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38917845230). | Must still validate complete source matched firmware/FAP/updater CI [#38917937898](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38917937898), expansion module client GUI/retry and physical HW-13. Legacy void client API cannot return BUSY. |
| `applications/drivers/subghz/cc1101_ext/cc1101_ext.c` | **RX implemented and host/full firmware PASS** for exact external PB2/EXTI2/TIM17 native owner; callback theft replaced with atomic try-add and compare/remove. [Evidence](E11_NATIVE_EXT_CC1101_RX_GATE.md). **TX still opens TIM17 + DMA2 CH3/4/5 without a composite claim**, external plugin v1 void RX cannot report BUSY to workers, arbitrary G0/mirrors unsupported. | Use V2 exact external TX mask and original DMA ISR/STOP native-C fault injection; design plugin-compatible worker BUSY without changing v1 ABI, verify supported physical mirror aliases and RF HW-14 |
| `lib/signal_reader/signal_reader.c` + NFC ISO15693 parser/listener | **Still unprotected source client.** Uses NFC PA2/EXTI2 + TIM16 + DMA2 CH2/3/5 + DMAMUX RG0; original STOP leaves request-gen cleanup incomplete. Pinned NFC transparent-mode exit now propagates IRQ restore BUSY and skips unmask ([host C #38921482299](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38921482299) PASS). Exact additive V2 allocator [#38920909082](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38920909082) PASS. | Source-integrate bool SignalReader START, native EXTI callback slot reservation and guarded DMA/DMAMUX IRQ/STOP; propagate parser/listener BUSY. Full matched build and HW-15 still required; [route analysis](E11_SIGNAL_READER_DMA_HANDOFF.md) |
| `applications/debug/accessor/helpers/wiegand.cpp` and native JS/vGM GPIO | Direct callbacks can be registered for configurable pins (some JS paths already cooperate) | Enumerate exact supported pins and error paths; no blanket blocking of arbitrary GPIO events, isolate debug-only vs production, prevent double removal |

## Required implementation sequence

1. **Protect system UI.** Assert native button IRQ/EXTI callback registration
   remains unchanged and STOP/BACK still works in genuine production-C
   concurrent/denied-start host regressions. Never "solve" collisions
   by suppressing another native callback.
2. **NFC PA2 / EXTI2** and **external CC1101 TIM17/EXTI** are highest
   shared-service risk. Add exact source review, atomic composite masks
   and status-bearing starts without breaking plugins; verify native
   timer, GPIO and IRQ all unwound on failure.
3. **iButton 1-Wire PB14** now has host-verified scoped owner; **serial PB7/PC0** still needs owner tracking
   around their actual callback lifecycle; ensure bus/serial functionality
   is not disabled by unrelated LabMate actions.
4. SignalReader DMAMUX/EXTI trigger routing must be checked against the
   LabMate and native GPIO listener masks, then debug/user-selectable
   pins may be registered in a conservative supported set.
5. Each stage needs original compiled production-C fault tests, denied
   **zero unowned writes**, repeat START/STOP, stale callback, failed
   release, unexpected clock, cross-native and native/LabMate conflicts,
   followed by an exact pinned **full** Momentum firmware + single
   LabMate FAP + JS plugin + MNTM-012 updater/APPCHK/policy CI PASS.

Internal radio and IRQ services frequently share a **timer** without
sharing the same **physical pin**. In particular native CC1101 G0 is
**PA1**, its optional external PB3 mirror is a separate claim, and
NFC/RFID_PULL GPIO is **PA2**. Do not use connector aliases for
unrelated internal pins.

**Open acceptance:** Hardware/fixture-dependent coexistence is
`DEFERRED / HARDWARE PENDING`. Software cannot be marked firmware-wide
E11 COMPLETE while noncooperating native EXTI/IRQ clients above remain.
No firmware flash, main/Stable merge or v1.9 transition.

## Verified next serial implementation constraint

The pinned native `furi_hal_serial.c` handle-to-pin mapping routes
USART1 RX to **PB7** but LPUART1 RX to **PC0**. The common serial
control function obtains the RX pin from whichever handle is active.
Its expansion-mode switch currently disables serial RX before registering
the EXTI callback, then removes the callback before restoring serial RX.
A correct E11 patch must implement **two distinct transactional composite
masks**, handle successful and denied callback CAS, and roll back any
completed serial-direction change in the same handle. In particular,
the LPUART1/PC0 mask must contend with LabMate Monitor/OneWire/I2C
clients already using PC0 and EXTI0. The USART1/PB7 mask must contend
with USART1 communication and all EXTI7 aliases. The firmware system
input callbacks must be left unchanged. This gate remains OPEN and
cannot be replaced by a PB7-only one-size-fits-all patch.
