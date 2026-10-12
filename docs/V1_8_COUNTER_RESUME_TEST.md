# v1.8 Counter STOP/RESUME — Development Candidate

Status: **not yet verified on Flipper**; isolated follow-up to completed
v1.8 coordinator refactor (PR #5). Official v1.7 Stable remains unchanged.

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
The user must retest on real Flipper before this branch is eligible to merge.

## Physical test checklist

- [ ] C1: Fresh menu entry Counter shows 0, STOP, OK START
- [ ] C2: With a safe PA7 -> PB3 3.3 V GPIO loopback at 100 Hz/50%,
      START increments total, STOP freezes e.g. ~100 or higher
- [ ] C3: Wait ~5 seconds in STOP: count and elapsed time remain unchanged
- [ ] C4: OK RESUME continues count **from old total**, not zero; UI shows
      elapsed active time without counting the STOP interval
- [ ] C5: STOP then UP RESET clears total/time; next START begins at zero
- [ ] C6: BACK to menu / re-enter Counter starts STOP with zero; PWM RUN
      persists within app if explicitly enabled; exiting LabMate stops PWM
- [ ] C7: Frequency Meter PB3 works after leaving Counter (TIM2 released)
- [ ] C8: Re-check Profiles S1, recent CSV History, normal app navigation

3.3 V-compatible GPIO loopback only. Stop generator before changing pins.
No calibrated hardware timing/soak claims from this test.
