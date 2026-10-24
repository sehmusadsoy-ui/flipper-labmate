# LabMate Ultimate v2.0 — Phase 2E native-publication accounting preflight

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor` → Draft PR #21 into `dev/v1.9-logic-scope`.  
**Gate:** **Isolated pure C host PASS (81 boundary checks on each of GCC 14.2 / Clang 17.0, ASan + UBSan).**  
**Live firmware/physical integration:** **NO-GO / PENDING.** Not an on-device waveform validation.

## 1. Actual E11 source audit

Three real source paths have different publication semantics and must **not** reuse one assumed `frequency_sample_count` as if it were a hardware total.

| Existing native path | Authoritative publication condition | Essential unresolved proof |
|---|---|---|
| LOW Frequency, PC1 / rising-edge EXTI | App thread consumes `frequency_irq_new_period` and successfully computes a positive `labmate_low_period_to_millihz` result | The ISR publishes period data asynchronously; the current reader copies/clears the flag without a critical section. Need coherent IRQ handoff and a new **monotonic completed-publication counter**, not the 8-entry rolling `frequency_sample_count` |
| HIGH Frequency, PB3 / TIM2 | `labmate_high_gate_evaluate` returns **`LabMateHighGatePublish`** for genuine counter/time-gate boundaries | `edges` is a hardware counter display. Need an explicit unique successful-gate counter, monotonic epoch, true observed TIM2 boundary values and independently proven lease return |
| Pulse, PC0 / PC1 / PB2 / PA4 | IRQ HIGH/LOW widths and validity are read under `FURI_CRITICAL_ENTER/EXIT`; derived period/duty are valid | HIGH/LOW can become valid at different times in ordinary averaging mode. Need proof of one consistent completed publication epoch; UI `pulse_period_valid` alone is insufficient. Do not infer exact completed-period counts from the edge count |

Exact source blobs read from GitHub: `src/labmate_measurements.c` `0a001602ea7344db1f7b5345253c0e1cb348517e`, `src/labmate_frequency_capture.c` `08c826e5095ae77f902df351fa122877da5b1258`, `src/labmate_pulse_capture.c` `a8cf92851cd27c2bbd05ced40260041419cb5509`, `src/labmate_frequency_tim2.c` `689e9f2c238eba9243e6a49f6d243bdb510f51d6`. The existing proven native acquisition/lease implementation was **not modified**.

## 2. New source-path-specific admission module

Added `src/labmate_publication_gate.h/.c`: a small no-heap standard-C **app-thread observation gate**, with no Flipper SDK headers, ISR callbacks, resource operations, device writes or allocations.

- Allows LOW on **PC1 index 1**, HIGH on **PB3 index 4**, Pulse on **PC0/PC1/PB2/PA4 indices 0/1/3/5**. All 8 pins are cross-checked against the Phase 2C snapshot bridge for both measurement families.
- `begin` requires an actual independently confirmed owner and refuses repeated starts or invalid pins. The boolean supplied by caller is not independent lease proof.
- `observe` returns **WAIT** if the genuine producer has not published a new completed observation; no counters advance.
- A published LOW result needs nonzero period/frequency, initial 2 rising edges and at least one fresh edge after the previous accepted publication.
- A published HIGH result needs the genuine measured positive rate, `period_ticks=0` (no invented CPU-edge period), and a higher TIM2 edge count after a unique successful gate.
- A published Pulse result needs a coherent HIGH+LOW pair with 64-bit sum equality, v1.9-rounded duty, initial 3 real edge observations and at least two new transitions per subsequent completed pair.
- Same/reversed timestamp, repeated or wrapped edge counter, malformed duty/period, missing clock safety, or publication inconsistency **poisons the gate**, preventing a stale result from reappearing as new.
- `accepted_publications` is **count of accepted output events**, NOT proof of the number of raw hardware periods. This module deliberately does **not** call `labmate_evidence_session_record` or synthesize completed ISR period totals.

**Trust boundary:** a malicious, buggy, or uninformed producer can still set `native_publication_confirmed=true` without a genuine event. The helper only checks internal consistency; it cannot prove actual GPIO edges, sampling coherence, safe native resource acquisition or lease release. Therefore this module is *not yet wired to live capture or Dashboard*.

## 3. Exact bytes and host results

New files were locally compiled from precisely the same bytes as verified GitHub Git blobs:

| Artifact | Exact Git blob SHA |
|---|---|
| `src/labmate_publication_gate.h` | `ea2316056b596ea13e0a324dbea77ee8969a7184` |
| `src/labmate_publication_gate.c` | `44baf8ba776a305b5e1eed977c6ba28a65f79d01` |
| `tests/test_v20_publication_gate.c` | `47074c48975f4bdc40cc0222f89d5bd2b1e65dd3` |
| `scripts/test-v20-phase2e-host.sh` | `1c896971b393583089714f1824104dd8358e8e6c` |

The host test links the **exact Phase 2C `labmate_snapshot.c` and `labmate_snapshot_bridge.c`**, in addition to the new full publication-gate translation unit. On local Linux, `sh scripts/test-v20-phase2e-host.sh` built both binaries under strict C11 with `-Wall -Wextra -Werror -pedantic -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`.

Actual result (one line per compiler), both exit **0**:

```text
Phase2E native-publication admission PASS: 81 boundary checks
Phase2E native-publication admission PASS: 81 boundary checks
```

Coverage: 24 path/pin cases, 16 bridge-policy consistency checks, refused starts, duplicate start, WAIT without mutation, valid publications, repeated/frozen edge samples, reversed/equal clock, lost clock, malformed frequency/high TIM2 period, contradictory Pulse duty, counter wrap and sticky fault. The previously retained Phase 2C and Phase 2D isolated runners were also executed locally and passed; that is **not** a substitute for a complete GitHub checkout / CI run.

## 4. Current workflow and next safe step

Read-only `.github/workflows/v20-ui-host-gates.yml` now adds a Phase 2E host step and includes the two new source files and runner in push/PR path filters. Its definition **does not prove GitHub Actions executed**, and the E11 SDK build remains unverified.

Before any live integration:

1. Instrument actual LOW publication under **correct IRQ critical sections**; preserve the existing 32-period ISR averaging and 8-item app-thread statistics, but count genuine completed publications independently.
2. Record HIGH `LabMateHighGatePublish` events in the app thread from authentic TIM2 count and DWT gate boundaries; do not treat ~100-ms polls as completed measurements.
3. Produce a coherent Pulse HIGH/LOW publication identity without resetting or racing EXTI-owned accumulators. Do not use the raw pin display/flags as generation evidence.
4. Verify native **start** and **teardown** including GPIO callback detach, lease return and TIM2 pending-handle flags. No `released=true` from merely clearing `active`.
5. Compile/test against the **pinned E11 SDK**, then inspect in Flipper on actual 128×64 display and run hardware loopback; never replace the stable FAP or rewrite microSD until separately authorized.

**Release gate:** Phase 2E *isolated host PASS*; complete CI, E11 ABI, live publisher integration and physical tests **PENDING / v2.0 Stable NO-GO**.
