# LabMate Ultimate v2.0 — Phase 2H PC1 coherent mailbox provenance and Snapshot quality

**Date:** 2026-10-21  
**Development:** `dev/v2.0-signal-doctor` → PR #21 (Open/Draft), base `dev/v1.9-logic-scope`.  
**Gate:** **Production-function-identical isolated host PASS**, full repository CI/E11 SDK/Flipper hardware **PENDING / NO-GO**. No firmware, Stable, FAP, SD/CSV or Profiles changes.

## 1. Change and safety rationale

Phase 2G introduced IRQ-owned `frequency_low_mailbox_audit` counters for completed PC1 publications and cases in which a new ISR period replaced an unread mailbox value. The Phase 2F consumer originally read the period and acknowledged the flag atomically, but it **did not read the audit counters in that same critical section**. A later read could attach counters from a later ISR update to an earlier consumed period.

The new `LabMateLowMailboxObservation` is a fixed-size app-thread snapshot with `has_period`, `period_cycles`, `publications`, `overwrites`, and `exhausted`. The pure-C `labmate_low_mailbox_consume_locked()` copies **all five** while the native caller has `FURI_CRITICAL_ENTER()` active; only then does it acknowledge the pending flag. Empty mailbox observations are explicit, have zero reported period, and still carry the audit counters.

The real `src/labmate_measurements.c` `labmate_frequency_low_take_period()` now uses that helper and stores the coherent value in `app->frequency_low_last_observation`. Existing averaging/statistics/period-to-mHz math, the physical IRQ ISR, TIM2 high-frequency operation and GPIO resource ownership are not changed by this consumer refactor. `src/labmate_frequency_capture.c` also clears the **app-thread observation** on a verified new LOW native capture start (beside the existing audit reset), not on HOLD or display refresh.

The app-thread snapshot does **not** independently prove release of the native IRQ/lease or a complete measurement epoch, and no live Dashboard binding was added.

## 2. Fail-closed quality bridge (not yet attached to live Dashboard)

Added `src/labmate_low_mailbox_evidence.h`, a pure-C helper `labmate_low_mailbox_apply_evidence()` for **LOW Frequency / PC1 only**. It modifies a caller-supplied Phase 2B `LabMateCaptureEvidenceV1`, which still must contain actual start/end, generation, timebase, completed samples, physical edge counts, and successful resource release:

- Any **observed overwritten publication** or counter saturation sets `evidence.overflow = true`, so the existing Snapshot bridge produces **`LabMateSnapshotOverflow`** when no higher-priority BUSY/CLOCK condition exists.
- No pending period or no ISR publication forces `measurement_valid = false`, preventing a stale UI value from becoming numeric `VALID`.
- For non-PC1 Frequency and Pulse, or missing arguments, it **refuses without changing the evidence**.
- It does **not infer the number of missed physical rising edges**. The `dropped_edge_count` is left unchanged; an unread mailbox overwrite is only proven coalescing of **completed ISR publications**.
- BUSY (unreleased or denied lease) and CLOCK ERR retain the existing higher-priority refusal semantics.
- Zero overwrites and no exhaustion **do not** prove accurate device metrology or valid physical provenance. The helper is not called by any live producer yet and grants no standalone `VALID` status.

## 3. Exact source hashes, reproducible execution

| Updated / new artifact | Verified Git blob |
|---|---|
| `src/labmate_low_mailbox_audit.h` | `9f057778ecfbb9271bdd4e88be972c86495e17e2` |
| `src/labmate_low_mailbox_evidence.h` | `b5c75c2f48485c73c652bf01ffb875554572357d` |
| `tests/test_v20_phase2f_low_mailbox.c` | `dea01a3c8e6139196c07d6217b89ffa182f1ecf4` |
| `tests/test_v20_phase2h_loss_quality.c` | `f650df8c0a12f59b9ff009adeb24407ed283fe16` |
| `src/labmate_measurements.c` | `d99bf9eb5e7a55a5d2ea0b5019b762eec2b2c086` |
| `src/labmate_internal.h` | `46e278830f065b7004211aa68667fc3e563efde7` |
| `src/labmate_frequency_capture.c` | `0def4c0e82e71ebccf67438aa1418dc3e3f0e3d9` |

The **exact live** `labmate_frequency_low_take_period()` production function was independently compared against the local executable source fragment: **705 characters, CRC32 `18a6c326`** (no trailing line break). New pure headers and C fixtures had matching local `git hash-object` and connected GitHub blob values.

Actual isolated host runs with GCC 14.2 / Clang 17, strict C11 `-Wall -Wextra -Werror -pedantic -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`:

```text
Phase2F LOW atomic IRQ mailbox PASS: 4107 deterministic states
Phase2F LOW atomic IRQ mailbox PASS: 4107 deterministic states
Phase2G PC1 publication audit PASS: 8192 ISR messages, 2048 detected overwrites, saturating counters
Phase2G PC1 publication audit PASS: 8192 ISR messages, 2048 detected overwrites, saturating counters
Phase2H PC1 overwrite -> Snapshot OVERFLOW PASS: 1036 quality cases
Phase2H PC1 overwrite -> Snapshot OVERFLOW PASS: 1036 quality cases
```

Phase 2F's expanded mock includes simulated IRQ delivery immediately **before** critical entry and **after** critical exit, and verifies the consumed value's audit belongs to its own IRQ-excluded snapshot even if a subsequent publication becomes pending. A deliberately coalesced pair is explicitly marked with one overwrite. The 1,036 quality scenarios cover loss/no loss, counter saturation, missing publication, BUSY/CLOCK prioritization, invalid pins/sources and a 1,024-value overwrite matrix. The Phase 2G audit's original 8,192-publication regression was also re-run and passed on both compilers with the updated pure audit header.

To reproduce in a **complete** branch checkout:

```sh
sh scripts/test-v20-phase2h-host.sh
```

The new runner source-checks the live consumer, app state and epoch reset, runs Phase 2G/2F, and compiles the Phase 2H Snapshot-quality test using full `labmate_snapshot.c` and `labmate_snapshot_bridge.c` production translation units. It was added to the read-only GitHub workflow's push/PR path filters and execution steps. **The new end-to-end whole-repository runner has not yet been independently observed running in a full checkout; workflow YAML is not a green GitHub Actions result.**

## 4. Remaining acceptance debts

1. Physically anchored capture epochs, monotonic *completed* LOW publication evidence, edge counters and actual lease teardown must be recorded by the real native producers and passed to the Snapshot bridge, with source-specific start/stop proof.
2. The app-thread observation must not be reused across HOLD/menu changes or treated as a validated capture generation. The live Dashboard is not yet bound to it.
3. Frequency HIGH PB3/TIM2 needs its own successfully published hardware gate accounting. Pulse needs coherent HIGH/LOW provenance, retaining 16/128-width IRQ averaging and resource safety.
4. Build and integration-test the whole `LabMateApp` translation units against the **pinned E11 SDK** and then on a real Flipper. A deterministic host IRQ-interleaving mock cannot certify actual EXTI timing, missed physical edges, clock accuracy or FAP ABI compatibility.
5. Preserve v1.8 normal-Momentum / v1.9 E11 Stable, firmware, installed FAP, original resources, CSV logs and Profiles data. Normal Momentum support is a separate workstream.

**Phase 2H isolated host gate: PASS. Live Snapshot publication and v2.0 Stable: NO-GO.**
