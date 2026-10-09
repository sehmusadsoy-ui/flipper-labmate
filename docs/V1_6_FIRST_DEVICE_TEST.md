# LabMate v1.6-dev — First physical Flipper test gate

**Status:** Ready for the **first device test**; NOT tested on hardware yet.  
**Candidate source commit:** `a69c231e631b446db33c28c36f7aaf7ea1d45725`  
**Momentum dev SDK CI:** [successful build and artifact](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/37992919485)  
**Device currently on:** [v1.5 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5) (do not claim v1.6 installed).  
**Test order:** smoke test **now**, before wiring up profile persistence to microSD.

## Why test now?

The v1.6 development branch has already changed the navigation hierarchy,
extracted every Canvas renderer, introduced capture ownership and pinned
interrupt input tracking, and added generator PA7 reservation. Host-native C
tests and an SDK compile cannot prove these behaviors on real Flipper hardware.
Adding new profile SD writes before checking them would make fault diagnosis
harder. This gate is deliberately inserted **before** profile file I/O.

## Preparation and safe install

1. Keep the currently working v1.5 Stable release link available for rollback:
   https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5
2. Open the successful Actions run above, download the artifact named
   `labmate-v1.6-dev-fap`, and **extract the ZIP**. It includes
   `labmate-v1.6-dev.fap` and `SHA256SUMS.txt`. Signing in to GitHub may
   be necessary to access Actions artifacts. The checksum in that archive
   authenticates the extracted file against the build archive, not the
   identity of the uploader; use the trusted repository/run.
3. Inspect the pinned source of `scripts/install-labmate.ps1` at
   https://github.com/sehmusadsoy-ui/flipper-labmate/blob/a69c231e631b446db33c28c36f7aaf7ea1d45725/scripts/install-labmate.ps1
   and run it on Windows from a matching local `v1.6-dev` checkout, for
   example:

   ```powershell
   cd "$env:USERPROFILE\flipper-labmate"
   .\scripts\install-labmate.ps1 -FapPath "C:\PATH\TO\labmate-v1.6-dev.fap" -VerifyOnly
   if ($LASTEXITCODE -ne 0) { throw "FAP checksum verification failed" }
   .\scripts\install-labmate.ps1 -FapPath "C:\PATH\TO\labmate-v1.6-dev.fap" -Port COM7
   if ($LASTEXITCODE -ne 0) { throw "v1.6-dev install was not confirmed" }
   ```

   Replace the two placeholders with the actual checkout/FAP paths. An
   alternative is to download the script from the exact pinned commit above
   to a local file and run it after inspection. Momentum Firmware is expected
   at `$HOME\Momentum-Firmware`; otherwise pass `-FirmwareRoot`.
   The installer uses one destination:
   `/ext/apps/Tools/labmate.fap`. Installing v1.6-dev will replace the
   v1.5 FAP at that path but does not intentionally delete
   `/ext/apps_data/labmate/` CSV files or flash the firmware.
4. Disconnect all external signal/wiring connections for the first **menu
   smoke test**. Leave the normal microSD card inserted. Do not remove the
   card while Logger or History is accessing it. Only use known
   **3.3 V-compatible** test signals during later signal testing.

Do not treat an installer exit code of zero as an on-device regression pass.
Actually inspect the Flipper screen and send results.

## Gate A: navigation / screen smoke (no external wiring; ~10–15 min)

| ID | Action | Expected result |
| --- | --- | --- |
| A1 | Launch LabMate | Main title shows `v1.6d`, not `v1.5` |
| A2 | Root UP/DOWN through all items | `MEASURE`, `OUTPUT`, `RECORDS`, `INFO`; list wraps, no blank/invisible selected row |
| A3 | Open MEASURE | Three tools: GPIO Monitor / Frequency Meter / Pulse Analyzer; all visible |
| A4 | Open each measurement tool and press BACK | No crash or hang; returns to MEASURE |
| A5 | Open OUTPUT → Signal Generator, leave RUN off, BACK | Returns to OUTPUT; no unintended PWM activation |
| A6 | Open RECORDS | Data Logger and Log History open and return normally; previous saved logs remain visible |
| A7 | Open INFO → About | Displays `v1.6d` and `3.3V GPIO ONLY` without clipping |
| A8 | BACK from child group, then BACK from root | Returns to root then exits normally |

