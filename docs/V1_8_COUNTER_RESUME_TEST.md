# v1.8 Counter STOP/RESUME — Development Candidate

Status: **C1–C8 8/8 PASS (user-reported physical Flipper test, 2026-10-12)**;
isolated follow-up to completed coordinator refactor PR #5. Official v1.7
Stable remains unchanged.

The exact development FAP was produced by CI
[38299402235](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38299402235)
from commit `989f6f37250f3bdba76144cfb4373ae236b97291`,
SHA256 `6ABB24285C1103429A6D978FF45B191922394D7CA2C462E05FBD207ED4BCAECB`.
CI completed 2/2 PASS (Momentum SDK API 87.1, host C math,
static guards and mock installer). The tester returned PASS on every
C1–C8 checkbox for this development candidate. User-reported functional
checks are not independent calibrated timing measurements or a soak test.

## Intended change

The old Event Counter behavior was START -> count -> STOP -> START
**reset to zero** (confirmed in unchanged v1.7 source). In this dev patch:

- Enter Counter via menu: fresh session with total/time zero, capture STOP
- OK START: count hardware PB3/TIM2 rising edges
- OK STOP: freeze result and accumulate elapsed **active RUN** ticks
- OK RESUME: new TIM2 session, **keep software count** and active-time total
- UP RESET while STOP: clear count and active-time total explicitly
- BACK to menu: detach capture, preserve no resource ownership
- New Counter entry: fresh zero-count session
- Physical timer wrap accumulation and 64-bit saturation unchanged
- GUI shows `RESUME` while a stopped session has count or elapsed time

The patch adds pure host-testable elapsed tick maths and a CI static guard.
Real Flipper functional tests were reported PASS (C1–C8). Counter code is now eligible for a separately verified PR merge; no v1.8 Stable release is implied.

## Physical test checklist — 8/8 PASS (operator report)

- [x] C1: Fresh menu entry Counter shows 0, STOP, OK START
- [x] C2: With a safe PA7 -> PB3 3.3 V GPIO loopback at 100 Hz/50%,
      START increments total, STOP freezes e.g. ~100 or higher
- [x] C3: Wait ~5 seconds in STOP: count and elapsed time remain unchanged
- [x] C4: OK RESUME continues count **from old total**, not zero; UI shows
      elapsed active time without counting the STOP interval
- [x] C5: STOP then UP RESET clears total/time; next START begins at zero
- [x] C6: BACK to menu / re-enter Counter starts STOP with zero; PWM RUN
      persists within app if explicitly enabled; exiting LabMate stops PWM
- [x] C7: Frequency Meter PB3 works after leaving Counter (TIM2 released)
- [x] C8: Re-check Profiles S1, recent CSV History, normal app navigation

3.3 V-compatible GPIO loopback only. Stop generator before changing pins.
No calibrated hardware timing/soak claims from this test.
