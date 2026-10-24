# LabMate v2.0 — Phase 3C Pulse STOP sealed evidence producer

**Date:** 2026-10-21. Development branch `dev/v2.0-signal-doctor`; Draft PR #21.  
**Status:** Native Pulse adapter source and pure host policy implemented; **real E11 FAP compile and device acceptance NOT YET RUN for this new code**.

## Implementation scope

1. **Native START:** `src/labmate_pulse_capture.c` calls `labmate_doctor_pulse_started()` only after successful native E11 callback installation and active capture ownership, and only when the Pulse Analyzer screen is selected. Start records the actual kernel tick and SystemCoreClock. The existing IRQ acquisition/teardown routines remain intact.
2. **Actual paired ISR evidence:** Existing `labmate_pulse_pair_audit` pairs are copied under `FURI_CRITICAL_ENTER/EXIT` in the app-thread measurement update. `labmate_doctor_pulse_observe_poll()` records when the paired publication count **increases**; it does not refresh timestamps for stale copies or UI redraws.
3. **STOP admission:** Pulse OK→HOLD (and Pulse BACK) calls `labmate_doctor_pulse_prepare_stop`, then the EXISTING `labmate_pulse_capture_stop` or `labmate_capture_stop_all`, then `labmate_doctor_pulse_finish_stop`. Source `labmate_input_measure.c` contains explicit before/after ordering. Mode/pin changes discard old evidence and never certify release on their own.
4. **Pure policy:** `labmate_doctor_pulse_policy_accept()` requires native owner, active IRQ and DWT cycle timebase, stable kernel/system frequencies, a coherent non-overflowed paired HIGH/LOW audit, matching app-observed publication count, a publication seen recently during the same session, fresh observed IRQ edge, nonwrapped observation times and valid 32-bit frequency conversion. Session age is capped at five minutes; last IRQ edge and last paired-publication observation must be within 500 ms. No missing-data timeout invents `NO SIGNAL`.
5. **Sealing:** `labmate_evidence_session_finish()` runs ONLY after the production STOP and checks inactive Pulse IRQ, empty capture ownership, no pending native lease, no sticky release fault, and no capture block. It publishes `VALID` only when old Phase2 snapshot/evidence gates also accept; otherwise `BUSY`, `CLOCK ERR` or `INSUFFICIENT`. Data enters the existing `LabMateDashboardStore`, read by the Phase3A doctor, without microSD/profile/IRQ writes.
6. **Lifetime:** New capture intent clears previous dashboard results. Settings remain user-specified (no implicit reference frequency). End-to-end support is **Pulse STOP only**; Frequency LOW/HIGH live publishing is not implemented and still shows NO SEALED DATA.

## Host evidence / boundaries

The 24-case pure Pulse policy (one admissible candidate and 23 negative cases) was executed in an isolated Linux host reproduction using GCC and Clang with C11, -Wall/-Wextra/-Werror/-pedantic and ASan/UBSan: two PASS outputs. The reproduction used a layout-equivalent local subset of the native pair observation type because this runtime cannot clone GitHub. The committed `scripts/test-v20-phase3c-pulse-host.sh` additionally compiles against the **real** repository header and runs source-link checks; **its exact full-source WSL execution is pending**. No FAP build or hardware results may be inferred from the pure test.

The existing `scripts/test-v20-offline-full-host.sh` now runs 22 Phase2L suites followed by Phase3A, Phase3B and Phase3C tests. The CI host workflow includes Phase3C, but no GitHub Actions run was observed at last check.

**NO-GO:** Stable 2.0, on-device app acceptance, live Frequency analysis, firmware install, USB flash, or overwriting Stable. A new pinned E11 FAP build, 128x64 on-device visual QA and Pulse end-to-end physical signal test are still mandatory.

## Reproduce without device writes

Fetch this branch's current full ZIP into a new folder; run:

```sh
sh scripts/test-v20-offline-full-host.sh
LABMATE_E11_WORK="$HOME/labmate-v20-phase3c-build-20261021" \
  bash scripts/build-v20-phase3b-e11-isolated.sh
```

Do not use the old Phase3B ZIP or old FAP: it does not contain this producer. The build wrapper will refuse to overwrite an existing output workspace. New working copy and original protected SDK remain separate.