**Stop criterion:** any freeze, crash, unexpected GPIO activity, cropped
screen text or missing tool is a FAIL. Do not proceed with Signal/Logger
testing; capture the exact path/actions and the screen/terminal result.
A passing Gate A is only navigation/display success.

## Gate B: capture / resource handoff (with safe known 3.3 V test setup; ~15–20 min)

| ID | Action | Expected result |
| --- | --- | --- |
| B1 | GPIO Monitor select available input | Input/HOLD/LIVE and edge display work as on v1.5 |
| B2 | Frequency HIGH PB3 → LOW PC1 → HIGH | No stale IRQ/TIM2 state, MIN/MAX behaves as v1.5 |
| B3 | Pulse PC0, PC1, PB2, PA4 | Correct HIGH/LOW/PERIOD/DUTY and MIN/MAX under the user's existing validated signal setup |
| B4 | Pulse HOLD → LIVE repeatedly, UP/DOWN, BACK | No frozen menu, duplicate callback or loss of control |
| B5 | Signal Generator PA7 RUN, change preset, BACK | PWM remains intentionally running in background |
| B6 | With PWM running: GPIO Monitor navigate past PA7 | `PA7 BUSY`, PA7 is skipped; PWM must **not** be silently disrupted |
| B7 | Return to Generator, STOP, revisit GPIO Monitor | PA7 becomes selectable again; app EXIT stops generator |

A real waveform measurement of B5/B6 requires an appropriate known-good,
3.3 V-compatible test instrument/setup. Do **not** connect a 5 V, unknown or
mains signal to Flipper GPIO.

## Gate C: Data Logger / history regressions (normal microSD; ~10–15 min)

| ID | Action | Expected result |
| --- | --- | --- |
| C1 | Start LOW PC1 logging then STOP | New CSV uses a previously unused sequential filename; records are readable |
| C2 | Repeat with HIGH PB3 and PULSE PC1 | Correct mode labels, valid flags and numeric data; no overwrite |
| C3 | Logging BACK and USB connection | App UI responsive; file is synced and closed |
| C4 | Log History inspect existing and new records | Correct rows/mode/duration, read-only; older v1.5 records preserved |
| C5 | Leave screen then exit/reopen LabMate | No crash; files remain readable |

This **does not** test actual microSD failure handling, a full card,
unmounted/corrupt media, blocked I/O or unexpected power loss. Those
remain declared untested cases, not prerequisites we can assume passed.

## Reporting and release gate

Record each test as `PASS`, `FAIL` or `NOT RUN`; for any failure include
the tool/menu path, sequence, Flipper screen message and relevant CLI log.
Start by reporting **A1–A8** only. Then we can decide whether to proceed to
B/C or first fix something on `v1.6-dev`.

After Gates A–C are reviewed:
- If behavior regresses, fix on `v1.6-dev` and rerun appropriate gates.
- If they pass, proceed with dual-file profile persistence and UI, which
  will require an **additional** device test. Do not label v1.6 Stable yet.
- Revert to v1.5 Stable if the development FAP is unstable:
  download `labmate-v1.5.fap` from the existing GitHub v1.5 release,
  verify SHA256 and install it to the same
  `/ext/apps/Tools/labmate.fap` via the previously successful Momentum
  `runfap.py` method. This restores the app binary; it does not reset CSVs.

**Important:** This file documents a planned test procedure, not a claim
that any device test took place.

## First physical test report — user-reported (2026-10-10)

