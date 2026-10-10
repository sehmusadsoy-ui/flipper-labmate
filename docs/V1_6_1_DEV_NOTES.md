# LabMate v1.6.1 — Dev Refactor, Step 1

**Branch:** `v1.6.1-dev`, forked from `main`
`08133dba06bf5c18780081e00a87b6778c3a29ba`.
**Status:** isolated development build, NOT v1.6.1 Stable.
Existing v1.6 tag/release and v1.5 Stable are unchanged.

## Extraction

- Add `labmate_logger_codec.c/.h`: pure C functions to decode
  `log_0001.csv` ... `log_9999.csv` filenames and to format
  existing FREQ/PC1, FREQ/PB3 and PULSE/PC1 CSV records.
- Keep file opening/closing, timestamps, sampling cadence, UI mutex,
  error handling and GPIO capture in the existing app loop for now.
- Keep identical CSV layout, invalid sample encoding and decimal
  precision; current microSD storage paths remain unchanged.
- Host native C tests verify filename edge cases, CSV rows, small
  output buffer handling and invalid input.
- Device label: `v1.6.1d`; `application.fam` retains SDK-compatible
  external-app manifest version `1.6` while the dev FAP is tested.
- Workflow builds modular Momentum FAP, existing host tests, new
  logger format tests, SHA256 artifact and Windows mock installer.
- Dev-only `scripts/install-v161-dev.ps1` requires successful
  CI for the exact branch head and validates `labmate.fap` SHA256;
  the published Stable installer remains release-pinned to v1.6.

## Step 1 — real Flipper regression: PASS (operator report)

The operator installed exact CI FAP from run
[38045960606](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38045960606)
(commit `c593a3322f1ca6505d2b02d0305e597998b595b1`)
via the checksum-checked PowerShell installer and confirmed all seven
smoke/compatibility tests PASS:

- `v1.6.1d` displayed correctly.
- PC1 LOW, PB3 HIGH and PULSE PC1 CSV recording each PASS.
- Log History reads both older and newly created CSV files.
- Previously saved Profile S1 persisted.
- Signal Generator default remained STOP.

This is functional device validation, not external metrology calibration
or intentional corrupt/full-microSD fault injection.

## Step 2 — read-only History module extraction

- Move all four existing Log History storage methods from `labmate.c`
  into `labmate_history.c/.h`: scan, open, incremental read and close.
- Keep the same I/O order, SD error handling, mutex boundaries,
  record formatting and 256-byte read size. This move does not modify
  the content of any existing CSV.
- Share one `LABMATE_LOGGER_DIR` macro between Logger and History.
  Continue to use `/ext/apps_data/labmate` without any on-disk migration.
- Retain canvas drawing in `labmate_ui_screens.c`, the pure CSV
  codec in `labmate_logger_codec.c`, and GPIO/IRQ/PWM routines in core.
- Extend CI architecture guards to require one implementation for
  each History operation, read-only SD mode and unchanged path.

## Step 2 — real Flipper regression: PASS (operator report)

After GitHub Actions build
[38046508627](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38046508627)
reported SUCCESS, the operator installed its checksum-verified
`labmate.fap` over COM7 for exact commit
`a89729141ea89e767b024de9cfe8c3d1a9adb517`.
The following seven checks were reported **PASS**:

1. Existing CSV files open through Log History.
2. Newly created CSV files open through Log History.
3. History still works after exiting and relaunching LabMate.
4. Data Logger PC1 LOW records successfully.
5. Data Logger PB3 HIGH records successfully.
6. Data Logger PULSE PC1 records successfully.
7. Saved Profile S1 is intact; Signal Generator defaults to STOP.

This confirms the read-only History module extraction on the tested
device under the listed normal-operation scenarios. It does not
prove all microSD error-handling or power-loss cases.

## Step 3 — portable Pulse measurement mathematics

- Move period/duty calculation and the existing median-of-five
  statistics sorter into `labmate_pulse_math.c/.h`.
- Keep IRQ callbacks, HAL timer ownership, app-thread filtering
  windows, capture scheduling and screen rendering where they are.
- Keep the original 64-bit period arithmetic, integer rounding
  and 5-sample median selection unchanged.
