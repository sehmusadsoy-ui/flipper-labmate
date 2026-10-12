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