**Firmware candidate under test:** development FAP from CI
[37992919485](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/37992919485),
code SHA `a69c231`; `v1.6d` was installed and launched on the Flipper via
Momentum runfap.py, COM7. This evidence was supplied by the device operator,
not collected by GitHub CI or by the development assistant directly.

| Test | User-reported result | Scope |
| --- | --- | --- |
| A1–A8 | PASS (8/8) | Grouped navigation, tool entry/exit, labels, display |
| B1 | PASS | GPIO monitor |
| B2 | PASS | Frequency Meter mode changes and functional checks |
| B3 | PASS | Pulse input selection, statistics/measurement UI |
| B4 | PASS | Pulse HOLD/LIVE and re-entry |
| B5 | PASS | Generator remains RUN after BACK |
| B6 | PASS | PWM PA7 software reservation/skip and release |
| C1–C3 | PASS | Logger PC1 LOW, PB3 HIGH, Pulse PC1 recording |
| C4–C5 | PASS | History new/old files and persistence across restart |

**Measurement accuracy finding, OPEN / HIGH PRIORITY:** The operator also
reports that while the Signal Generator is set to **1 Hz**, a frequency
measurement displayed approximately **10 Hz**. It is currently **unknown**
whether the affected input was Frequency HIGH PB3 or LOW PC1 (or another
measurement view), what values persisted after settling, and whether
physical 1 Hz timing was independently verified. Therefore none of these
PASS reports constitutes an unconditional 1 Hz frequency accuracy pass.

### Source-level leading hypothesis (not confirmed on hardware)

In `labmate.c`, the TIM2/PB3 HIGH branch samples a counter at
`SystemCoreClock / 10U`, approximately **100 ms**, and computes frequency
from `delta_count / elapsed_cycles` whenever `delta_count > 0`.
One rising edge detected inside a roughly 100 ms sample is therefore
reported around **10 Hz**, even if the source truly produces only one rising
edge per second. This is an inherent small-count / short-gate bias and is
consistent with the reported 10x symptom **IF the reading was HIGH PB3**.
The LOW PC1 branch timestamps successive rising edges instead and has a
different measurement path. Momentum's TIM1/PA7 PWM HAL takes the
configured frequency in Hz; no hardware output verification is claimed.

**Next diagnosis (before changing firmware):** Confirm which label
appeared on the measuring screen: `HIGH PB3` or `LOW PC1`, and the exact
display reading (LIVE value vs MIN/MAX). With an existing approved safe
3.3 V-compatible test setup, compare the reading after several seconds
in LOW PC1 and HIGH PB3 modes, without altering the current v1.6d binary.
STOP PWM before making any changes to the test setup; do not use 5 V or
unknown signals. If HIGH PB3 is affected, design and host-test low-count
gating or low-rate validity policy without regressing high-frequency
measurements. If LOW PC1 is affected, inspect EXTI edge/timestamp handling
instead of applying a HIGH-specific fix.

**Release decision:** Keep v1.6-dev unpromoted and profile SD persistence
deferred until the 1 Hz discrepancy has been diagnosed and retested on
device. Do NOT silently change a validated v1.5 Stable artifact.

## Confirmed HIGH PB3 discrepancy and corrective development work

The device operator confirmed that the unexpected **10 Hz** value appeared
specifically in **Frequency Meter / HIGH PB3**, while the generator was
configured to **1 Hz**. Source inspection confirmed that the old HIGH path
computed `delta_count / 0.1-second` even for one counted edge. One edge
observed in a 100 ms window corresponds to an instantaneous 10 Hz estimate,
which is not a reliable long-term 1 Hz reading.

The fix changes TIM2/PB3 sampling to two independent clocks:
- **100 ms hardware polls**, retaining high-speed edge observation and
  signal-loss tracking.
- **Adaptive frequency estimation:** publish on >=10 edges for prompt
  high-rate response, or after a maximum ~2 s gate for slow signals,
  provided at least two edges were counted. An empty or single-edge
  two-second gate produces no new frequency or MIN/MAX value.