- Add host-C regression tests for 0%, 25%, 50%, 75%, 100% duty,
  fractional rounding, out-of-range period, ties, and outliers.
- Guard source module boundaries and ensure Momentum SDK can compile
  the reorganized FAP.

## Step 3 — real Flipper regression: PASS (operator report)

For exact commit `e9ad287e332e8e5b680aad37a4ae78cb108d6819`
(GitHub Actions run [38046956822](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38046956822)),
the operator installed the SHA256-verified FAP over COM7 and reported
all seven real-device checks **PASS**:

1. Pulse Analyzer PC1 at 100 Hz: HIGH/LOW/PERIOD/DUTY correct.
2. Pulse Analyzer PC1 at 1 kHz: HIGH/LOW/PERIOD/DUTY correct.
3. Pulse STATS, MIN and MAX functional.
4. Pulse HOLD/LIVE switching functional.
5. All three Data Logger sources still write CSV.
6. Log History opens both previous and new CSV files.
7. Saved Profile S1 intact, Generator starts in STOP.

These are functional operator observations rather than independent
instrument calibration or long-duration/stress qualification.

## Step 4 — separate Logger SD lifecycle from acquisition

- Move existing `logger_stop`, `logger_init_next_file_index`
  and `logger_start` logic to `labmate_logger_storage.c/.h`.
- Preserve source ownership checks, SD status and error handling,
  `FSOM_CREATE_NEW`, monotonic file numbering, CSV header,
  sync, close and file path `/ext/apps_data/labmate`.
- Keep live capture and row scheduling in `labmate.c`; keep
  History separate and read-only, and UI drawing passive.
- Add source boundary assertions; run full Momentum SDK compile,
  host regression suite and Windows mock installer.

**Step 4 device tests completed; see operator report below.**
Only known 3.3 V GPIO-compatible signals are permitted.

## Step 4 — real Flipper regression: PASS (operator report)

The operator installed the checksum-verified FAP for exact commit
`62194ae2910cfda3d683d6c63e168a83881ca94c` from GitHub Actions
[38049466166](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38049466166)
over COM7. Installation reported SHA256 OK and successful app launch request.
The operator subsequently reported all seven physical tests **PASS**:

1. Data Logger PC1 LOW creates records.
2. Data Logger PB3 HIGH creates records.
3. Data Logger PULSE PC1 creates records.
4. New CSV file numbers advance without overwriting old files.
5. Log History opens both previous and new CSV files.
6. Logger STOP, app exit and relaunch work normally.
7. Profile S1 remains saved, and Signal Generator starts in STOP.

This validates normal-operation regression cases for the extracted logger
storage module. It does not establish power-failure recovery, malformed
microSD behavior, full-card handling or extended endurance qualification.

## Step 5 — proposed Frequency Meter pure-math extraction

Extract only SDK-independent PC1 period-to-millihertz calculation and
related filtering helpers after reviewing existing frequency sample
semantics. Preserve ISR, STM32 TIM2, EXTI, GPIO ownership, gate timing,
HOLD/LIVE, timeout and statistic scheduling until separately tested.
Require native regression tests and a successful Momentum SDK build,
then a fresh real-device frequency and Logger/Profile smoke test.
Do not modify v1.6 Stable, main or previously published release assets.

## Step 5 — real Flipper regression: PASS (operator report)

For exact commit `1e42b6a8c7f97473476f1f95f9d0c1fb70c53f55`,
GitHub Actions [38050554917](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38050554917)
completed successfully. The operator reported nine real-device checks **PASS**:

1. LOW PC1 frequency readings at 10 Hz.
2. LOW PC1 frequency readings at 100 Hz.
3. LOW PC1 frequency readings at 1 kHz.
4. HIGH PB3 frequency readings at 1 Hz and 10 Hz.
5. HIGH PB3 frequency readings at 1 kHz and 10 kHz.
6. Frequency HOLD/LIVE and MIN/MAX.
7. Pulse PC1 at 100 Hz and 1 kHz.
8. All three Data Logger sources and Log History.
9. Profile S1 persistence and Generator initial STOP.

