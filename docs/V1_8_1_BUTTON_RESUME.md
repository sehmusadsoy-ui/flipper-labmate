# LabMate v1.8.1 maintenance — Button Analyzer STOP / RESUME

**State:** development candidate; CI PASS and operator-reported Button test B1–B6 **6/6 PASS**, with B2 separately retested PASS. NOT a published Stable release.
**Base:** published v1.8 Stable source and its post-release documentation.
No change to the existing immutable v1.8 tag/assets or user's installed FAP.

## Observed v1.8 behavior

The operator reports that Button Analyzer OK toggles correctly:
RUN → STOP → RUN; the second RUN resets all counts. Source review
confirmed `labmate_button_capture_start()` reinitializes the button
state at every start. STOP itself does **not** automatically restart.
This is previous design behavior, not an observed firmware crash.

## Maintenance change (single real LabMate app)

- First `OK` from STOP: **START**, fresh counters.
- `OK` during RUN: **STOP**, release PC1 EXTI callback, preserve all
  completed press/release counts and last measured bounce/settle/HOLD.
- `OK` after STOP: **RESUME**, continue cumulative measurements.
  The GPIO is re-initialized with its actual current logic level to
  discard partial debounce transitions accrued before STOP and avoid
  synthesizing events that occurred during the stopped period.
  Partial contact/HOLD duration interrupted by STOP is not carried
  across pause time; the last completed HOLD metric is preserved.
- `UP` during STOP: **RESET**, clear counters and session flag,
  restoring next OK to **START**. During RUN, UP must not reset.
- `DOWN`: main/detail view only, no resource changes.
- `BACK`: releases capture; re-entering Button Analyzer begins with
  fresh statistics (previous page/session data is not persistent).
- PC1 3.3 V pull-up/active-low polarity and original EXTI ownership
  safety constraints remain unchanged.

## On-device Test 18.1-B1 — operator report (2026-10-14)

The operator submitted:
`B1=PASS; B2=DOĞRULANMADI; B3=PASS; B4=PASS; B5=PASS; B6=PASS`.

| Test | Defined criterion | Operator result |
| --- | --- | --- |
| B1 | On-device `v1.8.1d` label | PASS |
| B2 | Button Analyzer START begins measurement | Initially NOT VERIFIED; separate follow-up PASS |
| B3 | STOP retains press/release counts | PASS |
| B4 | RESUME continues counters without clearing | PASS |
| B5 | STOP → UP RESET clears counters | PASS |
| B6 | BACK exits normally | PASS |

**Initial report count: 5 PASS, 1 not verified; zero reported failures.**
The operator subsequently completed the specifically requested B2 retest:
**`LabMate v1.8.1d B2 tekrar testi: PASS`**. The retest criterion was
STOP → UP RESET, confirm START, OK START to RUN, then a known-safe PC1
button/digital event causing PRESS and RELEASE counters to increase.
Thus **cumulative B1–B6 physical functional acceptance is 6/6 PASS**
(user-reported). No extra USB log, unrelated instrument regression,
independent oscilloscope evidence or final Stable candidate acceptance
is inferred.

## Verification gates

- [x] Host native test confirms resume keeps counts / metrics and
  discards pending transition and stopped-time HOLD. CI run
  [38551143503](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38551143503).
- [x] Static guard ensures non-destructive STOP, correct STOP/RESUME
  footer, explicit RESET and version badge fit.
- [x] Momentum SDK built the actual integrated `labmate.fap`,
  with `v1.8.1d` on-screen development label. Source
  `9086c9d4af3f1cbc3dd92ea22385a5a68826baf2`, FAP SHA256
  `7862d0ebb36a8b77699db2037ba4cc6b641f6c291a5f18d36b27ad883931fcc9`.
- [ ] A complete independent USB installation transcript (including
  installer exit code) was not supplied. User-confirmed `v1.8.1d`
  visible on actual Flipper in B1 PASS supports use of the candidate.
  Original v1.8 Stable remains available for rollback.
- [x] Real-device Button test B1–B6: **6/6 operator-reported PASS**
  after separate B2 retest PASS. Button functional acceptance complete;
  other-tool regressions PWM/Counter/UART/Profiles/History still pending.
- [ ] Final `v1.8.1`-labelled source/binary and real hardware
  final smoke before publication. No GitHub v1.8.1 Stable tag
  should be created prematurely.

**Do not call an SDK or host test a physical PASS.** No demo or
second application is required. Previous v1.8 release is unchanged.
