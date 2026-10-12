# LabMate v1.7 Stable

> **Documentation maintenance notice:** These clarifications are on the
> default branch after the v1.7 Stable release. The already published
> `v1.7` tag/FAP/release assets are unchanged. This is not a new
> version or new binary.

**Flipper Zero / Momentum Firmware — 3.3 V digital signal diagnostics.**

This is the first **v1.7 Stable** release following the published v1.7 RC1 pre-release. Published v1.6.1 Stable and v1.7 RC1 remain available and unchanged. Install only with compatible Momentum Firmware SDK/API. This external `labmate.fap` does not update device firmware.

## New in v1.7

- **PWM Studio — PA7/TIM1:** 15 frequency presets, duty cycle adjustable from 5% through 95% (5% increments), and STOP-only custom 1–50,000 Hz frequency editor. PWM can keep running while moving through the app's menu, but stops on full app exit.
- **Event Counter — PB3/TIM2:** hardware counting of real rising edges with RUN, STOP, RESET, elapsed time and saturating 64-bit count.
- **Button Analyzer — PC1:** clean digital contact OPEN/CLOSED, presses/releases, selectable 5/10/20/50 ms debounce, and bounce, settle and hold readouts.
- **Threshold Alerts:** visual threshold ARM, latch, ACK and OFF for frequency, pulse duty, event count and button settle.
- **Better UI:** MEASURE, OUTPUT, RECORDS and INFO navigation, 11 instruments, 13-page About field guide and revised monochrome layouts on 128×64.
- **Data Logger / Log History:** 1-second CSV records from Frequency LOW PC1, Frequency HIGH PB3 and Pulse PC1; open recent and earlier compatible CSV logs; delete only a selected CSV following explicit confirmation. Deletion is irreversible; BACK cancels.
- **Profiles:** three stored preset slots, explicit SAVE/OVERWRITE/DELETE confirmation with BACK cancellation; blocked operations while PWM or capture resources run. LOAD never starts PWM and does not change existing saved files unless explicitly saved.
- **Internal quality:** measurement/statistics update logic, CSV sample formatting and Threshold sample validity handling split into independent modules. Timer, GPIO and EXTI resource ownership safeguards retained.

## Verification

The refactored Stable Candidate FAP (CI [38191036835](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38191036835), SHA256 `94883B517D526EAA0F64E2AEAC89F89D181F85FD4F3ABB9056F3EEC2B68123E0`) completed **36/36 user-reported Flipper checks** across tests 7A–7F: PWM/Pulse, Frequency LOW/HIGH, Event Counter, Button with clean digital input, Thresholds, CSV Logger/History, Profiles protections, navigation and data persistence. Test 7B included screenshot-reviewed PWM/Pulse readings at 100 Hz with 5/50/95% duty.

The separately built, final **`v1.7`-labeled** FAP (CI [38234204272](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38234204272), SHA256 `5A7CB0EAE601EEAC8856790211C4D2831A9198C31853631E1DAF0308CE724335`) passed **4/4 user-reported on-device smoke checks**: LCD/About version, startup/STOP, preserved S1 and CSV records, and 100 Hz / 50% PWM-to-PC1 Pulse with STOP after exit. A later packaging/installer-only CI reproduced the same exact FAP SHA256 and completed 2/2 PASS; all release publishing steps enforce that checksum.

These are **functional tests using the Flipper's own 3.3 V loopback**, not independent instrument calibration.

## Known limitations and deferred hardware testing

- **Not independently calibrated:** no oscilloscope/reference validation of PA7 frequency, duty, voltage levels or electrical OFF state.
- **Mechanical button not tested:** only clean digital simulation was available, so mechanical bounce/settle measurements are not independently verified.
- **Storage fault scenarios not exhaustively tested:** full, disconnected or corrupted microSD, interruption during writes, and extended continuous sessions remain deferred.
- **Microsoft Excel CSV import/analysis: NOT TESTED.** LabMate CSV import was demonstrated in LibreOffice Calc, but actual Microsoft Excel was unavailable in the test environment. Excel compatibility is tracked as deferred QA-01; no paid software purchase is required for this maintenance.
- **Additional hardware and edge cases:** external safe reference signals, all pins and every extreme PWM frequency/duty combination remain untested.
- **Profiles format:** saved profiles do not include CUSTOM PWM frequency, duty cycle or Threshold settings; CUSTOM SAVE is intentionally refused and a preset LOAD resets duty to 50%. LOAD never starts PWM.
- Back up important CSV and profile data; a confirmed History CSV DELETE is irreversible.

See [deferred test register](docs/DEFERRED_HARDWARE_TESTS.md) and [Stable Candidate device evidence](docs/V1_7_STABLE_CANDIDATE.md).

## Installation

Download `labmate.fap` and `SHA256SUMS.txt` from this **v1.7 Stable** release; verify SHA256 before installing to `/ext/apps/Tools/labmate.fap` on a compatible Momentum Firmware device. The official [PowerShell USB installer](scripts/install-v17-from-github.ps1) with `-Channel Stable` validates official tag/release metadata and FAP SHA256; see [installation guide](docs/V1_7_INSTALL_GUIDE.md). It does not remove existing CSV/profile data.

**GPIO safety:** use only known **3.3 V-compatible** digital signals, STOP PWM before moving connections, and never apply 5 V, mains, automotive or unknown signals directly to Flipper GPIO.
