# LabMate v1.8.1 maintenance — Button Analyzer STOP / RESUME

**State:** development candidate; CI PASS and operator-reported Button test B1/B3/B4/B5/B6 PASS (5/6); B2 NOT VERIFIED. NOT a published Stable release.
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
| B2 | Button Analyzer START begins measurement | **NOT VERIFIED**, not FAIL and not PASS |
| B3 | STOP retains press/release counts | PASS |
| B4 | RESUME continues counters without clearing | PASS |
| B5 | STOP → UP RESET clears counters | PASS |
| B6 | BACK exits normally | PASS |

**Count: 5 PASS, 1 not verified (5/6), zero reported failures.**
Because B3/B4 PASSED, START/RESUME interaction was apparently usable,
but this does **not** override the explicitly unverified B2 criterion.
Keep B2 open until the operator separately verifies that a new START
with a known-safe dry contact or existing 3.3V test signal on PC1
registers at least one press/release event.
No new code or final Stable tag is justified solely by this report.

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
- [ ] Real-device Button test B1–B6: **5/6 explicitly PASS,
  B2 NOT VERIFIED**; full Button functional acceptance pending.
  Details below. Other-tool regressions PWM/Counter/UART/Profiles/History
  still pending.
- [ ] Final `v1.8.1`-labelled source/binary and real hardware
  final smoke before publication. No GitHub v1.8.1 Stable tag
  should be created prematurely.

**Do not call an SDK or host test a physical PASS.** No demo or
second application is required. Previous v1.8 release is unchanged.