These are functional on-device operator observations, not independent
metrology certification or prolonged stress qualification.

## Step 6 — resource ownership and cleanup (planned, not yet tested)

Current pure resource rules in `labmate_resource_policy.c/.h` already
restrict Pulse EXTI to PC0/PC1/PB2/PA4; prohibit monitor polling of PA7
while TIM1 PWM runs; and enforce an exclusive owner for LOW PC1 EXTI,
HIGH PB3 TIM2 and Pulse EXTI capture.

Next, strengthen the ownership/cleanup contract incrementally with
host tests for conflicting acquisitions, allowed capture transitions,
invalid EXTI line choices, background PWM pin reservation, STOP/exit
release and re-entry. Do not move hardware ISR callbacks, TIM setup or
EXTI cleanup wholesale in a single change. Verify each narrow code
change with native tests, Momentum CI and fresh physical-device tests.
Keep stable v1.6 and all existing CSV/Profile data unchanged.

## Step 6.1 — real Flipper regression: PASS (operator report)

For exact commit `948ed0a1b0ff5f87dc25fe1320bf58da639bc802`,
GitHub Actions [38051780686](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38051780686)
completed SUCCESS. The operator installed the checksum-verified FAP over COM7
and reported **9/9 PASS**: LOW-to-HIGH, HIGH-to-Pulse and Pulse-to-LOW
transitions without freezes; PA7 reserved while PWM RUN and selectable after
STOP; Frequency and Pulse HOLD/LIVE; tool exit/re-entry without freezes;
three Logger modes and History; Profile S1 preserved and Generator STOP at start.
This verifies these normal-use scenarios, not full hardware fault recovery.

## Step 6.2 — centralized capture owner release (development)

Centralize owner-release policy without moving HAL/EXTI/TIM2 teardown.
Each stop routine must first detach its actual active peripheral, then
release its matching software owner; mismatched release requests must not
clear ownership of a different capture. Add host-native tests. Perform
Momentum CI and a separate on-device regression before acceptance.

## Step 6.2 — physical device regression: PASS (operator report)

The operator installed exact commit `8dd53b43437f7c55d23424eae47241b3957980dd`
from successful GitHub Actions run
[38052489517](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38052489517).
PowerShell verified SHA256 and reported a successful single-FAP update via COM7.
The operator reported **10/10 PASS** for these real-device checks:

1. Frequency LOW PC1 to HIGH PB3 transition.
2. Frequency HIGH PB3 to Pulse PC1 transition.
3. Pulse PC1 to Frequency LOW PC1 transition.
4. Repeated tool switching without a freeze.
5. Frequency and Pulse HOLD/LIVE.
6. PA7 reserved during Generator RUN.
7. PA7 available after Generator STOP.
8. Application exit and relaunch.
9. All three Logger sources and Log History.
10. Profile S1 preserved and Generator initially STOP.

The tested capture-owner release refactor passed these normal-operation
regressions. Abnormal interruptions or low-level hardware faults remain untested.

## Step 6.3 — next engineering gate (planned)

Extend host-native resource lifecycle tests and review timer/EXTI cleanup
for all STOP and screen exit paths before changing additional HAL operations.
Keep the implementation incremental, retain the tested firmware semantics,
and require a new CI PASS plus distinct physical-device regression checks.

## Step 6.3 — physical regression: PARTIAL (operator report)

Exact commit `986b32c79a0e7debb9f83ade19520284de55352c` was installed
from GitHub Actions run `38052823891` with SHA256 OK over COM7.
The operator reported **9 PASS, 0 FAIL, 1 PENDING**:

- PASS: LOW PC1 -> HIGH PB3, HIGH PB3 -> Pulse PC1, Pulse PC1 -> LOW PC1.
- PASS: repeated switching without freeze, PA7 reserved during Generator RUN
  and selectable after STOP, exit/relaunch, three Logger modes and History,
  Profile S1 preservation and Generator initial STOP.
- PENDING: Frequency and Pulse HOLD/LIVE functional regression.

Step 6.3 is **not fully accepted** until HOLD/LIVE is separately tested.
No HAL/IRQ resource ownership implementation was changed in Step 6.3;
this commit extends host regression tests only.

