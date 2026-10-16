# E11 — SignalReader TIM16 / DMAMUX RG0 / DMA2 and NFC ISO15693 handoff

**Date:** 2026-10-16. **Pinned source:** Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Scope:** `dev/v1.8-completion` and unmerged Draft PR #13.
**Status:** Collision analysis and **additive V2 firmware allocator**
implemented/tested; **SignalReader driver, parser and NFC caller are
NOT migrated**. E11 is **OPEN**.

## Exact production call path, not a hypothetical GPIO tool

`targets/f7/furi_hal/furi_hal_nfc_iso15693.c`
`furi_hal_nfc_iso15693_listener_alloc` constructs
`iso15693_parser_alloc(&gpio_nfc_irq_rfid_pull, ...)`: this pin is
**internal PA2**, the same EXTI2 alias owned by ordinary native NFC IRQ.
`lib/signal_reader/parsers/iso15693/iso15693_parser.c` calls
`signal_reader_start` and `signal_reader_stop` via a legacy
**void-returning** parser lifecycle.

The pinned ISO15693 listener **does** transfer this pin during transparent
mode: `furi_hal_nfc_iso15693_listener_transparent_mode_enter` calls
`furi_hal_nfc_deinit_gpio_isr()` after switching/deinitializing SPI,
relinquishing the NFC PA2/EXTI2 callback/lease. The exit path calls the
legacy `void furi_hal_nfc_init_gpio_isr()` before SPI reinit, so an
unexpected BUSY **cannot currently propagate** to the listener and
its cleanup. Replacing this with an unconditional global EXTI veto or
with an IRQ callback removal is **unsafe**. The lifecycle must be
transactional and report status on both acquire and restore.

## Exact resources and observed bypass

The original `lib/signal_reader/signal_reader.c` directly mutates:

- **TIM16**, its internal CH1 and DMA2 CH2 (GPIO bit capture).
- **DMA2 CH3** (DMAMUX-triggered counter start) and **DMA2 CH5**
  (counter synchronization).
- **DMAMUX request generator 0**, global to other possible DMA clients.
- **PA2 + EXTI2** configured as interrupt rise/fall, with no SignalReader
  callback registration but with line IRQ enabled.
- The DMA2 CH2 interrupt vector (it installs its own callback).

The original START is `void`: it changes callback and timer state and
then GPIO/DMAMUX/DMA2 and IRQ registers without an E11 claim.
The original STOP unconditionally disables its DMA ISR, DMA2 CH2/3/5,
GPIO EXTI and TIM16; it **does not explicitly disable request generator
0** before returning. STOP after a denied (future) START cannot be
allowed to remove a foreign DMA/IRQ/EXTI setup.

The **external CC1101 TX** plugin independently uses TIM17 and DMA2
**CH3/CH4/CH5**, including CH3+CH5 overlap with SignalReader. Its RX
is now separately host-gated on TIM17+PB2+EXTI2. The external plugin
TX mode remains unsafe/unmigrated, as do arbitrary G0/debug mirror
pins and the plugin's legacy void RX START notification.

## E11 V2 ABI-safe resource foundation

`scripts/patch_momentum_e11_extended_dma_lease.py` adds a
**separate** `furi_hal_resource_lease_v2_try_acquire(uint64_t)` and
`furi_hal_resource_lease_v2_release(handle,uint64_t)` pair.
It **does not modify** the existing `uint32_t` V1 exported function
signatures or handle namespace. V2 exact composite masks reserve
previously unrepresentable high bits:

| Atomic V2 claim | Low 32-bit aliases shared with V1 | High-bit unique owners |
|---|---|---|
| `FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC` | internal PA2, EXTI2, DMA2 CH2 | TIM16, DMA2 CH3, DMA2 CH5, DMAMUX RG0 |
| `FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX` | TIM17, external PB2 | DMA2 CH3, CH4 and CH5 |

Both share the *same physical low-bit busy table* with V1, so a
SignalReader V2 request is denied while the existing NFC IRQ or RFID
DMA emulation lease is held. The external CC1101 TX V2 request is
denied when native NFC TIM17, external CC1101 RX PB2 or overlapping
SignalReader DMA channels are already claimed. Both cannot hold
DMA2 CH3/CH5 simultaneously.

V2 is initially **dormant**. Host CI
[#38920909082](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38920909082)
tests genuine firmware V1+V2 C under cross-family collisions,
wrong release/double release, unsupported partial masks, handle
exhaustion and pthread start races. This passes as **allocator-level
evidence only**, NOT SignalReader/CC1101 TX implementation acceptance.
Matching firmware package CI also remains a separate acceptance gate.

## Required software completion stages (not claimed PASS)

1. Extend NFC ISO15693 transparent exit to check the status-bearing
   NFC PA2+EXTI2 re-registration. Preserve SPI/radio cleanup and
   propagate or retry a truthful BUSY; do not silently report ISO15693
   PASS with an absent IRQ handler.
2. Convert genuine SignalReader START to bool with atomic V2 lease
   **before** its buffer/ISR/GPIO/DMAMUX/timer writes, native legacy
   peripheral/channel preflight, and precise EXTI2 callback-slot
   reservation. The existing NFC transparent-mode handoff permits PA2
   to be owned by SignalReader only while NFC's ordinary IRQ callback
   is fully stopped. No fake global GPIO/EXTI no-op veto.
3. Guard DMA CH2 ISR and all STOP actions with exact owner, live timer,
   and expected DMA generator/channel state; on STOP **disable DMAMUX
   RG0 and IRQ** before DMA2 channel deinit, restore PA2 only if
   actually owned and release the exact V2 handle.
4. Wire `iso15693_parser_start`/listener `wait_event` to bool BUSY
   propagation. A void wrapper may remain for ABI, but the caller must
   not enter a receive wait or call unowned STOP after denial.
5. Convert external CC1101 TX to its distinct V2 composite and protect
   optional mirror pins + DMA CH3/CH4/CH5 original ISR. Preserve the
   regional transmit restriction, old plugin v1 ABI and safely skip TX
   when allocation or claim fails.
6. Execute actual patched production C for START/ISR/STOP, forced
   claims, malformed callbacks, competing NFC/RFID/CC1101, failed
   releases, nested handoff and regulator constraints. Then require
   exact pinned full Momentum+ONE LabMate FAP+native JS+MNTM-012 updater
   **SUCCESS** before software acceptance.

**Physical tests remain DEFERRED / HARDWARE PENDING** (NFC cards,
field/RF, external CC1101, DMA waveforms, STOP/BACK). No Stable/main,
flash, SD/USB or v1.9 changes from this allocator foundation.
