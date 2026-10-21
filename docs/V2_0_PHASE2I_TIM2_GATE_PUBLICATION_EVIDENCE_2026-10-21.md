# LabMate Ultimate v2.0 — Phase 2I PB3/TIM2 authentic published-gate audit

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor` into `dev/v1.9-logic-scope`, PR #21 **Open/Draft**.  
**Acceptance:** exact-source pure C host **PASS** (GCC 14.2/Clang 17, ASan + UBSan); full checked-out-repo workflow, E11 SDK FAP, real Flipper **PENDING / NO-GO**. No device/firmware/SD writes.

## 1. Real native source review and measurement rule

The existing `src/labmate_measurements.c` PB3/TIM2 high-frequency reader polls the hardware roughly every 100 ms, but **a poll is NOT a completed measurement**. The native `labmate_high_gate_evaluate()` in `src/labmate_frequency_gate.c` decides:

- **WAIT:** keep accumulating edges/time, no publication.
- **NoSample:** measurement window cannot publish a trustworthy value, no publication.
- **Publish:** a bounded edge-anchored count/time interval yielded a strictly positive millihertz result; the app updates the user-facing frequency.

A valid gate normally needs **at least 32 additional observed hardware edges**; or after roughly **3 seconds**, at least **2 additional edges**, with positive elapsed cycles and a safe native estimator. This permits slow-signal metrology without fabricating a period from the 100 ms poll interval.

Before Phase 2I the app had no separate monotonically increasing count of successfully published PB3 measurements. Neither `frequency_sample_count` (the LOW/PC1 rolling buffer) nor `edges` (raw TIM2 count) was an appropriate high-path publication sequence number.

## 2. Changes (intentionally narrow)

- **New `src/labmate_high_gate_audit.h`**: pure C, fixed-size `LabMateHighGateAudit` with successful publication count, last real hardware counter, published gate edge delta, elapsed CPU cycles, published millihertz and sticky counter-exhaustion state.
- **`src/labmate_internal.h`**: adds the audit as an internal `LabMateApp` field; tool IDs, menu order, profile/log formats and SDK API remain untouched.
- **`src/labmate_frequency_capture.c`**: invokes `labmate_high_gate_audit_reset` **only AFTER `labmate_frequency_tim2_configure()` succeeds**, while the counter is still disabled and **BEFORE `labmate_frequency_tim2_enable()`**. Failed/denied lease requests, STOP/BACK, HOLD and UI redraws do not reset it.
- **`src/labmate_measurements.c`**: saves `gate_edges` and `gate_cycles` before the existing window re-arm and records audit evidence **only within `if(gate == LabMateHighGatePublish)`**. The original native estimator and its WAIT/NoSample re-arm behavior are retained. A saturated or inconsistent publication audit cannot set the displayed `frequency_valid` to true; older valid display is invalidated rather than represented as new measurement.
- No change to `src/labmate_frequency_tim2.c`, DMA, native IRQ, PB3 GPIO configuration, TIM2 lease return, clock enable/disable ordering, or frequency LOW/Pulse calculations in this Phase 2I patch.
- The audit is **NOT YET used as a live Snapshot capture generation**, and it does not establish a successful TIM2 release or actual on-device metrology. It counts successful *app-thread publications*, not physical edges.

## 3. Exact GitHub identity

| Artifact | Git blob SHA |
|---|---|
| `src/labmate_high_gate_audit.h` | `a711574fa88bb63ca357f6e29a9ddfe554f5c527` |
| `src/labmate_frequency_gate.h` (unchanged) | `ccf0419523d00b410dda42ab202f263ae74cd0e1` |
| `src/labmate_frequency_gate.c` (unchanged) | `47059ba715a1297fde16c49ae8884929900f24c2` |
| `src/labmate_internal.h` | `118dd53214b9b7b2b1781e790099ba87eeaa8a59` |
| `src/labmate_frequency_capture.c` | `aa6c2021e99dfb717b04487c8619ec370838fb2f` |
| `src/labmate_measurements.c` | `92070be60da2a8c2d8326b68a8ec68da46381a8a` |
| `tests/test_v20_phase2i_high_gate_audit.c` | `47795aebb0413f241dda7ee9c28f9883dc4da618` |
| `scripts/test-v20-phase2i-host.sh` | `fb3096115dbb5a17fc466f4c83b76b2d44b19eda` |

The four files **actually compiled locally** — the real preexisting frequency gate header/source plus new audit header and test — were compared byte-for-byte to these exact GitHub Git blob SHAs using `git hash-object`. These are real production estimator functions and exact new audit functions, **not an imitation of the estimator**.

## 4. Actual execution

On an isolated Linux host with GCC 14.2 and Clang 17.0, the two source-identical binaries built and executed using:

```sh
gcc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc src/labmate_frequency_gate.c tests/test_v20_phase2i_high_gate_audit.c -o /tmp/labmate-phase2i-gcc
clang -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc src/labmate_frequency_gate.c tests/test_v20_phase2i_high_gate_audit.c -o /tmp/labmate-phase2i-clang
/tmp/labmate-phase2i-gcc
/tmp/labmate-phase2i-clang
```

Both exit status **0** and print:

```text
Phase2I PB3/TIM2 accepted-gate audit PASS: 1038 test groups
Phase2I PB3/TIM2 accepted-gate audit PASS: 1038 test groups
```

The groups comprise 1,024 successive real `labmate_high_gate_evaluate()` successful windows plus 14 explicit quality/boundary cases, including 100 ms non-events, partial gates, 1 Hz / 3-second gate, insufficient edges, WAIT/NoSample, duplicate TIM2 end-count, counter wrap scenario, malformed claimed Publish, zero clock, UINT32_MAX publication saturation and reset. The initial test counter assertion was corrected from 1,039 to the independently counted **1,038** before the successful local execution.

## 5. Reproducible repository runner and remaining gates

From a full repo checkout, run:

```sh
sh scripts/test-v20-phase2i-host.sh
```

This source-linked runner checks the real `LabMateApp` audit field, the **single** native TIM2-start reset, the **single** app-thread audit publication call, and **ordering**: configure before reset before enable; `Publish` before audit admission before showing a new rate. It compiles the same full production estimator and test on both host compilers with sanitizers. The runner and its sources are included in the read-only `.github/workflows/v20-ui-host-gates.yml` workflow's push/PR triggers and a new Phase 2I job step.

**Limitations not to conceal:** The complete checked-out-repository runner has **not yet been independently observed running**. This does not prove E11 SDK header/ABI compatibility, actual ISR race behavior, timing accuracy, physical TIM2 counter gate boundaries, successful native lease release, or a usable Dashboard screen. GitHub Actions has shown **0 runs** in recent checks; a configured YAML gate is not a green CI check.

**Next safe work:** perform all integrated host/E11 compilation gates, implement Pulse HIGH/LOW coherent completed-publication identity, and only then attach real producer evidence to the versioned Snapshot/Dashboard. Never substitute a 100 ms polling count or a display validity flag for physical acquisition evidence.

**Phase 2I pure-model gate: PASS. Actual Flipper device and v2.0 Stable: NO-GO.**
