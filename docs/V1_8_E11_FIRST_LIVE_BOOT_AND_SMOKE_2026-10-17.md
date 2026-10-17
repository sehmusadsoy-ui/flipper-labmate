# LabMate v1.8 E11 — FIRST post-update REAL device evidence + non-destructive physical plan

**Date:** 2026-10-17 (operator's Windows log). **Branch:** `dev/v1.8-completion`, PR #13 **DRAFT**. No Stable/main/tag promotion.

## Evidence accepted: CLI boot and exact installed resources

The operator performed the first explicitly authorized **FULL** E11 trial
using source `ba379f20fb29369501e1057f570a911f71ac83f8`
and CI #38966248325, preserving the two-state PC backups first.
The current script `check_v18_e11_postupdate_readonly.py` was
then executed on the **actual COM7-connected Flipper**, rather than CI.
The user posted this complete status:

```text
E11 LIVE FIRMWARE LABEL AND BASE: MATCH (NOT A FULL FIRMWARE FINGERPRINT)
E11 LIVE APP FAP: MATCH PINNED E11 BY MD5
E11 LIVE NATIVE JS GPIO PLUGIN: MATCH PINNED E11 BY MD5
E11 LIVE RESOURCE MANIFEST: MATCH PINNED E11 BY MD5
E11 POST-UPDATE RESOURCE SCREEN PASS - READ ONLY
BOOT SEEN BY CLI; NATIVE GPIO/TIM1/TIM2/EXTI PHYSICAL PASS: NOT TESTED
DO NOT MERGE OR TAG STABLE BASED ON THIS SCREEN.
```

Status interpretation: Flipper **booted far enough to serve CLI**;
firmware reports the expected version label/base hash; actual installed
app, native JS GPIO plugin and resource Manifest have correct MD5
relative to separately pinned locally SHA256-checked E11 build bytes.
This materially advances from an update-request-only state.

**Not proven:** entire flashed firmware image SHA, live native lease
correctness, GUI screen rendering, app launch/exit, exact PWM pin duty/
frequency/off-state, native firmware-wide TIM1/TIM2/EXTI conflicts,
normal function of all radio/NFC/services, SD history/profile integrity
after update, return from rollback or firmware-recovery testing.
Do not propagate earlier EXITFIX E1–E9 PASS to new E11.
The absent external fixtures in `DEFERRED_HARDWARE_TESTS.md` remain OPEN.

## Round A — operator on-device smoke, no GPIO wiring

Do not run any updater again, reflash, restore or attempt repair.
Keep external GPIO wires/peripherals disconnected. Verify the Flipper
display looks normal first. Open the single installed
`Apps > Tools > LabMate` app.

1. **Menu and navigation:** root categories exactly
   `MEASURE > OUTPUT > RECORDS > COMM > INFO` (INFO is LAST).
   Enter `INFO > About`, page left/right and BACK to menu.
   Enter `RECORDS > Log History`, browse only without delete.
   Enter `RECORDS > Profiles`, look only: do not SAVE/LOAD/DELETE
   while doing the first post-update smoke. BACK to menu. Confirm
   the app exits and reopens without crash.
2. **PWM TIM1/PA7 native START/STOP:** no connected devices. Enter
   `OUTPUT > PWM Studio`. It must start at STOP; opening the
   screen is **not** permission to drive PA7. Press OK **once** to
   request RUN. If BUSY/ERR appears, stop, record that state; do
   **not** repeatedly force it. If RUN appears, press OK once more
   to STOP and verify STOP appears. Then exit/re-enter PWM, repeat
   a single RUN->STOP. Distinguish a real screen badge change
   from an externally calibrated PWM waveform test (deferred).
3. **Persistent PWM vs COMM refusal:** start PWM, confirm RUN,
   press BACK. The PWM output intentionally remains running until
   explicit STOP or app exit. While PA7 is held, enter
   `COMM > I2C Explorer` and press OK to request a scan:
   expected BUSY, not RUN/SCANNING. BACK then enter
   `COMM > 1-Wire Temp`, press OK once to request READ:
   expected BUSY, not conversion. BACK; return to
   `OUTPUT > PWM Studio`, confirm RUN and press OK to **STOP**.
   Do not disconnect/reconfigure PA7 while RUN. If any screen
   hangs or the PWM cannot be stopped, terminate this round,
   preserve the on-screen error and avoid manually changing
   GPIO. The refusal demonstrates **LabMate's local tool busy
   policy**; it does not demonstrate denial of arbitrary
   foreign firmware services.
4. **No-sensor recovery (optional, only after PWM STOP):**
   `COMM > I2C Explorer > OK` without a connected I2C device.
   Accept NONE (or report ERR/BUSY exactly, if shown); do not
   report an ACK PASS on an empty bus. STOP/BACK, then re-enter.
   `COMM > 1-Wire Temp > OK` with no DS18B20:
   expected NONE and safe BACK/re-entry, not measured
   temperature. A missing sensor cannot prove CRC/temperature.
5. **No-edge TIM2/EXTI smoke, after PWM STOP:**
   `MEASURE > Event Counter` must enter STOP. OK RUN, OK STOP;
   UP reset only in STOP, BACK. `MEASURE > Button Analyzer`
   must enter STOP; OK RUN, OK STOP, OK RESUME and STOP again;
   BACK. No wired real button/pulses: do not assert measurement
   accuracy from zero/no edges.

**Always distinguish:** PASS / FAIL / SKIP / NOT TESTED for each.
Record exact visible status badges RUN/STOP/BUSY/ERR, key sequence
and any lockup; do not invent GPIO readings or missing fixtures.
Confirm PWM was STOP before moving to other activities.
For hardware trouble, stop and report: no firmware re-run/repair or
auto rollback on this evidence alone.

## Still required after Round A

Native cross-service coexistence with owned firmware services,
external 3.3 V loopback and genuine safe fixtures, preserved SD
History/Profiles functionality, E11 FAP app exit/reopen, and test
backlog HW-01..HW-19 all require their own dated, correctly scoped
results. `main` and published Stable v1.8 stay immutable.


## 2026-10-17 — Operator explicitly deferred physical tests until tomorrow

After reporting the real post-update CLI/resource matching PASS, the
operator asked to **postpone Round A GUI/PWM/COMM/Counter/Button tests until
tomorrow**. **No Round A hardware test result has yet been reported**,
so every such case above remains NOT TESTED on the installed E11 pair.

The operator also shared an **older app-menu screenshot** displaying
`KeyCopier`, `LabMate`, `LabMate BUSY Probe`,
`LabMate 2: UI Demo`, `LabMate Scope UI Demo`.
The screenshot **does not establish the installed FAP basenames or
prove the same extra test apps survived the intervening full E11 update**.
The operator wants to remove **only obsolete standalone demo/probe FAPs**,
keeping KeyCopier, actual production `/ext/apps/Tools/labmate.fap`,
firmware resources, LabMate `apps_data`, History, Profiles and
read-only PC snapshots intact.

The new `scripts/cleanup_v18_demo_faps.py` first confirms the actual
installed E11 main app via local independent SHA256 and live Flipper MD5,
then lists the actual Tools FAP names. Without `--apply` it is strictly
read-only. With `--apply`, it identifies at most three conservative
LabMate-named demo/probe FAP **filenames** (not the GUI label), makes a
fresh exact PC-only readback backup for each, checks remote MD5
before/after, requires an exact typed `SIL-DEMO-N` confirmation, and
only then calls `storage remove` for those named files. Other apps
and user data are out of scope. A demo with a non-obvious basename
must be handled separately after evidence review, not guessed.

**Status:** No report of demo deletion yet. Deletion software's
synthetic/CI PASS, when it arrives, is NOT a live microSD delete PASS.
Final E11 functional acceptance remains OPEN; Stable/main unchanged.

## 2026-10-17 — FIRST operator-reported E11 live GUI Round A: **6/6 PASS**

**Exact setup context:** actual COM7-installed matched E11 full trial firmware
`mntm-dev / d3f89dfe`, app FAP
`2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0`
(verified from independently SHA256-pinned candidate and live SD MD5).
Operator personally ran Round A on real Flipper with no external GPIO
fixture and submitted the complete following results in conversation:

```text
A1 — Menu order and INFO last: PASS
A2 — About and BACK operate correctly: PASS
A3 — PWM UI RUN/STOP twice: PASS
A4 — With LabMate PWM running, I2C scan request -> BUSY: PASS
A5 — With LabMate PWM running, 1-Wire read request -> BUSY: PASS
A6 — Return to PWM and stop: PASS
```

**Scope accepted:** GUI app launched, root menu/Info ordering and BACK;
PWM native TIM1/PA7 HAL RUN/STOP lifecycle *at observed UI level* with
two repetitions; LabMate-local I²C/1-Wire concurrent-use BUSY refusal
while PWM active; PWM returned to STOP. No unexpected failure was reported.
User-provided PASS is evidence of observed UI control flow, not an
independently instrumented measurement or a full timer lease trace.
Do not conclude calibrated PA7 waveform OFF state, exact timer/EXTI
register release, cross-firmware/third-party contention, physical
positive I²C ACK or DS18B20 CRC from these six results.

**Not included in user's explicit A1–A6 report:** Log History/Profiles
read-only inspection; app full exit/reopen; no-sensor I²C/OneWire
standalone scan; Event Counter TIM2; Button Analyzer EXTI; external
device/3.3 V loopback and native firmware-service contention. Preserve
all as not yet tested on current pair.

### Next requested device Round B — no GPIO wiring

Require prior PWM STOP; no firmware changes, external GPIO connections,
data deletions or saved-profile writes. Event Counter and Button Analyzer
use the real E11 production FAP:

- **B1:** `MEASURE > Event Counter`: initial STOP; OK -> RUN; wait ~3 s;
  OK -> STOP. Counter input PB3 is unconnected, so its number is **not**
  an accuracy verdict.
- **B2:** After B1, bottom action should offer RESUME if elapsed time
  accumulated (the Counter UI uses elapsed ticks or count). OK ->
  RUN again; then OK -> STOP. Verify no unintended reset across resume.
- **B3:** Press UP only while STOP; counter/time resets. BACK -> menu;
  reenter Counter shows STOP.
- **B4:** `MEASURE > Button Analyzer`: STOP on entry; OK -> RUN;
  OK -> STOP; OK -> RESUME/RUN; OK -> STOP again; no unexpected BUSY.
- **B5:** Button DOWN toggles MORE/MAIN details without rearming;
  LEFT/RIGHT changes quiet/debounce time among displayed options.
  UP while STOP resets statistics (no external mechanical button).
- **B6:** BACK to menu; reenter Button shows STOP and works;
  leave app entirely then reopen and confirm regular menu
  navigates without hang.
- **B7 optional/next stage:** `COMM > I2C Explorer` after PWM stopped:
  OK scan no connected devices, NONE/ERR with exact observed status;
  BACK/reenter without hanging. `COMM > 1-Wire Temp`: OK no sensor,
  expect NONE; this is only a missing-device smoke, **not** positive
  ACK or valid temperature proof.

On any ERR, BUSY, hang, unexpected edge count or inability to STOP,
record screen and stop test. Mark each PASS/FAIL/SKIP; do not run
firmware install or automatic recovery. Records/Profiles
preservation remains Round C.

## 2026-10-17 — Operator-reported REAL E11 Round B: **6/6 PASS**

Following actual paired E11 Round A (6/6), the operator reported
**`B1-B6 PASS`** for the exact previously requested device Round B
sequence (same installed E11 matching FAP + firmware; no GPIO fixture).

| Case | Actual operator verdict | Scope of requested sequence |
|---|---|---|
| B1 | PASS | Counter PB3/TIM2 STOP → RUN → STOP and short wait |
| B2 | PASS | Counter RESUME → RUN → STOP without unexpected clear |
| B3 | PASS | Counter UP RESET only while STOP; BACK/re-entry STOP |
| B4 | PASS | Button PC1/EXTI STOP → RUN → STOP → RESUME → STOP |
| B5 | PASS | Button MORE/MAIN, debounce change, stopped reset |
| B6 | PASS | Button BACK and re-entry, complete LabMate exit and reopen |

**Total actual paired E11 GUI/lifecycle smoke:** Round A 6/6 +
Round B 6/6 = **12/12 operator-reported PASS**. These are functional
controls on real hardware, not calibrated timer/counter measurements or
proof of externally driven EXTI edges. The live app's exit/reopen was
reported PASS in B6; delete the previous unfinished wording only by
superseding it here, not by rewriting the historical evidence.

**Unresolved:** firmware-global service arbitration and nonstandard
plugin paths, actual TIM2 count on known external 3.3 V edges,
independently checked PA7 PWM frequency/duty/OFF, actual dry-contact
bounce, positive I²C ACK or DS18B20 conversion, actual SD CSV/Profile
data readback preservation after E11 update, hardware recovery/rollback.
No main or Stable asset mutation, no firmware reinstall.

### Proposed REAL device Round C: SD preservation and no-device COMM (safe scope)

Only after confirming PWM STOP; no external GPIO leads or unsafe inputs.
Keep all current user CSVs and Profiles; do not SAVE, DELETE, LOAD, or
use History delete mode.

- **C1 — Log History:** `RECORDS > Log History`; verify historical
  numbered CSVs still listed, open one existing nonempty log read-only,
  BACK. This is **UI readability**, not byte-for-byte SD preservation.
  Leave any READ/DELETE mode toggle in READ before OK.
- **C2 — Profiles:** `RECORDS > Profiles`; verify existing profile
  slot S1 is visibly still present (if it existed before E11).
  Browse UP/DOWN and BACK **without OK**; avoid LOAD/SAVE/DELETE.
- **C3 — I²C no-device scan and cancellation:** with no I²C peripheral
  connected, enter `COMM > I2C Explorer`, press OK once to scan.
  Observe final state (commonly NONE; ERR or BUSY must be reported
  exactly, never silently accepted). During SCANNING, OK means STOP.
  BACK and reopen: READY, no freeze or persistent BUSY.
- **C4 — 1-Wire missing-sensor recovery:** `COMM > 1-Wire Temp`,
  OK READ with no DS18B20. Expect NONE after reasonable bounded
  completion. BACK/reopen returns READY; do not invent temperature.
- **C5 — Basic device consistency:** Confirm normal Flipper menu and
  app launch/exit after these reads; no SD error, unexpected BUSY,
  locked screen or reboot observed.
- **C6 — Restore safe idle:** PWM remains STOP, Counter and Button
  STOP, no COMM operation left RUNNING. No changes to historical
  storage, updater, firmware or installed FAPs.

Require exact operator PASS/FAIL/SKIP + the actual I²C and 1-Wire
displayed status for C3/C4. A missing physical peripheral is not
positive protocol-test evidence.

## 2026-10-17 — Operator-reported paired E11 Round C: **6/6 PASS**

The operator replied **`C1–C6 PASS`**, following the six cases
listed immediately above. Preserve the result scope exactly:

| Case | Operator verdict | What was requested |
|---|---|---|
| C1 | PASS | Read-only Log History list and open older CSV, BACK |
| C2 | PASS | Existing S1 profile visibly present, browse without mutating |
| C3 | PASS | Unconnected I2C Explorer scan, BACK and re-entry |
| C4 | PASS | Unconnected 1-Wire Temp READ, BACK and re-entry |
| C5 | PASS | Normal app exit, reboot-free reopening and responsive menu |
| C6 | PASS | No lingering PWM/Counter/Button/COMM operation, safe STOP |

**Important evidence limit:** the user did **not** separately state the
literal final on-screen badges for C3/C4 in this short response.
The prior test instructions expected `NONE` for an empty bus/no sensor
and asked for the labels, but no independent exact label text was
provided. Do NOT manufacture an observed `NONE` string.
Interpret as user-reported six workflow PASSs only; the standalone
I2C/OneWire UI negative-path smoke is covered at reported level.
A real positive 7-bit ACK or valid DS18B20 measurement was NOT tested.
Old logs/profile visible in UI does NOT imply byte-for-byte preservation
or verified restore. No user-owned files were intentionally changed.

**Cumulative matched real-device A+B+C:** **18/18 operator-reported
GUI/function/lifecycle PASS** (A6+B6+C6), separate from firmware
CLI boot/MD5 screen PASS. Remain DRAFT; no Stable or main mutation,
no firmware reflash or rollback. Physical safety/peripheral cases
HW-01..HW-19 remain only as actually covered by new evidence.

### Next Round D — optional previously documented SAME-Flipper 3.3 V loopback

Use the documented `docs/wiring_example.md` verified path **PA7 /
physical pin 2 → PC1 / physical pin 15** ONLY if the operator still
has a suitable jumper and can unambiguously confirm both pin labels
on their current Flipper. The sole loop connects one current device's
PA7 output to its own PC1 input. **No 5 V, OTG 5 V, external supply,
second GPIO output, ground/power rails or unknown wires.** Stop
the LabMate PWM and all captures, leave the app, and unplug any
other GPIO attachment BEFORE installing/removing this wire.
Check physical labels twice, and only then reenter LabMate.

- **D1** with no PWM RUN, set PWM Studio to 100 Hz/50% duty, start RUN,
  then BACK to menu without stopping.
- **D2** `MEASURE > Frequency Meter` select LOW **PC1** using LEFT.
  Observe a reasonably stable reading near 100 Hz (not necessarily
  exactly 100.00) and no BUSY/ERR; BACK.
- **D3** `MEASURE > Pulse Analyzer` on PC1; read HIGH, LOW, PERIOD,
  DUTY near 5 ms, 5 ms, 10 ms, 50% (functional comparison
  only, not oscilloscope calibration); BACK.
- **D4** return PWM Studio -> OK STOP, leave LabMate, verify app
  can relaunch, with all tools stopped. Only then remove wire while
  stopped. If anything ERR/BUSY/frozen, cease and note screen,
  no forced GPIO ownership or reboot-based workaround.
- **D5 deferred separately** repeat known-safe alternate path PA7
  to PB3 for actual TIM2 Event Counter and HIGH Frequency Meter.
  Do not connect PC1/PB3 simultaneously unless separately reviewed.

If no safe jumper or labels uncertain, record D1–D4 **SKIP,
hardware unavailable**; do not improvise. Independently calibrated
waveform/OFF state remains HW-02 NOT TESTED either way.
Native foreign-service conflicts remain a separate next gate, not
proved by the same-app loopback.

## 2026-10-17 — Operator-reported matched E11 Round D: **4/4 PASS**

After physical Round A–C 18/18 PASS, the operator reported **`D1-D4
PASS`** for the previously defined **same Flipper's PA7 → PC1 3.3 V
single-wire loopback**. Record this solely as the operator's four
functional test verdicts on the current exact firmware/FAP pair:

| Case | Operator verdict | Requested actual hardware activity |
|---|---|---|
| D1 | PASS | PWM 100 Hz/50% UI START, background RUN |
| D2 | PASS | Frequency Meter LOW PC1 captures actual loopback, no BUSY/ERR |
| D3 | PASS | Pulse Analyzer PC1 captures HIGH/LOW/PERIOD/DUTY functional loopback |
| D4 | PASS | PWM STOP, app exit/re-entry and safely remove wire while stopped |

**Numerical evidence caveat:** operator did not supply the actual frequency
readout, HIGH/LOW/PERIOD/DUTY screen values, nor an independent scope
capture. The previously prescribed *approximate reference targets*
100 Hz / 5 ms / 5 ms / 10 ms / 50% must **not** be quoted as real
observed measurements. Functional loopback PASS is real hardware
integration evidence, not independent measurement calibration and not
an instrument-grade output/OFF proof (HW-02 still NOT TESTED for that).

**Cumulative new matched E11 on-device checks:** A=6, B=6, C=6, D=4,
**22/22 operator-reported PASS**; original physical deferred test
exceptions, native service coexistence and true sensor/ACK tests remain
unproven unless separately documented. GUI and firmware MD5 postupdate
screen are separate evidence categories; no Stable promotion.

### Next Round E — controlled PA7 to PB3 TIM2 event count/high-frequency test

Review gate: earlier `docs/V1_8_COUNTER_RESUME_TEST.md` describes real
same-device 3.3 V **PA7 → PB3** loopback, and production
`src/labmate_frequency_tim2.c` configures PB3/TIM2_CH2 in rising-edge
external-clock mode; Counter cannot run simultaneously with HIGH
Frequency Meter because **both require TIM2**. Use one jumper ONLY.
Verify the `PA7` and `PB3` physical connector markings against
the present Flipper. If ambiguous, STOP and SKIP; never guess a numeric
GPIO header position. Never connect to 5 V, power rails, ground or
another output; do not connect both PC1 and PB3 at once.

- **E0 (precondition)** finish LabMate, ensure PWM STOP and all capture
  STOP, disconnect the prior PC1 jumper and all other attachments.
  With device and app safely idle, install the single PA7→PB3 jumper.
- **E1** open `OUTPUT > PWM Studio`, select 100 Hz, 50% duty,
  press OK to start RUN, press BACK to keep background RUN.
- **E2** open `MEASURE > Event Counter`: initial STOP 0; OK
  RUN, wait roughly 5 seconds, record actual PB3 rising-edge COUNT
  and elapsed time, OK STOP. Approximately 100 count/s expected
  from a 100 Hz source; avoid asserting an exact five-second count
  based on human keypress timing. Frozen total should remain stable
  during STOP.
- **E3** OK RESUME for roughly 3 seconds, observe count increases
  from prior value, STOP; UP RESET during STOP clears count/time.
  BACK must release the TIM2 owner.
- **E4** open `MEASURE > Frequency Meter`, select HIGH PB3
  using RIGHT (if not already high); verify functional reading
  reasonably near configured 100 Hz without unexpected BUSY/ERR;
  record the **actual displayed value**. BACK.
- **E5** go back to PWM Studio and explicitly STOP; exit LabMate.
  Then and only then remove PA7→PB3 jumper; subsequent app
  launch behaves normally. If ERROR/BUSY/freeze, do not force
  resource recovery; preserve observed evidence and cease.

Accept operator's actual E1–E5 PASS/FAIL/SKIP individually, actual
COUNT/time for E2 and actual frequency for E4 when available.
Do not infer calibrated timing, native RFID/SubGHz conflicting lease
denial or cross-firmware resource ownership from this loopback.

## 2026-10-17 — Round D numeric evidence supplied **after** D1–D4 PASS

The operator clarified explicitly that the following displayed values
belong to **the previous D experiment**, the single-wire
**PA7 → PC1** E11 functional loopback at PWM setting 100 Hz / 50%,
**not** to pending Round E / PB3 / TIM2:

```text
Frequency: 100 Hz
HIGH: 5.00 ms
LOW: 5.00 ms
PERIOD: 10 ms
DUTY: 50.0 %
```

Evidence classification: **user-reported, on-device displayed values**
from D2/D3; all five agree with the 100 Hz, 50% expected waveform to
the displayed precision. This supersedes the earlier record's
statement that no numerical D values were supplied *as of that point*,
without rewriting it. Same-device PWM is the reference source, not an
independently calibrated frequency/duty standard; **HW-02 independent
scope/frequency calibration stays NOT TESTED**. Do not count this as
new D test cases or as a TIM2/PB3 Round E result. Round E1–E5 remain
**NOT TESTED** until separately reported. No device write performed.

## 2026-10-17 — Operator-reported actual E11 Round E: **5/5 PASS**

The operator returned **`E1–E5 pass counter 100hz 50% count 508 5
saniye +3 saniye 832`** in the immediately preceding Round E
PA7→PB3 test, after the 22/22 confirmed earlier A–D functional
reports. This is **on-device operator report** for the matched FULL
E11 firmware/FAP pair, and must be scoped as such.

| Step | Operator verdict | Expected exercise | Actual additional observation |
|---|---|---|---|
| E1 | PASS | PWM PA7 100 Hz, 50% RUN then BACK | Source settings stated as 100 Hz / 50% |
| E2 | PASS | PB3/TIM2 Counter STOP→RUN ~5 s→STOP | 508 counted after approximately 5 s |
| E3 | PASS | RESUME ~3 more s→STOP and STOP-only RESET | cumulative 832 counted; **324 more edges** after resuming |
| E4 | PASS | Frequency Meter HIGH PB3 after Counter release | User says PASS, but **no independent displayed PB3 Hz number** supplied |
| E5 | PASS | PWM STOP, app exit and disconnect lead after STOP | User says PASS; no external instrument OFF capture |

**Timing interpretation:** human keypress intervals "~5 seconds" and
"~3 seconds" are approximate, **not** independently measured gates.
508 ≈ 500 expected edges over nominal 5 s from a 100 Hz waveform,
and delta 324 ≈ 300 nominal over another 3 s, consistent with
unspecified start/stop reaction timing and capture start phase.
Do not derive an accuracy percentage, a calibrated clock correction
or a "108 Hz real frequency" claim from those rough durations.
The clear increased cumulative total validates observable hardware
edge counting and **nonresetting software accumulation after RESUME**
at this functional scope. Cumulative **A 6 + B 6 + C 6 + D 4 +
E 5 = 27/27 user-reported matched E11 functional device PASS**.

**Boundaries:** no independently measured PWM output frequency/duty
or OFF voltage; no known calibrated edge generator/timing gate;
no measured PB3 HIGH Hz screenshot; no actual foreign firmware-owned
TIM2 refusal or native owner race test; no positive I2C ACK or 1-Wire
DS18B20, no byte-comparable full SD snapshot. Existing hardware
deferred checklist remains open where equipment unavailable.
No further firmware update, SD mutation, Stable/main merge or tag.

### Next Round F — native Momentum service sequential regression (no fixtures)

**Purpose:** catch basic post-E11 changes that prevent the patched
native firmware's other built-in services opening/exiting. This is
**SEQUENTIAL** and does not prove simultaneous TIM1/TIM2/EXTI
contention or all native lease participants.

Starting condition: LabMate completely exited; PA7→PB3 wire
disconnected only after STOP, no GPIO peripherals attached. Keep
saved NFC/RFID/IR/SubGHz/SD data intact. Never select Emulate,
Transmit, Send, save, delete, write, repair, force-reset or
firmware update. No need to deliberately create RF emissions.

- F1 native **NFC Read**: enter briefly without a tag, wait for
  normal reader status then BACK; no hang, forced reboot or fatal error.
  NFC produces its normal localized field in read mode; no card or
  credential data are needed.
- F2 native **125 kHz RFID Read**: enter briefly with no tag,
  verify the reader opens and BACK safely; no emulator or writable tag.
- F3 native **Infrared Learn**: open receiver screen with no remote
  pointing at it, then BACK without saving; no IR transmission.
- F4 optional native **Sub-GHz Read (RX ONLY)**: if available and
  permitted locally, open receiver interface and BACK; **never press
  TX/SEND**, even for a learned signal. SKIP if uncertain.
- F5 open production **Apps > Tools > LabMate** after these native
  services. PWM Studio must be STOP; Event Counter must enter STOP,
  briefly OK RUN/STOP with **no wire** and BACK, then app exits
  normally. This is source-release *sequential* recovery, not a
  simultaneously held native TIM2 owner test.

Treat any service absent from this Momentum build as **SKIP**, not
FAIL. Report exact unexpected BUSY/ERR or hang and stop at the first
failure. Do not over-claim RF protocol compatibility or shared
resource lease coverage based on UI-only smoke. Later exact native
RFID TIM2 vs Counter and native PWM vs LabMate TIM1 contention
require a reviewed concurrency fixture/scenario and are still OPEN.

## 2026-10-17 — Round E4 supplementary real HIGH PB3 frequency extrema

The operator separately added **"frekans değeri min 99 max 102.2 hz
bu arada hıgh pb3 için"**, explicitly identifying these displayed
readouts as the **HIGH PB3 Frequency Meter** portion of the already
completed E1–E5 loopback, not Round F or a new trial.

- PWM setting for Round E: **100 Hz, duty 50%** (from E1).
- User-observed HIGH PB3 Frequency Meter **minimum 99 Hz**.
- User-observed HIGH PB3 Frequency Meter **maximum 102.2 Hz**.

These are **displayed min/max observations**, not a time-series, an
instrument-calibrated stability measurement or a claim that the
actual PA7 output ranged 99–102.2 Hz. A simultaneous independent
measurement was not available. The previously logged E4 PASS now
has a numerical observed range; the E test count remains **5/5**,
cumulative matched E11 device functional checks **27/27**.

Round F native firmware service screens are still **NOT REPORTED**;
do not claim any F PASS from this E4 clarification.
