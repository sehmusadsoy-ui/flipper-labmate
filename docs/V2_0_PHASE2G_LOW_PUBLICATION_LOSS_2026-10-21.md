# LabMate Ultimate v2.0 — Phase 2G: PC1 ISR publication and overwrite audit

**Date:** 2026-10-21  
**Development:** `dev/v2.0-signal-doctor` → PR #21 Draft, base `dev/v1.9-logic-scope`.  
**Status:** **Pure C host PASS**; native ISR source instrumentation committed. E11 SDK/full application build, hardware IRQ behaviour and end-to-end Dashboard **PENDING / NO-GO**.

## 1. Exact original problem and narrow mitigation

The v1.9 PC1 LOW ISR at `src/labmate_frequency_capture.c` sends each completed slow per-edge period or 32-period fast average through **one** volatile `frequency_irq_period_cycles` field and a single `frequency_irq_new_period` boolean. When the app thread has not yet acknowledged an earlier publication, a second IRQ publication **replaces** it. Phase 2F made flag/value read-and-clear atomic, but that alone cannot detect coalesced publications.

Phase 2G **does not** add a queue, change filtering, make every IRQ a distinct measurement, or change the peripheral API. Instead it installs bounded, ISR-owned evidence:

- `publications`: increments once for **each completed period publication**, not every raw edge. Both actual ISR publication sites call the audit helper before replacing the value/flag.
- `overwrites`: increments only when the old pending flag is already set when a new period is published. This counts an observed replacement of an unread **publication slot**.
- `exhausted`: sticky when publication or overwrite counters would wrap `UINT32_MAX`. Values saturate, rather than silently wrapping and masquerading as a fresh generation.
- Reset occurs only in the existing **successful LOW native-start path after callback delivery has been disabled and ownership has been acquired**, before the callback is re-enabled; not in `measurement_reset`, HOLD, log refresh, menu rendering or failed lease acquisition.

## 2. Production files changed

| File | Exact verified Git blob |
|---|---|
| `src/labmate_low_mailbox_audit.h` | `108240417430d594406f81ebe25f574691eae582` |
| `src/labmate_internal.h` | `3595c99a10ee6d267e55ecaa3f7c0b9f311ffbb8` |
| `src/labmate_frequency_capture.c` | `c29fa7dd6d42f3fbb6789a9d9df54e9c9d436a41` |
| `tests/test_v20_phase2g_low_audit.c` | `bc71d88cbf8735d556ddbf41730eb67d1f05f17d` |
| `scripts/test-v20-phase2g-host.sh` | `f1e43114320f6a662ed355233b7ff7eac0c9001c` |

**Important:** The ISR has exactly **two** `labmate_low_mailbox_publish()` calls (slow published period and fast 32-period averaged publication). The successful LOW start has exactly **one** `labmate_low_mailbox_reset()` call. The script checks their presence and confirms the audit struct exists in the real `LabMateApp`.

This is an **internal state-layout change on the v2.0 dev branch**, not a backwards-compatible external ABI assertion; successful pinned E11 SDK compilation and physical validation remain necessary. No changes were made to `src/labmate_measurements.c` during Phase 2G, preserving the Phase 2F atomic mailbox reader.

## 3. Actual verified local test

The new production header and host test were compared byte-for-byte against the GitHub blobs using `git hash-object`:

```text
108240417430d594406f81ebe25f574691eae582  src/labmate_low_mailbox_audit.h
bc71d88cbf8735d556ddbf41730eb67d1f05f17d  tests/test_v20_phase2g_low_audit.c
```

The two exact files were compiled in a Linux host fixture using **GCC** and **Clang** with `-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer`. Both executions returned **0**, each printing:

```text
Phase2G PC1 publication audit PASS: 8192 ISR messages, 2048 detected overwrites, saturating counters
```

The deterministic host simulation models consumption and ISR publication timing, checks 8,192 publications, 2,048 unread-slot overwrites, the last pending period, reset behaviour, NULL safety, publication counter saturation, overwrite counter saturation and sticky overflow quality.

The updated **whole-repository** runner is:

```sh
sh scripts/test-v20-phase2g-host.sh
```

It additionally runs Phase 2F's existing source-extracted 4,106-state atomic mailbox test. **The entire runner has not been shown executing on a complete checkout and GitHub Actions success has not been observed.** Do not infer E11 SDK, physical IRQ safety, or integrated PR green CI from the isolated header test.

## 4. Explicit limitations and next acceptance gates

1. These are counts of **software ISR publications and known mailbox replacements**, not a direct count of physically missed rising edges. Lost EXTI edges, CPU timing skew, bad input signal, and external lease conflicts are not independently measured.
2. The optional `labmate_low_mailbox_detected_loss` accessor must be used only with a coherent IRQ-excluded snapshot; there is **no live Dashboard attachment yet**. In particular, a return value of false does not certify lossless hardware delivery or permission to classify a reading `VALID`.
3. The old mailbox retains **one latest pending period**, not a FIFO. Phase 2G detects a replacement but cannot reconstruct the overwritten data. A future fail-closed production handoff must incorporate this information into the freshness/overflow quality.
4. `publications` counts completed ISR publications, including the 32-period aggregate case; it is **not** a monotonic per-physical-period count. Don't feed it into `completed_sample_count` as though each represents one physical cycle without a formal contract.
5. HIGH/PB3/TIM2 has a separate native gate and needs its own actual `LabMateHighGatePublish` event count, not inference from polling cadence.
6. Before a live Dashboard: critically snapshot counters and period together, verify native resource ownership and teardown, run full host suite, build with pinned E11 SDK, perform real on-device display/STOP/BACK and PA7→PC1 loopback tests.

**Decision:** Phase 2G ISR publication/overwrite instrumentation **committed, isolated host PASS**. Live sensor-proven snapshot and v2.0 Stable **NO-GO**.
