# E11 — External CC1101 RX TIM17 / PB2 / EXTI2

**Scope:** pinned Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`,
`dev/v1.8-completion` / Draft PR #13 only.
**Status:** Original external plugin RX production C **HOST PASS**;
a matched full Momentum firmware/FAP/updater build **PASS** at the
pre-V2 commit. Newer V2 and ISO15693 builds are tracked separately.
All actual RF hardware remains **DEFERRED / HARDWARE PENDING**.

## Source-verified physical aliases

External CC1101 default G0 is `SUBGHZ_DEVICE_CC1101_EXT_TX_GPIO`,
**external PB2** in `applications/drivers/subghz/cc1101_ext/cc1101_ext.c`.
This is not the built-in CC1101 internal **PA1**. PB2 competes with
NFC internal **PA2** for the same *EXTI2* interrupt line. Its RX
uses **TIM17**, also used by native NFC's TIM1+TIM17 owner.

[`patch_momentum_native_ext_cc1101_rx_lease.py`](../scripts/patch_momentum_native_ext_cc1101_rx_lease.py)
implements one **TIM17 | PB2 | EXTI2** atomic mask and an exact
bool `subghz_device_cc1101_ext_try_start_async_rx`. The existing
void external radio plugin interconnect remains binary compatible.
Legacy/foreign TIM17 clock or callback occupancy is refused **before**
radio state, timer registers, GPIO mode or ISR installation.

The original code previously called
`furi_hal_gpio_remove_int_callback` before registration even when
a callback belonged to another module. This has been replaced by
atomic GPIO `try_add`; STOP now uses `try_remove` matching both
callback and context, with an opaque exact owner and sticky failed
release. A denied START followed by STOP cannot reset a foreign GPIO
or steal its timer/interrupt. Its actual capture callback checks
the held owner and TIM17 clock before any read/write.

Unknown external G0 assignments and **all** optional debug-mirror
pins deliberately return BUSY for this stage. This is a compatibility
limit rather than silently operating unclaimed physical pins.

**Evidence:** original external CC1101 native RX ISR/START/STOP C
and real firmware resource allocator, including occupied NFC EXTI2,
TIM17 BUSY, wrong mask, no register writes on denial, duplicate
START/STOP, replaced callback, failed release and lost timer:
[HOST #38919891825 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38919891825).
Matched full Momentum firmware, native JS, one LabMate FAP, updater
and SDK/radio/option-byte verification:
[#38920011519 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38920011519).

## Strictly open E11 responsibilities

External CC1101 **TX** still uses TIM17 and DMA2 **channels 3/4/5**
(and configurable debug mirror). Those cannot be represented by
the original 32-bit V1 mask, so the separate exact V2 lease was
created and host-tested. It is **dormant** until actual external TX
code, DMA ISR and STOP are fully migrated; see
[`E11_SIGNAL_READER_DMA_HANDOFF.md`](E11_SIGNAL_READER_DMA_HANDOFF.md).

The external v1 plugin `start_async_rx` signature is **void**; the
in-firmware SubGHz device/worker chain cannot yet receive a truthful
BUSY from this external plugin. Its denied STOP is safe, but GUI/worker
state may still think the RX session started. Do not claim upper
caller success without an explicit status-compatible plugin path.

Still OPEN: TX DMA2 CH3/4/5, unsupported external G0 or mirror pins,
plugin-to-worker BUSY reporting, external SPI/amp optional-pin
leases and radio concurrency, SignalReader TIM16/DMAMUX, full hardware
RF/receiver tests.

**No flash, no Stable/main merge, no v1.9 or physical PASS.**


## 2026-10-16 — External RX/TX follow-up status

The older paragraph identifying **external TX DMA2 CH3/4/5** as
unmigrated records a superseded development checkpoint.
The native TX V2 source migration, ISR/STOP host fault test
[#38924389450 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38924389450)
and combined full matched firmware/FAP/updater
[#38924489972 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38924489972)
have since passed. Existing RX gate
[#38924389500 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38924389500)
was also rerun alongside TX.

The previous external plugin `void` RX callback still **cannot
report BUSY to every SubGHz higher-level worker**. Unsupported
configurable G0 and debug pins, optional SPI/amp/LED GPIO ownership,
legacy native IRQ and actual RF tests remain OPEN. No physical PASS,
Stable release, merge, SD/USB access or firmware flash.
