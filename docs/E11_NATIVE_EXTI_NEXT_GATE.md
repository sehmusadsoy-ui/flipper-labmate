# E11 — Remaining Momentum-native EXTI/IRQ/GPIO owner work

**Scope:** v1.8 development `dev/v1.8-completion` and pinned Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** Verified source inventory / OPEN. This document does not
modify native code or confer a test PASS. Main, Stable, hardware and
SD/USB untouched.

## Concrete native EXTI source inventory

| Native producer | Pinned source behavior | Required exclusion / fail-safe |
|---|---|---|
| `targets/f7/furi_hal/furi_hal_nfc_irq.c` | `furi_hal_nfc_init_gpio_isr` sets IRQ on `gpio_nfc_irq_rfid_pull` then registers and enables native GPIO callback. `deinit` removes it and resets pin to analog. On pinned F7 resource header RFID_PULL is **PA2**. | Claim PA2 and **EXTI2** atomically before pin mode/callback registration; BUSY must propagate through NFC startup, STOP cannot remove another owner; RFID field/READ share internal pin utilities |
| `lib/one_wire/one_wire_slave.c` | Native 1-Wire slave START installs a GPIO callback and configures rise/fall pin without E11 claim. STOP changes pin state and removes callback unconditionally. Pinned default `gpio_ibutton` uses **PB14**. | Preserve native iButton emulation TIM1 ownership and separately guard 1-Wire pin + EXTI14; route BUSY and ensure double/denied STOP is not a foreign callback removal |
| `applications/services/input/input.c` | System input service registers ISR callbacks for all board buttons early, with debounce timers. | **Reserved system infrastructure:** never add a global silent EXTI veto or substitute/erase input callbacks. Pin-claim model must explicitly exclude keypad ports and preserve UI STOP/BACK |
| `targets/f7/furi_hal/furi_hal_serial_control.c` | Expansion module detection disables RX direction, adds GPIO interrupt callback, and changes UART RX input mode; disable removes it and enables UART direction. Pinned USART1 RX is **PB7**. | GPIO PB7 + EXTI7 and USART direction need a coordinated composite transfer. BUSY should preserve UART and expansion detection, especially STOP/BACK |
| `applications/drivers/subghz/cc1101_ext/cc1101_ext.c` | External CC1101 plugin RX uses **TIM17** and a configurable G0 GPIO with EXTI callback; before its own add it removes any existing callback on that pin. STOP unconditionally removes callback and disables TIM17. | Urgent: never remove other EXTI owner; pin + EXTI + TIM17 atomic ownership, explicit denial/ROLLBACK and external plugin API compatibility. TIM17 also appears in native NFC timer ownership; maintain v1 radio plugin ABI |
| `lib/signal_reader/signal_reader.c` | SignalReader configures external interrupt trigger/DMAMUX even without a registered GPIO ISR; it enables the EXTI line and DMA request generator. | Pin + EXTI line + DMA/DMAMUX routing together, prevent asynchronous IRQ alias conflicts and stale DMA on STOP |
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
3. **iButton 1-Wire PB14** and **serial PB7** need owner tracking
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
