# E11 — Remaining native TIM1/TIM2/IRQ owner integration (2026-10-16)

**Status: OPEN / PARTIAL.** Applies to pinned Momentum source
`d3f89dfe2ef6b01839201598e9be1590cba80322` plus LabMate
`dev/v1.8-completion` candidate only. This matrix distinguishes
**actual C/CI pass** from uncovered firmware-native services; none of
the remaining rows can be marked physical PASS. Existing Stable,
`main`, radio firmware and installed device remain unchanged.

## Verified cooperative owners

| Producer | Shared resource and scope | Evidence |
|---|---|---|
| LabMate Counter / Frequency Meter | TIM2, PB3; refuses already-enabled legacy TIM2 and sticky release failure | `test_v18_tim2_lease_integration.py`, matched SDK/FAP CI |
| Native PWM / LabMate Generator | TIM1 + PA7 (or native LPTIM2/PA4), cooperative firmware lease | `test_v18_native_pwm_lease.py`, joint actual C host CI |
| Native JavaScript GPIO / PulseReader / Monitor / capture | Selected external physical GPIO + EXTI, PulseReader TIM2+DMA/DMAMUX | actual native/production C host tests; not all firmware IRQ clients |
| Native DigitalSequence | TIM2+DMA1 CH1/2 and 8 connector pin aliases; internal unknown pins only TIM2/DMA | `test_v18_native_digital_sequence_lease.py`, full updater |
| Native iButton emulation | TIM1 and internal pin configuration only after successful claim, protocol Misc STOP ownership | `test_v18_native_ibutton_tim1_lease.py`, `test_v18_native_ibutton_protocol_lease.py`; firmware pairing under CI |

The lease mutex covers **cooperating** clients atomically. Direct
LL register writes in unrelated firmware components still bypass it;
a successful `furi_hal_bus_is_enabled` check alone cannot prevent a
noncooperating TIM1/TIM2 start immediately afterward.

## Native bypasses requiring redesign (not just a preflight check)

| Native source | Pinned code issue | Minimum software exit criteria |
|---|---|---|
| `targets/f7/furi_hal/furi_hal_subghz.c` | Async RX and TX both use TIM2. RX changes radio state and CC1101 GPIO before enabling timer; TX owns DMA, TIM2 IRQ and cleanup state. | Acquire complete TIM2/required DMA/IRQ resources **before** radio/GPIO/state writes, propagate BUSY through callers instead of silently returning, ensure each stop owns its timer, test RX/TX DMA and radio recovery |
| `targets/f7/furi_hal/furi_hal_rfid.c` | TIM1 read/field timeout, TIM2 emulate/capture/field counter; shared DMA and ISR. Independent start/stop functions call `furi_hal_bus_enable/disable` without a canonical owner. | Transactional composite claims for each mode and safe rollback when second timer/DMA claim fails; accurate owner-based releases; host radio/RFID mode transition regressions |
| `targets/f7/furi_hal/furi_hal_infrared.c` | RX configures internal GPIO before enabling TIM2 and unconditionally disables on STOP; TX allocates DMA buffers/semaphore before enabling TIM1, may use external PA7 output. Public start routines return void. | TIM2 RX and TIM1 TX composite claims acquired before all effects, native-client-visible BUSY path, full allocation rollback, preserved ISR/DMA state and PA7 alias ownership |
| `targets/f7/furi_hal/furi_hal_nfc_timer.c` and `furi_hal_nfc.c` | NFC frame-wait timer uses TIM1; frame-block timer uses TIM17; `furi_hal_nfc_timers_init()` is void, called from low-power-mode exit. On failure its paired deinit can touch a timer it never acquired. | BUSY-capable transactional initialization of TIM1+TIM17 with per-timer owned state, `FuriHalNfcErrorBusy` propagation from low-power-mode restart, rollback of NFC GPIO/IRQ on timer-denied path, guarded deinit and frame timer stop, non-crashing host and NFC regressions |
| `lib/one_wire/one_wire_slave.c`, `applications/services/input/input.c`, `targets/f7/furi_hal/furi_hal_serial_control.c` and other EXTI clients | Direct interrupt registration and physical-line aliases are not all migrated to E11; GPIO callback ownership can change outside LabMate. | Pin/EXTI owner tracking at each real registration/removal boundary without overwriting firmware system input IRQs; preserve native peripheral functionality |
| `targets/f7/furi_hal/furi_hal_bus.c` | Existing bus enable is assertion-oriented `void`; changing it to no-op would let callers proceed with unclocked TIM registers and leave IRQ/DMA/radio state partly mutated. | **Never install a global silent timer veto.** Call sites must return BUSY (or explicitly roll back) before any peripheral mutation and clear only owned resources |

## Closing criteria

1. All TIM1/TIM2 **native** source paths either become cooperative
   lifecycle clients or have an independently tested, explicit equivalent
   global exclusion mechanism. Include IRQ, DMA, GPIO aliases and
   error-return behavior; no firmware-global PASS by just listing paths.
2. Negative-path tests compile and execute actual patched production
   C: denied start **zero unsafe writes**, partial acquisition/rollback,
   repeat START/STOP, stale-handle/double-release, unexpected clock loss,
   native/native and native/LabMate conflicts.
3. Compile one matched Momentum firmware + LabMate FAP + native JS module
   and a full, checksum-verified updater. Preserve exact source and
   checksums; successful host CI is not a device test.
4. Physical fixture-dependent coexistence and recovery are separately
   tracked as **DEFERRED / HARDWARE PENDING** until equipment is available;
   releasing custom firmware requires user-approved backup/recovery and
   controlled device testing. No physical test is reclassified PASS.

**Project rule:** v1.6 firmware-global resource ownership is *not*
closed while the critical native bypasses above remain open. No silent
scope reductions, Stable replacement, or v1.9 work.