- HOLD to LIVE, capture release and fresh mode entry reset both clocks.
  No GPIO/EXTI/TIM2 acquisition API is changed.

New portable C tests exercise 1 Hz sampled at 100 ms, 2/10/100/1000/50000 Hz
counter windows, isolated noise edges, no-signal gates and TIM2/DWT counter
wraparound. These are **host simulations, not a Flipper accuracy
calibration**. At low frequencies in HIGH mode, measurement latency is about
2 seconds and count/time quantization persists; LOW PC1 remains preferable
for precise very slow signals. Signal Generator PA7 TIM1 output has NOT been
independently verified at the pin by external timing equipment.

The corrected FAP must be tested on the same Flipper, with the same known
3.3 V-compatible setup, **before** the physical 1 Hz finding can be closed.
The physical operator is required to reinstall the newly built FAP.

## PowerShell GitHub install without manual ZIP download

The development workflow packages the app with the consistent filename
labmate.fap (GitHub Actions artifact: labmate), still installing to
/ext/apps/Tools/labmate.fap. Run scripts/install-from-github.ps1 in PowerShell
on Windows after one-time GitHub CLI (gh) installation and authentication.
The script finds the most recent successful development run, automatically
retrieves the artifact into a temporary folder, checks SHA256, invokes
Momentum runfap.py via COM7 by default and cleans up temporary files.
Stable v1.5, Momentum firmware and existing CSV records are not modified.

## Device operator follow-up: HIGH PB3 1/2/10 Hz (2026-10-10)

Following the first two-second counter-window fix, the user reported
the following **MIN/MAX** readings on real hardware with Signal Generator
set to each preset and Frequency Meter in **HIGH PB3**:

| Generator preset | Recorded MIN (Hz) | Recorded MAX (Hz) |
| --- | ---: | ---: |
| 1 Hz | 0.95 | 1.45 |
| 2 Hz | 1.91 | 2.39 |
| 10 Hz | 9.34 | 10.70 |

These user-reported extrema are not a steady-state instantaneous sample,
nor independent oscilloscope calibration. The prior tenfold 1 Hz -> 10 Hz
artefact appears eliminated, but the maximum errors are still +45%,
+19.5%, and +7%, respectively. Therefore HIGH PB3 frequency *accuracy*
is still pending hardware verification; the 1 Hz result is not a full PASS.

**Second correction:** The remaining source-level issue was terminating
a multi-second counting window at an arbitrary 100 ms polling boundary,
which can add/remove one entire counted edge. At 1 Hz, a two-second
window containing three edges reports approximately 1.5 Hz. The new
edge-aligned algorithm starts a window on a detected TIM2 count increment
and publishes only at another detected increment. It waits for 32 counted
edges (fast rates), or at least 3 seconds with >=2 counted edges (slow
rates). It re-arms on HOLD/LIVE and after an input silence >3 seconds.
No PWM output, pin ownership, logger CSV or v1.5 Stable code changes.

**Expected trade-off:** at ~1 Hz the display takes about 3–4 seconds
to generate a fresh value; at ~2 Hz about 3–4 seconds; at ~10 Hz about
3–4 seconds until 32 additional edges have been observed. This is a
deliberate stability-over-latency choice for the HIGH PB3 mode. The
100 ms hardware poll remains, and very fast signals can still update
on successive polls. Time quantization from 100 ms polling remains;
physical retesting is essential.

**Next physical retest:** using the already validated 3.3 V-compatible
setup, re-check HIGH PB3 1, 2, and 10 Hz. Wait long enough to see new
readings and distinguish LIVE values from lifetime MIN/MAX extrema,
resetting MIN/MAX before each preset/mode. Stop PWM before changing any
connections. No manual ZIP downloads: use the PowerShell GitHub installer.

## Third physical retest: HIGH PB3 stability (user-reported, 2026-10-10)

