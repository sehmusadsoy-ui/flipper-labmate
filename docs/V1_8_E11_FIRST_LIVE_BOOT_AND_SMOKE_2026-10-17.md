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
