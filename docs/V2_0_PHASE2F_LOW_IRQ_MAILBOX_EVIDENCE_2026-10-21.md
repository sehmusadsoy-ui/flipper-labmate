# LabMate Ultimate v2.0 — Phase 2F: PC1/EXTI LOW atomic mailbox

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor`, PR #21 remains **Open / Draft**, base `dev/v1.9-logic-scope`.  
**Decision:** **Isolated source-identical host safety test PASS**. **E11 SDK/full firmware, Actions and physical Flipper acceptance PENDING.** Stable v1.8/v1.9 and device files untouched.

## Discovered race in real native app-thread path

Original `src/labmate_measurements.c` Git blob `0a001602ea7344db1f7b5345253c0e1cb348517e` consumed the LOW/PC1 ISR mailbox using three separate steps without one IRQ exclusion scope:

```c
if(app->frequency_irq_new_period) {
    period_cycles = app->frequency_irq_period_cycles;
    app->frequency_irq_new_period = false;
    /* Existing low-frequency math follows. */
}
```

A new ISR publication between reading `period_cycles` and clearing `frequency_irq_new_period` can be acknowledged without ever being consumed. This risk matters when introducing strictly increasing published-sample evidence; counting `frequency_sample_count` as a hardware total would not solve it.

The existing `src/labmate_frequency_capture.c` ISR publishes the period field and `frequency_irq_new_period` while owning PC1/EXTI. We did **not** change that ISR, its 32-period averaging, pin configuration, FURI HAL leases, timer timing, HOLD semantics or the existing 8-slot app-thread frequency average.

## Production correction, narrowly scoped

`src/labmate_measurements.c` now uses a file-static `labmate_frequency_low_take_period(LabMateApp*,uint32_t*)` helper:

- Reject NULL arguments without altering output or entering a critical section.
- Enter `FURI_CRITICAL_ENTER()`.
- Copy publication flag and, **if pending**, copy the matching volatile period and clear the flag before `FURI_CRITICAL_EXIT()`.
- Return the captured pending status; leave output unchanged if there was no pending data.
- Continue the **unchanged** period validity check, averaging, frequency conversion, statistics and display handling outside the critical section.

The critical section only covers the flag/period copy/ack, not formatting, filtering or UI. It neither creates a genuine monotonic completed-period counter nor verifies firmware lease return.

**Actual GitHub readback:** updated full `src/labmate_measurements.c` Git blob **`93aa8bd9cc47a0a201cde068fd852e9e22c96397`**. The extracted production helper body has **402 characters**, **CRC32 `d801aef7`**. Its contents are byte-for-byte equal to the independently compiled local fixture.

## Regression test and reproducibility

- `tests/test_v20_phase2f_low_mailbox.c` — exact tested Git blob `77bec89ca86b76e4500c18becf12dbed5499e76d`.
- `scripts/test-v20-phase2f-host.sh` — extracts the **actual** helper from the current `src/labmate_measurements.c`, checks that `measurement_update` calls it, and compiles GCC/Clang host binaries with `-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer`.
- Simulated ISR interleavings use a minimal deterministic critical-section mock. These exercise publication before disable, publication at critical exit, no pending message, delayed message consumed by the next poll, zero period, bad pointers, and a 4096-iteration alternating arrival matrix.

Both **GCC 14.2 and Clang 17** compiled and executed the byte-identical helper and test with exit code **0**. Each printed:

```text
Phase2F LOW atomic IRQ mailbox PASS: 4106 deterministic states
```

Independent GitHub source readback confirms the current LIVE code calls `labmate_frequency_low_take_period(app, &period_cycles)`. The runner also checks that integration point. The sanitizer mock cannot prove a physical STM32 interrupt preemption rate, E11 SDK compatibility, full application compilation or lossless queueing: the mailbox remains **one latest pending period**, which may coalesce multiple ISR publications at very high rates. The test demonstrates atomic acknowledgement of the one pending mailbox value, not precise IRQ-by-IRQ counting.

From a complete checkout:

```sh
sh scripts/test-v20-phase2f-host.sh
```

The read-only `.github/workflows/v20-ui-host-gates.yml` now includes the Phase 2F host step, and triggers on changes to `src/labmate_measurements.c` and the new runner. **A workflow definition is not proof of a successful GitHub Actions run.**

## Deliberately postponed integration gates

1. **Frequency LOW:** define monotonic published-observation generation and loss/overwrite detection; decide explicitly whether coalescing can be tolerated for the Dashboard's freshness contract. Do not count the rolling average buffer as a total.
2. **Frequency HIGH:** count authentic `LabMateHighGatePublish` events only after valid TIM2 gates; do not derive event counts from ~100 ms polls.
3. **Pulse:** publish a coherent HIGH/LOW epoch with correct critical-section synchronization and preserve the existing high-speed 16/128 width processing.
4. **STOP/BACK and resource ownership:** prove actual callback removal, native lease return and TIM2 pending-handle state before any `released=true` snapshot.
5. **Independent gates:** run full checked-out repository GCC/Clang host suite, compile against the pinned E11 SDK, review real on-device LCD/input and run physical PA7→PC1 loopback. Normal Momentum support stays a separate workstream.

**Phase 2F narrow native-path atomicity host PASS. Full publication provenance / live Dashboard / v2.0 Stable: NO-GO.**
