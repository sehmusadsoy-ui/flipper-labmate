# E11.1x — Native Sub-GHz TIM2 and shared DMA2 migration gate

**Source of truth:** pinned Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`,
`targets/f7/furi_hal/furi_hal_subghz.c`. **This is a source
design gate, NOT a driver patch and NOT an implementation PASS.**
Draft PR #13 only. Firmware Stable/main and installed device unchanged.

## Confirmed native hardware overlaps

- Async Sub-GHz **RX** uses **TIM2**, CC1101 G0 alt-output/capture
  GPIO, TIM2 CC1/CC2 and native TIM2 ISR. The original
  `furi_hal_subghz_start_async_rx` returns **void** and changes
  `state`, capture callback, external radio GPIO and TIM2 clock
  before the native timer is fully initialized. `stop_async_rx`
  unconditionally transitions radio to idle, disables TIM2 and removes
  ISR. A denied timer claim must not execute this STOP sequence.
- Async Sub-GHz **TX** already returns **bool** for regional TX
  permissions. It configures **TIM2 + DMA2 channel 1**, and
  **DMA2 channel 2 when debug mirror is enabled**, with native
  DMA ISR, CC1101 G0 output and SPI radio TX switching. It sets
  `SubGhzStateAsyncTx` and allocates the transmit buffer before
  enabling the timer. A BUSY resource claim can reuse existing bool
  semantics only if performed **before any state/GPIO/radio/DMA changes**.
- **Critical cross-service collision:** infrared TX separately
  reserves **DMA2 channels 1 AND 2**, in addition to its TIM1 and
  optional PA7 output. Hence Sub-GHz TX can collide with infrared TX
  **even though their timer numbers differ**. Both DMA channels must
  be accounted for by the same global E11 allocator mask.
- The source may enable an optional **dynamic debug mirror GPIO**
  whose pin is supplied through `async_mirror_pin`. This GPIO
  cannot be treated as a fixed PB3/PA7 alias. Either map and claim
  its precise physical pin atomically with the TIM2/DMA reservation,
  or return a clearly surfaced unsupported/BUSY result without
  touching mirror GPIO. Never turn a DMA denial into silent firmware
  bus-disable no-op.
- CC1101 G0 is configured in both RX and TX. Its exact physical
  alias must be identified from the pinned board resource definition
  before adding a fixed GPIO lease.

## Exit criteria for production source migration

1. A canonical **TX** composite mask for TIM2, both relevant DMA2
   channel masks and CC1101 G0 physical pin, with optional debug
   mirror pin accounted for. Before any state/callback/buffer/GPIO
   write, the bool TX START checks the lease and legacy already-live
   DMA/TIM2; on denied claim it returns false without side effects.
2. Full failed-allocation rollback; no stale TX state or orphaned
   buffer; ISR stops touching DMA on ownership loss; STOP can disable
   only its own radio/IRQ/clock and releases the exact opaque handle
   **after** teardown. Failed release stays sticky.
3. A **BUSY-capable RX** entrypoint and caller integration that does
   not start an RX thread, change radio state or invoke RX STOP after
   a denied TIM2 claim. Preserve original public void symbol.
4. Actual source C fault-injection for RX, TX, TIM2, DMA2
   (including conflict with infrared TX when TIM1 is independent),
   GPIO aliases, unexpected clock loss, wrong/double handle release,
   debug-pin denial, STOP and repeated start. No full HAL PASS based
   only on compile or source-string inspection.
5. Matched full firmware, single LabMate FAP, JS plugin and
   official MNTM-012 updater/policy comparison CI, followed by
   separately approved hardware coexistence test when equipment is
   available. **DO NOT FLASH** a review-only CI artifact.

**Status:** OPEN, not counted toward closed E11/v1.6 firmware-global
resource ownership. Physical verification DEFERRED/HARDWARE PENDING.
