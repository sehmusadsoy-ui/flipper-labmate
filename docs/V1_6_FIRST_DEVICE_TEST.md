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
