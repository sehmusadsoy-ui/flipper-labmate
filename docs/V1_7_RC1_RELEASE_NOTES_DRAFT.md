# LabMate v1.7 RC1 — Release Notes (DRAFT, NOT PUBLISHED)

> **Preparation only.** This document is not a release, tag or announcement.
> Base RC1 and a narrow Profiles-fix FAP were CI-built, USB-installed and user-tested. The integrated final RC1 artifact remains to be verified. No GitHub Release or tag exists.
> The latest publicly published stable release is **v1.6.1**, unchanged.

## Highlights since v1.6.1

### New and expanded instruments

- **PWM Studio — TIM1 / PA7:** the 15 existing presets remain available.
  Adjustable **5–95% duty** in 5% steps, with a default of 50%.
  A STOP-only **CUSTOM 1–50,000 Hz** mode uses 1/10/100/1000 Hz editing
  steps. PWM can continue during in-app navigation, but stops on full
  application exit. Only verified 3.3 V-compatible GPIO signals should
  be connected.
- **Event Counter — PB3 / TIM2:** actual hardware rising-edge counting
  with a saturating 64-bit total, RUN/STOP, STOP-only RESET and an elapsed
  timer. It does not estimate total edges by multiplying rate by time.
- **Button Analyzer — PC1:** EXTI-based press/release detection using an
  internal pull-up (LOW means contact closed), configurable debounce
  intervals of **5, 10, 20 or 50 ms**, and displayed bounce, settle,
  hold and extra-edge information. The tested input was a clean
  Flipper-generated digital signal; actual mechanical bounce testing
  has **not** been performed.
- **Threshold Alerts:** visual-only configurable alert thresholds for
  Frequency (Hz), Pulse duty (%), Event Counter (rising edges) and
  Button settling (ms), with arm, latch and acknowledge behavior.
  Alerts do **not** switch PWM, trigger GPIO outputs or write CSV data.

### Usability, navigation and Records

- More distinguishable icons for all **11** menu tools and a **13-page
  About guide** describing tool inputs, methods and controls.
- Refined compact 128x64 monochrome layouts and two-key action footers
  in PWM Studio, Button Analyzer, Event Counter, Threshold Alerts and
  the Records screens.
- **Data Logger:** better organized source, live reading, row count,
  READY/REC/WAIT/DONE/ERR state and SAVE controls. The established
  1-second CSV format and three sources (PC1 LOW, PB3 HIGH, PC1 PULSE)
  remain compatible with older files.
- **Log History:** selected-file list, read-only CSV detail, and a
  **new single-log DELETE mode**. LEFT/RIGHT switches OPEN/DELETE;
  deletion requires selecting the file and a second OK on an explicit
  `DELETE THIS FILE?` / `CANNOT UNDO` confirmation. BACK cancels.
  The fixed file path is restricted to LabMate's `log_XXXX.csv` files;
  deletion is not recursive. **Deletion is permanent and has no undo.**
  The list displays at most the latest 32 matching logs at once.
- **Profiles:** clearer S1/S2/S3 slots and status; existing SAVE, LOAD,
  DELETE and CRC-protected redundant storage remain compatible.
  Profiles save the frequency/pulse pin choices, one of the 15 generator
  presets, and logger source. The current profile schema **does not save**
  custom PWM frequency, duty, or Threshold Alerts settings. Saving
  CUSTOM is refused; loading a preset resets duty to 50%. A profile
  LOAD does not automatically start PWM. A later RC1 candidate fix adds
  permanent LOAD/SAVE/DELETE action labels, slot-specific confirmation
  prompts and blocks all profile mutations while PWM/capture/logger is
  active, including immediately before final SAVE/DELETE commit.

### Stability and fixed defects

- Fixed first entry to Frequency Meter when a saved profile selects
  LOW PC1: initializes LOW capture rather than incorrectly initializing
  PB3 HIGH and showing ERR.
- Fixed Pulse Analyzer's asymmetric-duty accumulation, where a 100 Hz
  / 95% input displayed HIGH while LOW, PERIOD, DUTY and statistics
  remained blank; the reciprocal 5% case is covered as well.
- Consolidated capture-owner handoff/cleanup between PC1 EXTI, PB3
  TIM2 and independent PA7 PWM, including tested app-exit shutdown.
- Continued the portable-code, 128x64 layout, Momentum SDK compile,
  profile/CSV, threshold and Windows mock-installer test coverage.

## Validation record and scope

**User-reported on-device functional PASS checks** in `v1.7-dev`
include:

- PWM 100 Hz at 25%, 50%, 95% and 5% duty; 1 kHz/50%; custom
  1235 Hz/50%; Pulse timing and extrema/STATS at asymmetric duty.
- Event Counter at 10 Hz with STOP/RESET, PB3 source transition to
  Frequency Meter HIGH and Data Logger HIGH; Button Analyzer against
  a clean 1 Hz digital stimulus and transitions among PC1 tools.
- Four Threshold Alerts sources, acknowledgement and latching.
- Legacy frequency/pulse LIVE/HOLD/STATS, Logger's three modes,
  History's old/new CSV browsing and Profiles S1 persistence.
- Revised menu/icons/About and instrument layouts, along with user
  screenshot review of Records. The user also reported that the new
  Log History DELETE worked; the exact cancel-path, unrelated-file
  preservation and SD error-path checks were **not each separately
  reported PASS**.

All physically tested signal sources above were Flipper's own
**PA7-to-PC1 or PA7-to-PB3 3.3 V digital loopback**, not an independent
frequency/voltage reference. See `docs/V1_7_DEV_NOTES.md` for
test-by-test evidence and original observations. A passing native
or CI test does not replace physical validation.

**Last development source verified in CI:**
`b5bbd31804d3bed068aaf425e0b408fa7962ddbc`

