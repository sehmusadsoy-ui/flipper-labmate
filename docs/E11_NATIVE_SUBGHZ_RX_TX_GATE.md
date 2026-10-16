# E11 — Native Sub-GHz RX/TX timer and DMA owner gate

**Branch:** `dev/v1.8-completion` / Draft PR #13.  
**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** Real production-C RX and TX driver fault-injection HOST SUCCESS.
Built-in CC1101 RX device + application BUSY propagation host SUCCESS.
**Newest matching complete Momentum firmware/FAP/JS/updater CI still must
finish successfully**. All physical RF, IRQ/EXTI and debug hardware
acceptance remains **DEFERRED / HARDWARE PENDING**.

## Exact board mapping and collision

At the pinned firmware source `targets/f7/furi_hal/furi_hal_resources.h`:
`CC1101_G0_GPIO_Port GPIOA` and `CC1101_G0_Pin LL_GPIO_PIN_1`.
**Internal CC1101 G0 is PA1, not external connector PB3.** Both share
TIM2 via the Sub-GHz HAL, but a TIM2 lease does not imply a PB3 GPIO
lease. PB3 and PA7 bits are added **only when the actual configured
external debug mirror pin is PB3 or PA7**. Do not conflate GPIO pin
aliases with hardware timer channels.

## Reviewed RX HAL

[`patch_momentum_native_subghz_rx_lease.py`](../scripts/patch_momentum_native_subghz_rx_lease.py)
adds a bool `furi_hal_subghz_async_rx_try_start` while retaining the
published void legacy HAL START. It acquires a cooperative TIM2 lease
before callback, CC1101 GPIO, IRQ or radio mutations, rejects
pre-enabled legacy timer clocks without writes, and handles the
optional supported PA7/PB3 debug-mirror claim atomically.

A denied or repeated START cannot accidentally clear another owner's
TIM2 flags, ISR or GPIO on STOP. Its original ISR is guarded by the
held owner and live TIM2 clock; unexpected clock loss and failed lease
release make the owner sticky, requiring controlled recovery.

Unsupported mirror pins are **explicitly refused**, not operated
without ownership. Extending mirror support beyond PA7/PB3 is an OPEN
compatibility/functionality task, not a hidden completed feature.

**Actual native C + genuine firmware allocator host:**
[CI #38911157761 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38911157761).
Regressed denied-zero-hardware-write, normal RX ISR, repeat START/STOP,
failed release, clock loss, legacy enabled TIM2 and optional external
PA7/PB3 conflicts with native IR/Counter.

## Built-in RX caller propagation without breaking external plugins

[`patch_momentum_native_subghz_rx_busy_callers.py`](../scripts/patch_momentum_native_subghz_rx_busy_callers.py)
routes BUSY through the real in-firmware chain:
`cc1101_int_interconnect.c` →
`lib/subghz/devices/devices.c` →
`applications/main/subghz/helpers/subghz_txrx.c`.

The built-in CC1101 gets a bool START through a new firmware function.
On BUSY, Sub-GHz RX does not start its worker, announce an RX state or
activate the speaker. The older public void wrapper and the v1 plugin
interconnect function pointer **remain ABI-compatible**. External radio
plugins still use their older void function, which cannot truthfully
report BUSY without a coordinated plugin API change. This is an
explicit remaining capability gap.

**Actual native interconnect, device and app C host:**
[CI #38911453319 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38911453319);
also [#38912207664](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38912207664)
SUCCESS after later TX-stage fixture isolation.

## Reviewed TX HAL

[`patch_momentum_native_subghz_tx_lease.py`](../scripts/patch_momentum_native_subghz_tx_lease.py)
keeps the **existing bool TX API and regional TX permission check**.
One atomic mask owns TIM2 + DMA2 CH1 for normal TX; with PA7/PB3
debug mirror it additionally owns DMA2 CH2 and that exact external pin
BEFORE callback, buffer allocation, timer/IRQ, CC1101 GPIO or radio
writes. It denies already-enabled legacy TIM2 or the DMA channels
it plans to mutate.

An unavailable allocation unwinds the **exact acquired claim** without
GPIO/DMA effects. The genuine DMA ISR, completion check and STOP are
ownership/clock/active-DMA guarded; denied STOP and stale ISR are
no-ops and unexpected clock or DMA loss prevents arbitrary foreign
resource teardown. Normal STOP releases owned DMA, timer, CC1101 G0
and debug mirror then the original exact opaque claim. Failed release
is sticky.

**Actual native TX ISR/START/STOP C + genuine firmware allocator:**
[CI #38912471437 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38912471437).
Host tests cover regional denial, denied-zero-writes, legacy TIM2/DMA
occupancy, allocation failure, normal TX/STOP/re-entry, debug mirror
DMA2 CH2, foreign DMA conflicts with RFID/infrared, repeat STOP,
release failures and loss of timer clock. Host mocks are not proof of
accurate radio modulation, timing or RF emission.

The compile-time `FURI_HAL_SUBGHZ_TX_GPIO` build option is deliberately
rejected at compile time until its optional GPIO is jointly leased;
a firmware build enabling that macro is not supported by this
candidate. Other dynamic mirror choices beyond PA7/PB3 are also
rejected. These remain **OPEN**.

## End-to-end acceptance and known gaps

The matching Momentum firmware, single LabMate FAP, native JS GPIO
module and MNTM-012 full updater package with source provenance,
APPCHK, radio/option-byte policy and checksums must pass at its *exact
source SHA* before accepting these stages as build-matched software.
Current full gate:
[CI #38913062269](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38913062269) (full firmware/ABI/release packaging IN PROGRESS at this checkpoint).
Earlier #38912588242 failed at firmware link because the new built-in CC1101 boolean wrapper lacked C linkage in the C++ SDK table; the header now uses extern-C linkage (source commit 69ecfdd). Record the final #38913062269 conclusion separately from the three host-C success
runs; older successful package #38909551244 predates Sub-GHz work.

Remaining E11 coverage: native RF pin and EXTI/IRQ users beyond
the cooperating entrypoints, arbitrary mirror pin/plugin API support,
Sub-GHz hopper/CLI/error-UI handoffs and standalone external radio
plug-ins, full concurrent workload tests, optional TX debug GPIO,
legacy direct LL bypasses, field coexistence and every physical
RF/module/connector test. The old void RX ABI cannot signal BUSY and
must not be counted as a truthful status-bearing API.

**No v1.6 firmware-global COMPLETE, no v1.9, no main/Stable merge,
no package installation/flash, no SD/USB changes.**