**FAP build:** GitHub Actions
[37999740904](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/37999740904),
source SHA `f2edde8dbd31022daa4ca182e48855fac2779422`.
This is device-operator evidence, not an independent oscilloscope
calibration or a GitHub CI hardware test.

| Generator preset | LIVE (Hz) | MIN (Hz) | MAX (Hz) | Maximum absolute relative error |
| --- | ---: | ---: | ---: | ---: |
| 1 Hz | 0.99 | 0.97 | 1.02 | 3.0% |
| 2 Hz | 1.99 | 1.96 | 2.03 | 2.0% |
| 10 Hz | operator reports "very variable" | 9.83 | 10.29 | 2.9% |

**Assessment:** The original catastrophic 1 Hz -> 10 Hz result
and the subsequent 1 Hz -> ~1.5 Hz phase-biased peak were no longer
observed. The first two nominal frequencies achieved readings within
approximately 3% of the programmed source, a **functional device retest
PASS** for their intended measurement modes. The 10 Hz range has
0.46 Hz peak-to-peak spread, approximately 4.6% of nominal; all reported
extrema are within 2.9% of nominal, but LIVE was described as very
variable with no single representative number provided, so 10 Hz
*stability* remains **OBSERVE / NEEDS FOLLOW-UP**, not a numerical
instantaneous-reading PASS.

**Technical hypothesis:** HIGH PB3 uses a ~100 ms software poll of
the TIM2 rising-edge counter. The edge-aligned estimator still anchors
timestamps at the poll rather than at the exact hardware edge time.
Up to roughly one poll interval at each gate boundary contributes
quantization jitter, which can be relevant for ~3 s estimation gates
(around a few percent). This is a hypothesis based on source and readings,
not a proven external electrical or oscillator defect.

**Decision:** Preserve this known-good correction and avoid further
frequency algorithm changes solely from MIN/MAX spread. Verify
repeatability and LIVE behavior at 10 Hz before attempting further
smoothing; adding an estimator or median should not conceal real signal
changes or degrade high-frequency counting. The user prefers
one-command GitHub CLI + PowerShell installation and the consistent
`labmate.fap` filename.

**Release discipline:** Keep `main` / v1.5 Stable untouched. The
frequency accuracy evidence compares Signal Generator with the same
Flipper's Frequency Meter, and does not independently calibrate TIM1 PWM
or TIM2 timing. Physical signal output calibration and broader accuracy
requirements should remain explicitly separate from functional smoke
tests.

## Fourth operator confirmation — 10 Hz LIVE range (2026-10-10)

The device operator explicitly confirmed that, with Signal Generator at
10 Hz and Frequency Meter in HIGH PB3 mode, the LIVE readout varies
**within the previously reported 9.83–10.29 Hz MIN/MAX limits**,
rather than making larger unexpected excursions.

**Disposition:** The earlier 1 Hz -> 10 Hz false-reading bug is
**RESOLVED for functional self-measurement testing** on the Flipper.
Operator-reported HIGH PB3 1/2/10 Hz readings all fall within 3%
of the nominal Signal Generator settings (based on the observed ranges).
The 10 Hz LIVE variability is bounded and no longer blocks moving on
to saved-profile development. Keep the 100 ms TIM2 polling quantization
as a documented accuracy/UX limitation; do not alter the now-tested
counter algorithm for cosmetic smoothing without explicit new tests.

**Scope limitation:** Generator and meter share the same Flipper; there
has been **no independent calibrated frequency reference** or
oscilloscope timing verification. This is a functional regression pass,
not a metrology guarantee. Keep `main` / Stable `v1.5` untouched.
No new Flipper installation is required from this documentation-only
update.

## Next on-device gate: three-slot Profiles (NOT RUN yet)

The v1.6-dev code now includes a Records > Profiles screen and a
redundant A/B microSD store. After a successful GitHub CI build, use
the existing one-step GitHub CLI + PowerShell installer (FAP name
`labmate.fap`), not manual ZIP extraction.