## Step 6.3 — final operator result: PASS (10/10)

Follow-up on the same installed exact commit
`986b32c79a0e7debb9f83ade19520284de55352c`:
Frequency Meter HOLD/LIVE **PASS**, Pulse Analyzer HOLD/LIVE **PASS**.
Together with the previous nine passing checklist items, the full
Step 6.3 checklist is now **10/10 PASS**, with no reported failures.
This supersedes the earlier 9 PASS / 1 PENDING report, without
claiming additional stress or external calibration coverage.

## Step 6.4 — EXTI cleanup refactor plan

Consolidate EXTI trigger cleanup into one internal helper while preserving
LOW PC1's falling-edge-only pre-arm cleanup, Pulse's complete rising/falling
teardown, and their critical sections. Do not touch TIM2, PWM or IRQ callback
ordering. Require Momentum CI PASS and a separate on-device regression.

## Step 6.4 — real Flipper regression: PASS (operator report)

For exact commit `b7d4e2b4a29dd63b64803d9f477e579a37f44cd6`,
GitHub Actions [38055872768](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38055872768)
completed successfully. The operator reported **10/10 PASS**:

1. LOW PC1 -> Pulse PC1 -> LOW PC1 transition.
2. LOW PC1 1 kHz reading correct, without double counting.
3. Pulse PC1 100 Hz and 1 kHz readings correct.
4. Pulse -> HIGH PB3 -> Pulse transition without freeze.
5. Frequency and Pulse HOLD/LIVE.
6. Repeated tool entry/exit without freeze.
7. PA7 protected during Generator RUN and released after STOP.
8. All three Logger modes and Log History.
9. Profile S1 preserved; Generator initially STOP.
10. App exit and relaunch without problems.

This accepts the EXTI cleanup refactor for tested normal-operation cases,
not deliberately induced hardware faults or external metrology calibration.

## Step 6.5 — planned defensive cleanup validation

Review the shared capture teardown and add a pure, host-testable
predicate for whether every capture engine has released its active
flag. Apply it as a final ownership-reset guard after the existing stop
operations. Preserve the normal teardown order and TIM1/PA7 independence.
Require CI success and a new physical regression check before acceptance.

## Step 6.5 — real Flipper regression: PASS (operator report)

For exact commit `ddf7367070cf06f2d625991d1b0f3f8546da62e8`,
GitHub Actions [38056187365](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38056187365)
completed SUCCESS. The operator installed the build on the device and
reported **5/5 PASS**:

1. Frequency LOW -> HIGH -> Pulse switching without problems.
2. Frequency and Pulse HOLD/LIVE functional.
3. Generator RUN/STOP and PA7 protection.
4. Tool exit/re-entry and app relaunch without observed freeze.
5. All three Logger modes, History, Profile S1 and initial Generator STOP.

This completes Step 6.5's normal-operation acceptance checks. Software
state flags do not independently prove physical peripheral teardown under
all hardware faults.

## v1.6.1 consolidation and release gates

Stop subdividing the project into repetitive Step 6.x hardware cycles.
Target **two remaining grouped physical-device test sessions**, subject
to additional regression testing if a defect is discovered.

### Gate A — architecture and display integration

Review the modular measurement, UI/navigation, storage/profile and
resource policy boundaries; retain existing behavior and CSV/profile
format. Complete necessary small changes and automated host, architecture,
Momentum SDK and installer tests before one combined device session.
Test navigation, display bounds, measurement handoffs, HOLD/LIVE, PWM
ownership, logger/history and profile persistence. The communication
boundary may remain an extension point: UART/I2C implementation is out
of scope for v1.6.1.

### Gate B — release candidate validation

After Gate A passes, freeze the candidate commit, compile the exact
artifact, and perform one final device session: USB single-FAP
installation, startup/exit/relaunch, representative frequency/pulse
readings, Generator STOP and PA7 ownership, CSV/history compatibility,
saved profiles and extended ordinary-operation stability. Treat
abnormal SD/power-loss scenarios as unverified until explicitly tested.
Do not promote to Stable unless both gates pass. Keep main, the
published v1.6 release and historical tags untouched until a separate
release decision.

