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