**Latest corresponding development CI:**
[GitHub Actions 38185793925](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38185793925)
— 2/2 jobs PASS (Momentum FAP, layout/static/host tests, file
SHA256 creation and verification, and a mocked Windows installer).
Artifact: `labmate` (FAP + `SHA256SUMS.txt`).
Later `v1.7-dev` commits through
`52fe588ddf19a38bc01bda7f8de6d4a6cc7d725b`
were documentation-only. **These results belong to a development FAP,
not to a newly built RC1-labeled artifact.**

## RC1 physical verification (user-reported, 2026-10-12)

The original RC1-labeled FAP (CI run `38186623651`; source
`55edee5890c2d62ea229f9271c97c6260b067b5a`; verified FAP SHA256
`DB2BB859819075E0120FEF2E65131CB18127FB91B881F7C8520B4CA22277064F`)
was installed and tested. Boot/version/PWM STOP, PWM 100 Hz 95%/5%,
Pulse PC1 timing/statistics, Frequency LOW PC1 and HIGH PB3, Button clean
input, Counter and source handoff, Frequency Threshold at 50/200 Hz,
Logger HIGH PB3 CSV/History open/delete cancellation/confirmed deletion,
and profile data/load and exit STOP all passed. The original RC1's
Profiles PWM-RUN action UX did **not** meet the user expectation (one
FAIL): a blocked LOAD could be followed by selecting and confirming
SAVE/DELETE while PWM was still running.

A focused fix was implemented separately on `v1.7-profiles-ux-fix`:
source `f6bebbe996d22cbafe49097abde336911e5dc8c3`,
[CI run 38188798973](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38188798973)
2/2 PASS, FAP SHA256
`ED2E91A02AB0F720D6B48EAC13D505D37570FB3A4A1F8E8A76D59E1B79FE14AA`.
Its user-confirmed Tests 6A (5/5), 6B (5/5), and 6C (6/6) all PASS:
cancel/save/load of S1; PWM RUN blocks all three actions; slot-specific
overwrite/delete confirmations; temporary S2 create/delete; S1
persistence across relaunch. Profiles storage encoding is unchanged.

The user had deleted all three profiles while evaluating the ambiguous
original UI; the fix tests started with empty slots and recreated S1.
Do not imply that the original user profile settings were recovered.

**Pending:** verify the final integrated `v1.7-rc1` FAP checksum, a short
on-device handoff check, candidate screenshot/release-note review and
explicit approval before publishing an RC pre-release. Old base/fix FAP
checksums are not valid for a newly compiled integrated artifact.

## Explicitly deferred and unverified

- **NOT TESTED: real mechanical momentary switch contact bounce,
  debounced electrical settle/hold against a physical pushbutton.**
  The user will obtain a switch later.
- **NOT TESTED: independent oscilloscope or calibrated-instrument
  measurement** of PA7 output frequency, duty, waveform, voltage HIGH
  (~3.3 V), LOW or shutdown electrical state. The user will obtain
  measurement equipment later.
- NOT EXHAUSTIVELY TESTED: all duty/frequency combinations, every
  supported Pulse input pin, external input characteristics, long
  endurance runs, full/corrupted/missing SD, abrupt power loss,
  simultaneous external SD writes, or repeated DELETE failure recovery.
- GPIO Monitor `EDGES` uses polling and can miss narrow pulses;
  Button Analyzer's debounce intentionally suppresses pulses shorter
  than its configured quiet interval.

## Safety, compatibility and release controls

- **3.3 V digital GPIO only.** Do not connect unknown voltage, 5 V,
  mains, automotive wiring or other uncontrolled external sources
  directly to Flipper GPIO.
- Designed for **Flipper Zero with a compatible Momentum Firmware API**.
  Existing `/ext/apps_data/labmate/` CSV/profile storage paths and
  file formats are preserved. Back up valuable CSVs/profiles before
  maintenance. The installer updates the external FAP, not the MCU
  firmware.
- The isolated candidate branch **`v1.7-rc1`** displays
  **`v1.7rc1`** in the LCD menu/About; SDK-compatible FAP manifest
  version remains **`1.7`**. The candidate FAP was compiled on the
  exact source commit below with a generated `SHA256SUMS.txt`.
  Independently verify the downloaded FAP against that checksum before
  installing and perform a short on-device RC1 smoke test.
- **Do not publish a release, create a release tag, update `main`, or
  modify published v1.6.1 Stable without the user's explicit approval.**

## RC1 status

**DRAFT / BASE RC1 AND PROFILES FIX DEVICE CHECKS PASS (with documented base UX failure); FINAL INTEGRATED CANDIDATE/PUBLICATION PENDING.**

- Branch: `v1.7-rc1` (no public Release or tag).
- First RC1-labeled source commit:
  `55edee5890c2d62ea229f9271c97c6260b067b5a`.
- [RC1-specific CI run 38186623651](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38186623651): **2/2 PASS** — Momentum FAP, host/layout/security
  checks, SHA256 file creation and check, Windows mocked installer.
- GitHub Actions artifact `labmate` (id `11719294967`) contains
  `labmate.fap` and `SHA256SUMS.txt`. The artifact ZIP digest is
  not the FAP digest; validate the downloaded FAP with `sha256sum -c`
  or the checksum-checking installer.
- RC1 source differs from the last dev FAP only in the candidate LCD
  label, widened menu badge, matching static layout guards and the
  candidate-branch CI workflow. **No instrument algorithm changes.**
- Original RC1 and focused Profiles fix have fresh, separate user-reported
  physical evidence (see RC1 physical verification above). The final
  integrated candidate still requires checksum and short device handoff.
  Do not reuse the SHA256 of either earlier binary for the final artifact.