## Gate A — completed device integration checks: PASS (operator report)

Exact firmware commit `9c087b64504083e5f977544bc27cd9ce37840819`
passed GitHub Actions [38056474953](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38056474953).
The operator reported **8/8 PASS** in the combined device session:

1. MEASURE / OUTPUT / RECORDS / INFO grouped menus; all tools accessible.
2. Screen labels, selections and footer layout without observed overflow.
3. Frequency LOW/HIGH and Pulse, including HOLD/LIVE.
4. GPIO/EXTI transitions without observed freezes/collisions.
5. Generator RUN/STOP and PA7 reservation.
6. Three Logger sources, incremental CSV names and History.
7. Preserved Profile S1, SAVE/LOAD and Generator initially STOP.
8. Exit/relaunch and repeated tool switching without observed freezes.

Gate A is accepted for these normal-use scenarios; no external metrology,
interrupt fault injection, or long endurance guarantee is implied.

## Gate B — frozen release-candidate source and final acceptance checklist

**Candidate source SHA:** `9c087b64504083e5f977544bc27cd9ce37840819`.
This exact already-successful firmware run is the release-candidate binary;
this documentation-only commit must not be mistaken for a new FAP build.
Do not introduce further code changes before the final Gate B check.
The updater must validate the successful run's SHA and artifact checksum,
and install only `/ext/apps/Tools/labmate.fap` on COM7.

Final single-session checks: clean startup; LOW PC1 (100 Hz / 1 kHz),
HIGH PB3 (1 kHz / 10 kHz), Pulse PC1 (100 Hz / 1 kHz) readings; HOLD/LIVE;
LOW/HIGH/Pulse repeated transitions without freeze; Generator default STOP,
PA7 protection during RUN and release after STOP; all three Logger modes,
CSV sequence and old/new History; S1 SAVE/LOAD persistence after exit/restart;
all four group menus and screens; final exit/relaunch and sustained ordinary
use. Capture results separately as PASS/FAIL/PENDING; no automatic claim of
Stable promotion on CI alone. Keep `main`, v1.6 Stable and published tags
unchanged pending a separately authorized release decision.

## Gate B — release-candidate physical validation: PASS (operator report)

**Frozen source commit:** `9c087b64504083e5f977544bc27cd9ce37840819`.
GitHub Actions [38056474953](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38056474953)
completed SUCCESS for this exact firmware commit. The operator reports
**6/6 PASS** in the final device acceptance session:

1. LOW PC1 100 Hz / 1 kHz, HIGH PB3 1 kHz / 10 kHz and Pulse PC1 100 Hz / 1 kHz.
2. Frequency and Pulse HOLD/LIVE.
3. LOW/HIGH/Pulse switching without freeze; Generator RUN/STOP and PA7 protection.
4. All three Logger sources, sequential new CSV names and old/new Log History.
5. S1 SAVE/LOAD retained, four groups accessible and Generator initially STOP.
6. Several minutes of ordinary use, tool transitions, exit and relaunch without freeze.

**Gate A: 8/8 PASS. Gate B: 6/6 PASS.** The firmware candidate is
accepted for release preparation based on these user-reported tests.
This is not an independent precision calibration or long-duration
fault-injection qualification.

### Release preparation checklist (not yet published)

- [x] Freeze exact firmware source SHA and successful CI run.
- [x] Pass Gate A combined device regression.
- [x] Pass Gate B final device regression.
- [x] Confirm single installed FAP path: `/ext/apps/Tools/labmate.fap`.
- [x] Confirm existing CSV/History and Profile S1 compatibility in device tests.
- [ ] Choose explicit v1.6.1 release/publishing strategy and authorization.
- [ ] Verify release asset checksum and package provenance from exact CI artifact.
- [ ] Publish new v1.6.1 version/tag/release only after explicit approval.

The `v1.6.1-dev` branch includes documentation-only commits beyond the
frozen firmware SHA. DO NOT use branch HEAD as a substitute for the tested
binary commit, and do not assert a new firmware CI run on the docs commit.
Keep `main`, existing v1.6 Stable assets and tags unchanged without an
explicit separate release instruction.