1. **P1:** Enter Records > Profiles with microSD inserted. The three
   slots show EMPTY on first use, or prior saved entries on a repeat.
   No GPIO wiring is needed.
2. **P2:** Choose S1, toggle SAVE, press OK and confirm with OK.
   SAVED must appear; a second SAVE may overwrite that same slot only
   after confirmation. BACK on confirmation must cancel.
3. **P3:** Change a Generator frequency preset while output is
   STOP. Select LOAD for S1 and press OK. LOADED must appear; opening
   Signal Generator must show the stored preset with output STOP.
   There must be no unexpected PWM output activation.
4. **P4:** Repeat S2/S3 with distinct frequency presets. Exit app,
   restart, and verify all slots and their settings persist. Confirm
   existing History CSV files remain present and readable.
5. **P5:** With Signal Generator RUN, try to LOAD a saved profile.
   The screen must display STOP PWM and refuse to alter parameters.
   Return to Generator, STOP it, and load again.
6. **P6:** If a damaged/inaccessible file is encountered naturally,
   capture the error screen; **do not remove the microSD during a
   write or deliberately corrupt data on-device**.

Capture PASS/FAIL/NOT RUN for each item. Device operator confirmed
P1/P2 (three slots and SAVE) PASS and P3/P4 (LOAD and persistence)
PASS. P5 (generator-active LOAD refusal) and P6 (naturally encountered
storage errors) remain NOT RUN. All results are user-reported, not
independent physical testing by the assistant.

## P7 profile deletion gate (NOT RUN)

Once P3–P6 are complete with the known-good three-slot firmware, install
a successful new CI build containing explicit DELETE support via the
usual PowerShell GitHub CLI installer (no manual FAP download). No GPIO
wires are needed for this test.

1. Pick a saved noncritical slot, e.g. S2; use LEFT/RIGHT to select DELETE.
2. Press OK once, then BACK. Slot MUST remain populated (cancel path).
3. Press OK twice and wait for DELETED; slot MUST show EMPTY.
4. Exit and restart LabMate, then verify the slot stays EMPTY while other
   saved slots and existing Log History CSV files remain available.
5. Selecting DELETE on the empty slot should display EMPTY without a
   microSD write.
6. Do not corrupt the SD card, remove it during writes, or delete any
   binary file manually to simulate failure. No hardware safety test
   beyond user-reported observation is claimed.

## User-reported P7 DELETE device pass (2026-10-10)

Operator reported `P7-A=PASS`, `P7-B=PASS`, `P7-C=PASS`
on real Flipper Zero running the development DELETE-capable FAP built
from commit `4eaf8054d354fb7725617b72df25c0a974daf214`
(GitHub Actions `38001774685`). Observed outcomes:

- **P7-A PASS:** Selecting DELETE and pressing BACK at the confirmation
  stage leaves the profile intact.
- **P7-B PASS:** Confirming DELETE with OK twice clears the selected
  S2 slot and reports a successful deletion.
- **P7-C PASS:** After exiting and reopening LabMate, the S2 slot stays
  EMPTY, while S1 and existing CSV Log History entries remain intact.

This is evidence for functional slot deletion and persistence, not proof
of secure erasure of the older redundant binary copy. P7 empty-slot
DELETE no-write behavior was not individually tested by the operator.
No changes to firmware `main`, Stable `v1.5`, or the now-tested FAP
are made by this record-only commit.

## User-reported P5 profile LOAD safety pass (2026-10-10)

After P7's three functional PASS results, the device operator was asked
to verify all three P5 checks and replied **"evet başarılı"** (yes,
successful), confirming the requested test sequence succeeded:

- **P5-A PASS:** Signal Generator left RUN in the background; trying
  to LOAD saved S1 showed `STOP PWM` and did not apply the profile.
- **P5-B PASS:** Operator returned to Generator and explicitly STOPped
  it; repeating LOAD showed `LOADED`.
- **P5-C PASS:** After LOAD, Generator remained STOP, with no
  automatic output activation.

