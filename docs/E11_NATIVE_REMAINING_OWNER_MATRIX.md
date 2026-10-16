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
| Native iButton emulation | TIM1 and internal pin configuration only after successful claim, protocol Misc STOP ownership | `test_v18_native_ibutton_tim1_lease.py`, `test_v18_native_ibutton_protocol_lease.py`; full paired firmware CI #38888012694 PASS |
| Native RFID carrier/read PWM TIM1 | Owner acquired before native read GPIO or timer writes, guarded pause/continue/retune/STOP with sticky failure refusal | Real production C + allocator [#38902785963](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38902785963) PASS; matching firmware/FAP/updater [#38903026814](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38903026814) SUCCESS; normal/RAW caller BUSY handled in later CI; some legacy callers remain unreviewed |
| Native RFID comparator capture TIM2 | Atomic TIM2 claim before capture callback, clock, IRQ and comparator writes; native ISR and owned STOP fail closed on BUSY, timer loss and release faults | Real native capture C + allocator [#38904967453](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38904967453) SUCCESS; capture-only matched updater [#38904996042](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38904996042) **SUCCESS**; later normal/RAW/UI combined software and remaining DMA/field modes tracked separately |
| Native LFRFID normal+RAW READ worker and native scene BUSY | Calls both bool carrier/capture HAL STARTs; returns BUSY without infinite ASK/PSK retry; RAW refuses before opening/writing SD; normal and RAW scenes display RFID BUSY and suppress false success | Normal worker original-helper C [#38906188632](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38906188632) PASS + early full updater [#38906213089](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38906213089) PASS; RAW original-helper C [#38906641928](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38906641928) PASS; scene callback actual-C [#38907211834](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38907211834) PASS; READ/RAW/UI full matching pair [#38907211713](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38907211713) **SUCCESS**; native record/GUI on device NOT TESTED |\n| Native RFID TIM2+DMA2 emulation and native LF workers | One atomic TIM2/DMA2 CH1+CH2 claim, no DMA or pin writes on BUSY, owned ISR/STOP and sticky fault state; normal & RAW emulation workers consume bool BUSY and RAW scene warns instead of fake success | Real HAL C + firmware allocator [#38908647175](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38908647175) SUCCESS; native worker helper-C [#38908966404](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38908966404) SUCCESS; latest matched updater still separate CI gate; normal emulation scene BUSY visual and physical RF unverified |
| Native RFID field detection TIM1+TIM2+DMA2 | One atomic TIM1, TIM2, DMA2 CH1/2 claim BEFORE pin/timer/DMA writes; owned STOP/update IRQ teardown and frequency health check refuse absent clock; legacy void ABI retained | Real field production C + actual lease allocator [#38909551118](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38909551118) SUCCESS; latest matched updater [#38909551244](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38909551244) PENDING; physical field/pin/EXTI NOT TESTED |
| Native infrared RX / TIM2 | Refuses occupied TIM2 before native RX GPIO/IRQ changes; guarded ISR, timeout, owned STOP and sticky lease faults | `test_v18_native_infrared_rx_lease.py` actual RX C CI #38891712004 PASS; RX worker BUSY+denied-STOP actual C CI #38901733766 PASS; full integrated firmware/FAP/updater CI #38901733940 SUCCESS; TX separately integrated CI #38897716100 PASS |
| Native infrared TX / TIM1 + DMA2 | Composite TIM1+DMA2 CH1/CH2 claim, external PA7 alias and PA7 accessory probe, BUSY-aware worker, sticky release/clock-loss guards | Real native production C/firmware allocator CI #38897716061 PASS, full matched MNTM-012 firmware/FAP/JS/updater CI #38897716100 PASS; physical IR TX not validated |
| Native NFC FWT / Block-TX timers | Atomic TIM1+TIM17 composite lease, BUSY propagated from low-power resume, owned ISR/STOP and oscillator-failure rollback | `test_v18_native_nfc_tim1_lease.py` real NFC timer + low-power resume C host PASS #38890147922, full matched firmware/FAP/updater CI #38890148015 PASS; other NFC GPIO IRQ clients uncoordinated |

The lease mutex covers **cooperating** clients atomically. Direct
LL register writes in unrelated firmware components still bypass it;
a successful `furi_hal_bus_is_enabled` check alone cannot prevent a
noncooperating TIM1/TIM2 start immediately afterward.

## Native bypasses requiring redesign (not just a preflight check)

| Native source | Pinned code issue | Minimum software exit criteria |
|---|---|---|
| `targets/f7/furi_hal/furi_hal_subghz.c` | Async RX and TX both use TIM2. RX changes radio state and CC1101 GPIO before enabling timer; TX owns DMA, TIM2 IRQ and cleanup state. | Acquire complete TIM2/required DMA/IRQ resources **before** radio/GPIO/state writes, propagate BUSY through callers instead of silently returning, ensure each stop owns its timer, test RX/TX DMA and radio recovery |
| `targets/f7/furi_hal/furi_hal_rfid.c` — internal pins, comparator/IRQ, upper clients and recovery | READ TIM1, capture TIM2, emulation TIM2+DMA2, and field TIM1+TIM2+DMA2 are now separate staged cooperative leases with original-C host fault gates. Normal/RAW READ and EMULATE callers have bool BUSY guards and native UI/RAW status. **Still uncoordinated:** comparator/EXTI20, internal iButton/NFC GPIO configuration/reset utilities, other legacy void clients, debug GPIO, native radio races and hardware-only coexistence. | Integrate internal GPIO/EXTI ownership and all native callers, verify worker scheduling and error recovery; require latest complete firmware/JS/FAP/updater SUCCESS and explicit fixture-based tests before firmware-global E11 closure |
| Infrared worker RX BUSY, TX timeout/recovery and radio coexistence | Native TX TIM1+DMA2 CH1/2 (+PA7) and its worker bool BUSY/STOP/WAIT are now lease-managed, actual native C host CI #38897716061 PASS; PA7 detection probe is also guarded. RX now has a bool BUSY-aware worker start and denied-start thread/IRQ-callback rollback, actual C CI #38901733766 PASS, including safe no-op STOP after both rejected bool and legacy void START; old void API remains ABI-compatible but cannot communicate BUSY to callers. Noncooperating native DMA/IRQ and unexpected clock-loss TX recovery remain open. | Preserve successful paired RX-worker firmware/FAP/updater #38901733940; review TX completion recovery and maintain physical IR module coexistence as hardware-pending; validate cross-native TIM1 races before E11 closure |
| NFC GPIO IRQ/debug and physical NFC coexistence | TIM1+TIM17 ownership and firmware-low-power BUSY paths now have actual-C host PASS, but NFC IRQ GPIO is still a direct registration and optional PA7/PA6 debug outputs remain unclaimed (debug build now rejected). | Coordinate shared NFC IRQ GPIO ownership with other EXTI native clients and validate NFC field/recovery on device after explicit firmware install approval; no physical PASS from host tests |
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
