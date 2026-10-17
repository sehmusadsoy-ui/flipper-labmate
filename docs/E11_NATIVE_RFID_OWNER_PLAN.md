# E11 RFID native owner migration — exact pinned-source plan

**Status:** OPEN / PARTIALLY IMPLEMENTED. READ TIM1 and comparator capture
TIM2 are staged with production-C host evidence. DMA emulation, field,
upstream BUSY handling, other native IRQ/GPIO and hardware remain OPEN;
no release approval is implied.  
**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`  
**Branch:** `dev/v1.8-completion`, Draft PR #13.

## Original source inventory

Source: `targets/f7/furi_hal/furi_hal_rfid.c` (pinned revision).
RFID currently configures timers and GPIO directly without firmware
global E11 leases. The following are *different* service lifecycles,
not one interchangeable TIM1/TIM2 owner:

| Mode | Native entry/exit | Shared resources | Existing pre-claim mutations |
|---|---|---|---|
| Carrier/read PWM | `furi_hal_rfid_tim_read_start/stop`, `read_continue/pause`, `set_read_period/pulse` | TIM1 plus internal RFID read GPIO | clock enabled and pins configured at start; follow-up functions write TIM1 directly |
| Read capture | `furi_hal_rfid_tim_read_capture_start/stop` | TIM2, capture channel IRQ and read GPIO | callback, GPIO and timer configuration |
| DMA emulation | `furi_hal_rfid_tim_emulate_dma_start/stop` | TIM2, DMA2 channels 1 and 2, DMA interrupt, emulate GPIO | callback/context and pins configured before bus enable; DMA/ISR teardown separate |
| Field detection | `furi_hal_rfid_field_detect_start/stop` | **TIM2 + TIM1 + DMA2 channels 1 and 2 in one composite claim**, field GPIO | pin state changed before either clock; field setup starts TIM2 and TIM1 separately; STOP deinitializes both DMA channels and both clocks |
| Comparator and pin utilities | `furi_hal_rfid_comp_*`, `furi_hal_rfid_pins_*` | Internal comparator/EXTI and hardware pins | their own non-timer callback/pin lifecycle |

## Required staged approach

The implemented first stage migrated **read PWM** as a canonical TIM1-only claim with a
status-bearing internal start. Acquire before enabling clock or
changing RFID pins. A denied START must not mutate hardware,
and `read_continue`, `read_pause`, period, pulse and STOP must
be guarded by the retained handle and valid TIM1 clock.
Wrong-mask and failed-release paths retain sticky ownership. Keep
legacy void HAL symbols for ABI while adding a truthful BUSY status
for upstream callers; otherwise a denied native START may still
leave the caller believing RF transmission is active.

The second staged host-verified stage migrated **TIM2 comparator read capture**
with a timer-owner guard on the ISR/STOP; its legacy upper callers,
comparator/EXTI and internal GPIO ownership remain open. Next migrate
**TIM2 + DMA2 emulation** with complete IRQ/DMA/GPIO claims and native consumer BUSY handling.
A claim must occur before updating callback state, GPIO modes,
timer registers, DMA requests or interrupt installation.
Native ISR must check the current owner. STOP only releases the
resources the same session acquired, and must never clear a
foreign DMA interrupt.

Finally migrate **field detection** as one atomic composite
TIM1|TIM2|DMA2-CH1|DMA2-CH2 claim. Never acquire TIM2 and
then TIM1 as two unrelated transactions: that can temporarily
modify TIM2 before learning that PWM, NFC, iButton or infrared
owns TIM1. Make aborted field detection safe for a later STOP,
and test field mode against simultaneous Counter/DigitalSequence,
NFC TIM1 and native infrared TX sessions.

Each mode needs **real original native C host fault injection**:
denied claim = zero timer/GPIO/DMA/ISR writes, pre-enabled legacy
clock/DMA, partial allocation/claim rollback, genuine
START/continue/pause/STOP, ISR and DMA callbacks, stale owner,
failed release, unexpected clock loss, double STOP, and native-native
mode handoffs. A full pinned Momentum firmware + single LabMate
FAP + JS + official MNTM-012 package comparison is mandatory
**after** each integrated patch.

## Explicit blockers

The original RFID APIs largely return `void` and some higher-level
protocol calls may set pins/state before invoking the HAL
start. Their call sites must consume BUSY; source-only compiler
success does not prove native service safety. Existing
`furi_hal_bus_enable` can assert when another owner is active,
so it is **not** safe to substitute a silent no-op or trust an
uncoordinated `is_enabled` check as an atomic lock.

**Firmware-global E11 remains OPEN** while RFID, Sub-GHz and
other native EXTI clients bypass the lease table. Physical
coexistence is **DEFERRED / HARDWARE PENDING**, not PASS.
No main/Stable merge and no firmware installation without an
approved backup/recovery and physical acceptance protocol.

## 2026-10-16 evidence checkpoint

- READ TIM1 actual-C+allocator host [#38902785963](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38902785963) SUCCESS; full matched firmware+FAP/JS/updater [#38903026814](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38903026814) SUCCESS.
- Capture TIM2 actual native production-C+allocator host [#38904967453](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38904967453) SUCCESS. See [capture gate](E11_NATIVE_RFID_CAPTURE_TIM2_GATE.md); its full matched updater [#38904996042](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38904996042) needs separately confirmed conclusion.
- Physical coexistence remains DEFERRED / HARDWARE PENDING. Firmware-wide E11 still OPEN; main, Stable, Flipper, SD/USB remain untouched.