These are user-reported functional/UI observations on the real Flipper,
not an independent electrical PA7 measurement. P1, P2, P3, P4,
P5-A/B/C and P7-A/B/C are now reported PASS. P6 (naturally encountered
microSD read/corruption cases), empty-slot DELETE/no-write, and broader
hardware calibration are not reported as tested. No intentional SD
corruption, unsafe electrical tests, or changes to stable v1.5 are
required. The current profile implementation is a viable **v1.6-dev
device-tested feature candidate**, not automatically promoted to main.

## H1-H3 HIGH PB3 kHz device observations (user-reported, 2026-10-10)

The operator tested the active v1.6-dev firmware on the real Flipper
with the built-in Signal Generator and Frequency Meter set to HIGH PB3.
Input units in the message were abbreviated; values below interpret
LIVE as kHz and the MIN/MAX fields per the actual LCD format.

| Test | Generator | Reported LIVE | Reported MIN | Reported MAX |
| --- | --- | --- | --- | --- |
| H1 | 1 kHz | 1.00 kHz | 999.9 Hz | 1.000 kHz |
| H2 | 5 kHz | 4.99 kHz | 4.999 kHz | 5.000 kHz |
| H3 | 10 kHz | 9.99 kHz | 9.991 kHz | 10.00 kHz |

For the reported MIN/MAX, the greatest deviation from the generator
setting is 0.01% at H1, 0.02% at H2, and 0.09% at H3. These three
**functional self-test points PASS** on the device, but the generator
and meter share the same Flipper reference; this is NOT independent
frequency calibration and cannot establish external absolute accuracy.

### LCD decimal precision, not independent LIVE-vs-MIN error

The frequency display implementation in `labmate_ui_screens.c`
formats high-frequency **LIVE** as `%lu.%02lu kHz` (two decimal places,
truncated), while the compact MIN/MAX formatter displays
`%lu.%03luk` in the 1–9.999 kHz range. For example, a single
underlying reading of 4.999 kHz is printed as `4.99 kHz` in LIVE
but `4.999k` in MIN. Similarly, LIVE 9.99 vs MIN 9.991 at H3
is an intentional formatting-precision difference, not evidence of
a conflicting measurement. The near-10 kHz compact formatter changes
its precision at 10 kHz. No estimator or PWM code was changed here.

**H4/H5 subsequently completed:** user-reported functional self-test
results are recorded below. No external calibrated measurement is implied.

## H4-H5 20/50 kHz device results (user-reported, 2026-10-10)

The operator reported real-device HIGH PB3 frequency observations
using the Flipper Signal Generator for the following additional test
points. Units were explicitly kHz:

| Test | Generator | LIVE | MIN | MAX | Largest deviation of stated extrema |
| --- | --- | --- | --- | --- | --- |
| H4 | 20 kHz | 20.00 kHz | 19.99 kHz | 20.00 kHz | 0.05% |
| H5 | 50 kHz | 50.00 kHz | 49.99 kHz | 50.00 kHz | 0.02% |

**H4 PASS / H5 PASS** for functional self-measurement on the physical
device. Together with the earlier user-reported H1-H3 passes (1, 5,
10 kHz), all **five discrete HIGH PB3 kHz test points** have passed.
This does not prove continuous performance at *every* frequency
between 1 and 50 kHz or above the tested range.

At these speeds the TIM2 hardware edge counter is used; the
frequency estimator was not modified. The generator and meter share
Flipper hardware/timing resources, so the comparison is not an
independent absolute-frequency calibration. The measured range,
display precision, and lack of an independent oscillator reference
must be documented in any future release summary.

**Outcome:** Treat the HIGH PB3 high-frequency regression on the
five tested presets as complete, retain the currently device-tested
estimation algorithm, and avoid unnecessary changes to TIM2/PA7.
Stable v1.5 / `main` remain untouched. No FAP reinstall required
for this documentation-only update.
