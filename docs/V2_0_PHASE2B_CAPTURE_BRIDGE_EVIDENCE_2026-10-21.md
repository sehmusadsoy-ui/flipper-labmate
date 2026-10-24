# LabMate Ultimate v2.0 — Phase 2B, Frequency/Pulse evidence bridge

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor` → Draft PR #21, base `dev/v1.9-logic-scope`  
**Result:** **Pure C source-identical host PASS — 283 cases with GCC and Clang.**  
**Integration gate:** **PENDING**. Neither actual Flipper capture callbacks nor the on-device Dashboard menu are wired to this API.

## 1. Existing measurement source audit

The E11 v1.9 development code was inspected directly, before constructing the bridge:

- `src/labmate_internal.h` Git blob `ade05ed99bbc4335b6428ba69cbd736395d290b2`: the actual `LabMateApp` display-side Frequency state includes `frequency_millihz`, `frequency_valid`, `frequency_sample_count`, `edges`; Pulse has `pulse_high_cycles`, `pulse_low_cycles`, `pulse_period_cycles`, `pulse_duty_permille`, validity bits, and separately IRQ-owned `pulse_irq_edges`. High-frequency Frequency uses a **separate PB3/TIM2 gated counting path**.
- `src/labmate_measurements.c` Git blob `0a001602ea7344db1f7b5345253c0e1cb348517e`: Frequency low path derives averaged completed periods, high path uses real counted TIM2 gate intervals. Pulse obtains a coherent high/low/edge snapshot under `FURI_CRITICAL_ENTER/EXIT`. The display-side `frequency_valid` or `pulse_period_valid` flags alone do **not** certify a new capture-generation identifier, same-epoch start/end times, lossless observation count, or successful lease teardown.
- `src/labmate_pulse_math.c` Git blob `255780e347ce75d67f7b1c8f1ddc419b34687585`: checked the exact `high+low` overflow limit and nearest-permille duty calculation. The bridge deliberately reuses this same deterministic arithmetic; 0%/100% pulse duty are not rejected solely for having a zero HIGH/LOW component.
- Legacy GPIO index order remains unchanged (PC1 = 1, PB3 = 4). The adapter refuses Frequency on other pins. Pulse remains selectable on the existing pin array.
- `src/labmate_scope_buffer.h` Git blob `ac8778961fc6d8a6d88b4581b8e968bd71830eb4` exposes real Scope buffer snapshots with overflow/timebase flags, but timebase/ownership/session semantics require separate analysis. **Scope, Counter and Logger are explicitly NOT supported by this first bridge.**

## 2. New code and precise contract

`src/labmate_snapshot_bridge.h/.c` defines `LabMateCaptureEvidenceV1` and `labmate_snapshot_bridge_from_capture()`. This is a *handoff API*, not a new data-acquisition or ISR implementation.

- Requires caller-provided **genuine** `capture_generation`, monotonic observation start/end, capture timebase, `completed_sample_count`, `observed_edge_count`, drop/overflow/clock flags, current measurement validity, and **successful ownership/IRQ release evidence**. These fields cannot be fabricated from `LabMateApp`'s held screen values.
- Maps only verified **Frequency and Pulse** observations. The helper does not read Flipper application state, GPIO hardware, DWT, TIM2 or ISR fields and never starts PWM.
- Priority is safe: `BUSY` when still owned or resource blocked, `CLOCK ERR` for unknown/unsafe timebase, `OVERFLOW` for edge drops/overflow, `NO DATA` for incomplete samples, `INVALID` for contradictory values, and `VALID` only with all required evidence.
- Frequency uses the **measured published millihertz**. A zero `period_ticks` remains legitimate for the PB3/TIM2 path; it is **not** synthesized from the current display rate.
- Pulse verifies `HIGH + LOW == PERIOD` using 64-bit intermediates, matches the v1.9 rounded duty-permille equation, and calculates its displayed frequency in millihertz using the **caller-provided actual timer frequency**, with overflow protection.
- All results go through the Phase 2A `labmate_snapshot_v1_well_formed` and `labmate_snapshot_v1_can_display_measurement` checks. Invalid pointers/IDs/generations or reversed timestamps leave the output untouched.
- The adapter never infers an electrical `NO SIG` finding from 0 edges. Silence requires separately established acquisition duration/evidence.

**Important limitation:** There is no safe automatic source of all these mandatory facts in the current producer state. Connecting only current `frequency_valid`/`pulse_period_valid` directly would create a false VALID reading. **Do not wire the bridge into live rendering until actual source-specific capture generations, completed observations and successful teardown are instrumented and tested.**

## 3. Exact source and test artifacts

| File | Verified Git blob |
|---|---|
| `src/labmate_snapshot_bridge.h` | `4013ac338b6b7f382e8061b715104e85809a6550` |
| `src/labmate_snapshot_bridge.c` | `8a97b7f28e2079cbf1a816740ecd8c679fd59d9f` |
| `tests/test_v20_snapshot_bridge.c` | `64d1389701231d7d97c523a44c3fe783164393ac` |
| `scripts/test-v20-phase2b-host.sh` | `278d475ac1ab99ae270d3c3ef280e5be009ec57b` |

Each GitHub file was read back and compared to `git hash-object` on the **exact local file actually compiled**.

## 4. Actual execution

Run the exact branch checkout on Linux/WSL:

```sh
sh scripts/test-v20-phase2b-host.sh
```

Both GCC and Clang compile `labmate_snapshot.c`, `labmate_snapshot_bridge.c`, `labmate_dashboard_store.c` and the committed bridge test in a **single linked executable**. Compiler options: C11, strict warnings-as-errors, `-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`.

Observed actual local output, both compilers exited 0:

```text
Phase2B snapshot bridge PASS: 283 cases
Phase2B snapshot bridge PASS: 283 cases
```

These cases include genuine field-formula examples for 100 Hz Frequency and 1 kHz / 50% Pulse, 0% and 100% edge-case duty, PB3/TIM2 zero-period handling, clock failure, busy/unreleased ownership, lost edges, overflow, missing/zero samples, inconsistent pulse arithmetic, bad pins/IDs, and 255 consecutive valid generation values. A later BUSY observation is passed into the actual Dashboard store and verified to suppress the preceding VALID Pulse value. All negative structural inputs preserve the previous output object.

**No physical oscilloscope calibration, actual on-device E11 FAP build, Flipper firmware flash, SD write, or live Dashboard update is included.**

## 5. Acceptance decision and next step

- **Phase 2B handoff API, pure C host: PASS.**
- **Live Frequency/Pulse producer instrumentation:** PENDING — preserve correct critical sections, original resource ownership/teardown and capture generation epochs.
- **Scope/Counter/Logger adapters:** PENDING — do not map unknown fields onto misleading metrics.
- **UI-06 integrated full repository regression:** PENDING.
- **GitHub Actions:** a read-only `Phase 2B` job step has been added to `.github/workflows/v20-ui-host-gates.yml`; no confirmed green workflow run yet.
- **E11 SDK physical device, mainline normal Momentum compatibility, v2.0 Stable:** NO-GO.

Existing published v1.8 ordinary and v1.9 E11 Stable versions, legacy CSV and S1–S3 Profile/CRC formats, native IRQ leases, installed firmware and Flipper microSD contents remain unchanged.
