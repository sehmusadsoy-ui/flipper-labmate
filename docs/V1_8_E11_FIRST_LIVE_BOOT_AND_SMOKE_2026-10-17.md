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
