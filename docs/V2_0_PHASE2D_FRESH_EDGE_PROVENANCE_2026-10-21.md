# LabMate v2.0 — Phase 2D fresh-edge provenance, red-green host gate

**Date:** 2026-10-21  
**Development:** `dev/v2.0-signal-doctor` → Draft PR #21 (base `dev/v1.9-logic-scope`)  
**Gate:** **HOST PASS** for source-level anti-replay correction, **LIVE PRODUCER INTEGRATION NO-GO**.  
**Hardware, SD, firmware, Stable:** no writes or release modifications.

## 1. Genuine missing proof discovered

Before modifying code, audited existing E11 v1.9 capture sources:

| Producer | Actual capture evidence | Why old UI fields cannot safely certify a fresh snapshot |
|---|---|---|
| Frequency LOW, PC1/EXTI | `frequency_irq_edges`, `frequency_irq_new_period`; app-thread average of up to eight period samples | `frequency_sample_count` is a bounded rolling count, **not** a monotonic completed-period total. ISR edge and app-thread sample evidence need a coherent handoff |
| Frequency HIGH, PB3/TIM2 | TIM2 counter at ~100-ms polls; `LabMateHighGatePublish` events after genuine counter boundaries | `frequency_sample_count` is not updated for this path; current `edges` is a counter display value, **not** a verified per-session gate-completion count |
| Pulse, PC0/PC1/PB2/PA4 | IRQ edge count, high/low widths, validity bits; `measurement_update` copies IRQ fields inside `FURI_CRITICAL_ENTER/EXIT` | Display validity alone does not certify a completed period, monotonic report generation, independent timestamp epoch, or successful teardown |
| Lease teardown | Frequency and Pulse stop routines; sticky fault flag and lease handles; TIM2 `labmate_frequency_tim2_lease_pending()` | Active=false, HOLD, or changed menu must **never** be substituted for *confirmed release of the actual native lease* |

Source Git blobs inspected: `labmate_measurements.c` = `0a001602ea7344db1f7b5345253c0e1cb348517e`; `labmate_frequency_capture.c` = `08c826e5095ae77f902df351fa122877da5b1258`; `labmate_pulse_capture.c` = `a8cf92851cd27c2bbd05ced40260041419cb5509`; `labmate_frequency_tim2.c` = `689e9f2c238eba9243e6a49f6d243bdb510f51d6`. No firmware producer source was edited.

## 2. Reproduced failure (RED)

Found an anti-replay flaw in the new Phase 2C helper: it accepted a **higher completed-sample counter with an unchanged physical edge counter**. That could allow a stale capture reading to be described as a fresh completed observation.

A new `tests/test_v20_evidence_freshness.c` host regression was executed against the **unchanged Phase 2C code**, producing the expected failure before the source edit:

```text
RED_EXIT=134
Assertion '!sample(&s, 2U, 2U)' failed.
```

This is a host-code regression, not a reported failure of a released Stable binary or an on-device capture.

## 3. Minimal correction

In `src/labmate_evidence_session.c`, each newly reported completed sample now requires:

- The cumulative completed-sample count strictly increases (existing gate).
- At least **two physical observed edges** for an initial complete observation.
- The cumulative observed-edge count **strictly increases** over the last accepted sample (new gate).
- Dropped-edge count never goes backwards; the existing sticky poison mechanism remains unchanged.
- An edge-counter rollover cannot be mistaken for a new sample within the same capture generation. The native producer needs a fresh explicitly verified acquisition epoch.

A violation poisons the session; at STOP a previously accepted value cannot be exposed as `VALID`. This change touches **only the pure-C evidence consumer**; not the E11 IRQ, TIM2, GPIO, resource leases, Profiles, CSV or any Live measurement code.

## 4. Actual GREEN results and source identity

Exact locally compiled bytes were verified with Git blob hashes against the connected GitHub readback:

| Artifact | SHA-1 Git blob |
|---|---|
| New `src/labmate_evidence_session.c` | `411d693fb3e5b12fea359403177db6db31c25363` |
| Updated `src/labmate_evidence_session.h` (clarified lifetime contract) | `59fe2c29c6a0092730143c5025d591047822dade` |
| New `tests/test_v20_evidence_freshness.c` | `66df3366975638cb55d64e2da0eb0f108f95dba3` |
| New `scripts/test-v20-phase2d-host.sh` | `fd8e1f603e10bdc1c26ede9087096875e5eec6e5` |

Actual command from isolated locally source-identical directory:

```sh
sh scripts/test-v20-phase2d-host.sh
```

Compiler matrix: GCC 14.2 and Clang 17; strict C11 `-Wall -Wextra -Werror -pedantic`, `-O1 -g`, AddressSanitizer and UndefinedBehaviorSanitizer. Both compiler executions exited **0**. Observed output, per compiler:

```text
UI-Phase2C strict E11 capture pin matrix PASS (8 Pulse, 8 Frequency, 2 unsupported sources)
Phase2C evidence lifecycle PASS: 43 cases
Phase2D fresh-edge evidence PASS: 8 scenarios
```

The eight Phase 2D cases span both Frequency and Pulse: same-edge replay rejected; zero-edge completed sample rejected; new-edge sample accepted and sealed; edge counter wrap rejected. Rejecting an invalid sample blocks subsequent reports in that session and produces `INVALID` after successful release.

The **workflow was updated** to include a read-only Phase 2D step, but no GitHub Actions green run has been confirmed. This local test does not attest a full E11 SDK build or a Flipper device.

## 5. Explicitly unclosed gate: native publication evidence

Do **not** connect `LabMateEvidenceSession` to real capture callbacks by copying UI fields and supplying arbitrary counts or an invented `ownership_confirmed` boolean. The native producers need:

1. An app-thread-only capture-generation source incremented **only after confirmed native ownership**; screen switches/HOLD must not forge a new generation.
2. A real monotonic **completed-observation** counter separately maintained for Frequency LOW, Frequency HIGH and Pulse, with actual edge counters captured in the **same coherent reporting window**.
3. Bounded and independently checked monotonic start/end timestamps and actual clock reference; counter wrap or ambiguous timebase -> **CLOCK ERR**, not guessed rate.
4. A genuine final status after native IRQ detach and firmware lease return, including release failure and stale handle inspection. An unresolved lease -> **BUSY/ERR**, never `released=true`.
5. Source-path-specific compile tests and *then* E11 SDK/FAP integration and on-device metrology, without affecting published Stable tags or microSD contents.

The helper still **cannot independently prove a caller's claims of physical edges**. It only rejects internally inconsistent reported evidence. The full-stack / full-repository CI regression and E11/physical acceptance remain separate gates.

**Decision:** Phase 2D evidence-consumer anti-replay **HOST PASS**. Live acquisition instrumentation and v2.0 Stable **NO-GO**.
