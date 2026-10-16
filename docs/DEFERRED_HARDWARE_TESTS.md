# LabMate — Deferred physical and compatibility verification backlog

**Status: OPEN / NOT TESTED where explicitly marked below.** This is a living
hardware-validation queue for equipment that is not available yet. Do **not**
mark PASS from CI, simulator results, or another device's digital loopback.
Keep this document even after v1.7 Stable; add dated, reproducible evidence
when suitable equipment becomes available.

| ID | Capability | Needed equipment | Current evidence | Deferred check | Status |
|---|---|---|---|---|---|
| HW-01 | Button Analyzer true contact bounce, settle, hold and debounce | Real dry-contact mechanical pushbutton, safe 3.3 V Flipper GPIO connection | Clean Flipper-generated PC1 digital signal; functional PASS | Compare real press/release counts, bounce N/us, settle ms, hold; try 5/10/20/50 ms debounce | **NOT TESTED** |
| HW-02 | PWM output accuracy and OFF state | Independent oscilloscope or calibrated logic measurement instrument | PA7 -> PC1/PB3 3.3 V digital loopback; functional PASS | Independently measure PA7 frequency/duty for representative low/high/custom presets and 5/50/95%; confirm OFF after STOP and app exit | **NOT TESTED** |
| HW-03 | Storage failure handling | Spare noncritical microSD card / controlled test media | Normal CSV/profile save/open/delete and restart PASS | Missing/full/corrupt-media and error/recovery handling without risking saved user data | **NOT TESTED** |
| HW-04 | External reference and extended GPIO modes | Known safe 3.3 V reference signal source and measurement equipment | Internal loopback tests at selected frequencies | Additional supported Pulse pins, extreme duty-frequency combinations, external input characteristics | **NOT TESTED** |
| HW-05 | Long-duration use | Charged Flipper, test microSD and repeatable checklist | Short and moderate device sessions were tested | Longer PWM/Logger sessions, navigation/resource handoffs, repeated restart with CSV/profile integrity checks | **NOT YET EXHAUSTIVELY TESTED** |
| HW-06 | v1.8 real I2C3 scanner, positive ACK/STOP/re-entry, contention | Independently verified safe **3.3 V** I2C peripheral on PC0 SCL / PC1 SDA and safe contention fixture | I2C READY, empty-bus NONE, STOP/BACK/re-entry on earlier paired DEV FAP physically PASS; new E11 code host PASS | Observe correct real 7-bit device address, zero false hits, cancellation after ACK and safe owner BUSY/fault recovery on an explicitly approved matching firmware+FAP pair | **NOT TESTED for actual ACK, safe external contention and latest E11 pair** |
| HW-07 | v1.8 1-Wire DS18B20 conversion, CRC, STOP | Verified externally VDD-powered **3.3 V** DS18B20 on PA4 with suitable 3.3 V DQ pull-up | Real driver/CRC host PASS; no-sensor NONE on an older DEV pair | Real plausible temperature, repeated STOP/BACK/conversion, release and coexistence with existing measurement modes | **NOT TESTED for real sensor and latest E11 pair** |
| HW-08 | v1.6/E11 firmware-wide GPIO/EXTI/TIM arbitration, native Momentum PWM/JS GPIO/PulseReader interaction | Verified rollback plan and operator-approved matched firmware+FAP with exact native JS plugin; safe 3.3 V test fixture; optional independent scope | Native PWM, JS GPIO plugin and PulseReader TIM2/DMA4/5/DMAMUX0 C host tests, matched CI build evidence; independent legacy services still bypass leases | Physically verify **LabMate PWM native HAL sole lease** START/RUN/duty/frequency/STOP/re-entry and ERR on foreign native PWM, TIM1 PA7 vs native PWM, PA4 LPTIM2 vs OneWire, JS GPIO/IRQ/event/Monitor conflicts, including **PC3 vs PB3 shared EXTI3** mode-init denial without register writes, TIM2 PulseReader vs Counter and occupied DMA; **TIM2 Counter/HIGH BUSY when native RFID/Sub-GHz already enabled timer**; clock disappears during capture → ERR without fabricated pulse count, fail-closed START/STOP/BACK/reopen/rollback without crash or overwriting unrelated state | **NOT TESTED on device; global native-service integration remains a separate software gate, not a hardware-only deferral** |
| HW-09 | E11 native RFID TIM1 read, TIM2 capture, TIM2+DMA2 emulation, TIM1+TIM2+DMA2 field detect and radio/IR/Counter contention | Operator-approved checksum-matched custom Momentum+single LabMate FAP with recovery/backup plan, safe known-good 125 kHz LF RFID test setup; no unsafe GPIO hookups | READ TIM1/CAPTURE TIM2/DMA EMULATE/FIELD original-C host PASS #38902785963 / #38904967453 / #38908647175 / #38909551118 and emulation worker host #38908966404; **not RF/SD/device or global E11 PASS** | Once native software and operator-approved matched firmware gates are closed, safely test real RFID carrier/capture data, DMA emulation and field detection against known-good LF fixtures; native LFRFID BUSY with competing TIM1/TIM2/DMA2, safe STOP without touching foreign GPIO, infrared/Sub-GHz coexistence, field recovery and RAW recording integrity; preserve old SD files, capture exact logs and checksum provenance | **DEFERRED / HARDWARE PENDING**; software BUSY caller migration and full native-service integration remain separate OPEN blockers |
| HW-10 | E11 native Sub-GHz RX/TX, CC1101 G0 PA1, optional PA7/PB3 mirror, TIM2 and DMA2 contention | User-approved matched custom Momentum/FAP with checksum + recovery, safe 3.3V fixture, SDR/known-good legal RF reception source; permitted region/frequency, suitable receiver to confirm TX without unlawful emissions | Actual Sub-GHz RX HAL/allocator C #38911157761, native RX app BUSY #38911453319, native TX HAL/allocator C #38912471437 host PASS; **NO DEVICE OR RF TEST** | Verify denied RX/TX has no foreign TIM2/DMA/IRQ/GPIO writes with concurrent LabMate Counter, RFID/IR, stop/restart after release, CC1101 PA1 vs external PB3 mapping, optional PA7/PB3 mirror, frequency/decoding/legally permitted emissions, hopper STOP/BACK, raw logs and graceful recovery; do not flash without approval | **DEFERRED / HARDWARE PENDING**; full firmware gate and all native client/EXTI coverage separate OPEN blockers |
| HW-11 | E11 native 1-Wire iButton PB14+EXTI14 callback coexistence | Known-safe iButton contact/logic instrumentation (3.3V-safe), operator-approved matched custom Momentum and recovery plan | Exact compiled native OneWire callback/STOP/allocator host CI #38915550354 SUCCESS; not a hardware PASS | Confirm Dallas emulation and native iButton read/writer coexistence, prior callback not removed on denied START, PB14/EXTI14 with competing native inputs, STOP/BACK and no leaked callback after mode change; log firmware and FAP checksums | **DEFERRED / HARDWARE PENDING** |
| HW-12 | E11 NFC internal IRQ PA2/EXTI2 vs external PB2 callback and native NFC TIM1/TIM17 coexistence | Operator-approved matched full Momentum+LabMate recovery bundle, known-good NFC card/tag and safe GPIO instrument or competing approved EXTI2 fixture | Genuine native NFC PA2/EXTI2 callback, rollback and firmware allocator host #38916131290 PASS; no physical NFC/EXTI test | Validate NFC bootstrap, low-power suspend/resume, card detection, denied EXTI2 before GPIO writes, no foreign callback removal after STOP, NFC timer and RFID/iButton/CC1101 coexistence, confirm preserved STOP/BACK; log firmware commit/CRC/observations | **DEFERRED / HARDWARE PENDING** |
| HW-13 | E11 native serial expansion USART1 PB7/EXTI7 and LPUART1 PC0/EXTI0 | Approved full Momentum/one LabMate FAP recovery, safe UART module and logic capture at 3.3V, validated expansion fixture | Genuine native SerialControl queue/ISR C + allocator host [#38917845230](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38917845230) PASS; **no physical serial, expansion, firmware flash or GPIO device test** | Exercise both native expansion RX paths with held LabMate USART1 and Monitor/I²C PC0, denied START with foreign callback, exact STOP/restart, logging/serial client handoff, unplug/replug, STOP/BACK and saved data preservation; compare matched firmware/FAP provenance | **DEFERRED / HARDWARE PENDING** |
| QA-01 | **Microsoft Excel CSV compatibility and analysis** | Access to Microsoft Excel on a compatible computer (can be later; no paid license is required now) | LabMate CSV generation, old/new History and **LibreOffice Calc CSV import PASS** | Open a real LabMate CSV in Microsoft Excel; verify 9 columns/headers, delimiters, decimal numbers, units and non-empty / invalid-data rows; check basic filtering or chart analysis | **NOT TESTED — deferred until Excel is available** |

## Evidence entry template

- **ID / test:** 
- **Date / firmware / exact LabMate commit + FAP SHA256:** 
- **Equipment + electrical conditions:** 
- **Procedure and raw readings/screenshots:** 
- **Result:** PASS / FAIL / SKIP / NOT TESTED
- **Limitations or follow-up issue:** 

## v1.7 release decision rules

The missing scope/physical-contact equipment must be disclosed in
v1.7 Stable release notes. A Stable release may claim **functionally
tested on internal 3.3 V loopback**, but must **not** claim independent
instrument-grade calibration or verified mechanical-contact metrics.

**Excel availability note:** Excel software is not available in the current
operator environment and may require a paid license. Do not purchase it
solely for release QA; defer this test until legal access is available.
LibreOffice Calc import is evidence of general CSV readability, not proof
of Microsoft Excel compatibility.

These deferred checks are not silently treated as PASS. A newly discovered
functional/safety failure remains a release blocker until corrected and
retested. Reserve destructive SD fault-injection for spare test media.
Never connect unknown/5 V/mains/automotive sources directly to Flipper GPIO.
