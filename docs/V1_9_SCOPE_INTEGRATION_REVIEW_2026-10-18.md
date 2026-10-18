# LabMate v1.9 — PC1 Logic Scope integration review (2026-10-18)

Status: **SOURCE REVIEW / NOT PHYSICAL ACCEPTANCE**. This is a scoped review of the current `dev/v1.9-logic-scope` branch; it is neither a firmware flash authorization nor a v1.9 release.

## Verified in source on this branch

- `application.fam` declares experimental v1.9; `src/labmate.c` allocates/initializes a Scope state and polls the Scope screen.
- `src/labmate_scope_bridge.c` routes START/STOP/BACK, drives UI display state, and records A/B metrics only after native capture teardown. 
- `src/labmate_scope_native.c` gates native capture behind `FURI_HAL_RESOURCE_LEASE_API_V1` and `FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK`. On absent matching APIs, START returns unsupported instead of falling back to asserting stock callbacks.
- PC1 EXTI1 native driver uses a resource lease plus try-add callback before GPIO/EXTI reconfiguration; interrupt callback reads DWT cycles and GPIO state, with no storage/UI work.
- A bounded 256-edge in-app capture buffer and a time guard are present. The target remains *single-channel digital*, not an analog scope.

These are **code observations only**. Neither CI status nor real native coexistence/measurement accuracy was independently established by this review.

## Integration gate before any install or v1.9 release

| ID | Required validation | Status |
| --- | --- | --- |
| LS-01 | Exact E11 patched native ABI symbols, SDK pin and reproducible FAP build | NOT VERIFIED IN THIS REVIEW |
| LS-02 | Host tests: 0/1/2 edges, repeated levels, wraparound, buffer-full, dropped-edge flags | INITIAL HOST CASES ADDED; CI RESULT UNVERIFIED; full matrix remains open |
| LS-03 | Trigger/quiet/wall-duration and delayed (>100ms) polling watchdog, including tick-to-ms conversion | TRIGGER/QUIET/POLL-GAP/WRAP CASES ADDED; wall-duration/native conversion still open; CI result unverified |
| LS-04 | START refusal under existing PC1 native callback/lease **without changing foreign registers**, and lease-release failure stickiness | PURE C PC1/OWNER TESTS ADDED; real HAL register and callback isolation not yet verified |
| LS-05 | STOP/BACK/restart during ARMED, RUNNING, FULL, error and clock-unsafe states; verify no own IRQ/lease remains | NOT VERIFIED IN THIS REVIEW |
| LS-06 | A/B pair metrics: require complete distinct captures; invalid/no signal/overflow must never report an idealized PASS | TRUNCATION FAIL-CLOSED FIX + HOST REGRESSION ADDED; exact CI/FAP/physical acceptance still open |
| LS-07 | Peak IRQ load, RAM/stack usage and 128×64 rendering responsiveness under high edge rate | NOT VERIFIED IN THIS REVIEW |
| LS-08 | 3.3V independent signal generator and independent analyzer/scope, plus native foreign-service contention | DEFERRED PHYSICAL TEST |
| LS-09 | Existing UART/PWM/Counter/Button/Logger/Profile navigation and legacy data regression | NOT VERIFIED FOR V1.9 |
| LS-10 | Exact FAP SHA256, backed-up SD/firmware, tested FAP-only recovery and separately classified full-firmware recovery | NOT VERIFIED FOR V1.9 |

## Source-level review observations

1. The header comment in `src/labmate_scope_native.h` still says the driver is not connected to the menu, whereas `src/labmate.c` already shows Scope integration. Treat such historical comments as stale, not evidence of disabled code.
2. `src/labmate_scope_bridge_refresh` reads a bounded live sample snapshot; full metrics are latched only when no native IRQ or lease is active. Validate this distinction with host tests before changing UI semantics.
3. The code checks the kernel tick frequency before millisecond conversion, and rejects certain late/unsafe clock states. Verify timer wrap, long UI stalls and watchdog behavior against actual patched firmware.
4. Do not merge E11 Draft PR #13 wholesale into `main`, modify historical tags or update installed devices as part of this review.

## Next controlled implementation step

Run and inspect the newly added host regression CI; extend the uncovered metrics/owner/native ABI tests and then inspect build logs before any FAP change. Record exact test commands and commit SHA. Only after that, assess an explicitly approved, backup-protected physical test on the matched E11 device.

Canonical scope stays: v1.9 **Logic Scope + Signal Compare**, then v2.0 **Signal Doctor + unified dashboard**. Existing Stable v1.8 and compatibility-limited E11 prerelease are preserved.

## Implementation update — 2026-10-18

- Explicit PC1-only input validation strengthened at the pure resource gate. The underlying capture policy already restricts the Scope owner to PC1; this is a second fail-closed check, **not** proof that a different pin previously reconfigured hardware.
- Added `tests/test_scope_pc1_pin_gate.c` for allowed/denied GPIO, unavailable ABI, conflicting local owner, fault status and sticky lease-release retry.
- Added `tests/test_scope_buffer_timeguard.c` for trigger filtering, short 32-bit wrap, invalid interval, 256-edge capacity/drop, no-trigger/quiet timeout, late poll and millisecond wrap.
- Added `.github/workflows/v19-scope-host.yml` on the dev branch to compile and execute both tests on branch pushes with strict compiler warnings. This workflow is **host only**: no Flipper firmware flashing, FAP publishing, personal data or GPIO access.
- Commits: `eae6bbd` gate, `f171d80` initial PC1 regression, `7a9e27b` buffer/timeguard suite, `7e12fef` workflow, `9954701` ownership retry test.
- **Execution status:** workflow source and tests exist, but no authenticated run/job PASS log was retrieved in this session. Treat outcomes as **UNVERIFIED**, never as CI PASS.

## Signal Compare follow-up — 2026-10-18

**Source defect fixed:** `scope_bridge_latch` marked an overflow/dropped-edge capture as `truncated` while still allowing `scope_last_valid`. The pure A/B pair validator and comparison engine also accepted such metrics. A sample containing unobserved transitions must not be used as a trustworthy full-capture comparison.

- `src/labmate_scope_bridge.c`: latches `last_valid` only for READY **and not truncated**.
- `src/labmate_scope_pair.c`: refuses saving A/B from truncated measurements.
- `src/labmate_scope_compare.c`: independent comparison API refuses truncated A or B.
- `tests/test_scope_compare_pair.c`: covers two genuinely observed 1kHz waves with different duty (50.0% vs 45.0%), insufficient/invalid input, A/B generation monotonicity, and overflow-marked A/B rejection.
- `.github/workflows/v19-scope-host.yml`: added the third host test executable.
- Relevant commits: `15de604`, `3035467`, `4ec7796`, `a2439f2`, `09b788f`.

**Evidence correction:** No reproducible local GCC execution log for the exact repository sources is available in the reviewed evidence. An earlier note describing a reconstructed implementation as local PASS is **not acceptable as verified evidence** and is superseded here. Host test code is committed, but exact checkout/CI execution and native FAP/device acceptance remain UNVERIFIED until genuine logs are inspected.

## Measured tolerance reference module — 2026-10-18

A new **pure C, UI-independent** starting point toward the required v1.9 named reference and tolerance feature is on the development branch:

- `src/labmate_scope_tolerance.h/.c`: sample presets `100Hz 50%` and `1kHz 50%`, illustrative ±1% frequency and ±2 percentage-point duty tolerances; custom caller-supplied numeric limits are supported by the reference struct. These are reference specifications, **not measured signal truth or accuracy claims**.
- Verdicts are `PASS`, `OUT_OF_TOLERANCE`, `NO_SIGNAL`, `INVALID` and `BUSY`. Only capture-complete READY metrics without dropped edges, with observed cycles, valid timebase and plausible fields can become PASS/OUT_OF_TOLERANCE.
- `NO_SIGNAL` requires the caller to explicitly classify a confirmed no-signal timeout. Zero edges alone, while still waiting for a signal, remain `INVALID`. A BUSY condition is not evaluated as a pass.
- `tests/test_scope_tolerance.c` exercises authentic synthetic H-L-H timestamp-derived 1kHz metrics, exact and exceeded numeric limits, null/stale references, truncated captures, unverified clock/zero-cycle metrics, BUSY and NO_SIGNAL differentiation.
- `.github/workflows/v19-scope-host.yml` builds and runs the tolerance module as a **fourth host test**. Commits `eff400b`, `48c6174`, `15ff321`, `9e4bee9`.
- **Acceptance scope:** source files and CI configuration committed; exact GitHub runner logs/green result were not available through the readback tools. No v1.9 FAP, UI integration, ABI compatibility or physical device results are claimed.

**Next gate:** inspect real CI job output and fix any compiler/runtime regressions, then connect this verified evaluator to the Flipper display via an explicitly reviewable change. Do not invent measured PASS screens or integrate demo-only output.

## Reference verdict page integration — 2026-10-18

The pure-C reference comparator is now **connected in development source** to an additional read-only Scope LCD page. This is NOT a device acceptance or a published v1.9 FAP.

- `src/labmate_scope_reference_view.[ch]` renders the selected named preset, `PASS / OUT OF TOLERANCE / NO SIGNAL / INVALID / BUSY`, and measured Hz/duty only for complete, non-truncated, validated captures. The verdict uses full mHz precision; LCD display rounds/truncates for readability.
- Existing app view and input coordinator now offer `DOWN` cycling `PLOT -> A/B -> REFERENCE -> PLOT` when stopped, and `UP` to toggle `100Hz 50%` / `1kHz 50%` on the reference page. `BACK` retains existing safe STOP + return logic. Starting new capture resets the page to PLOT without changing the selected reference.
- The reference view cannot independently acquire GPIO/IRQ, and app UI computes a comparison only after a matching completed capture generation, no active native owner/lease and no clock fault. `NO SIGNAL` is shown only after the native no-trigger timeout with zero captured edges. `BUSY` is not shown as a measurement.
- Existing A/B and waveform screens remain available; neither SD Profile nor Logger CSV format was modified.
- Added `tests/host_stubs/gui/gui.h` and `tests/test_scope_reference_view.c` for a fake Canvas test of read-only PASS/INVALID/NO SIGNAL/BUSY rendering and denial of a PASS without validated metrics. Included as fifth host test in `.github/workflows/v19-scope-host.yml`.
- The new reference presets are initial fixed examples. An on-device editor for custom tolerances is **NOT implemented**; the pure comparator accepts caller-provided reference values, but UI currently offers only the two named presets. Do not claim full user-configurable v1.9 controls are shipped.

**GitHub evidence:** committed branch files were read back. Native Flipper SDK compilation, CI green logs, on-device UI pixels/controls, independent waveform truth, real firmware-wide BUSY and STOP/RESTART are **NOT VERIFIED**. The connected GitHub Actions tool used here did not expose push-run logs; empty commit-status or PR-run lists do not establish CI PASS/FAIL. Work must remain in `dev/v1.9-logic-scope` until these gates are separately checked.

### Next manual physical acceptance (only after confirmed matched E11 FAP build and backup)

1. Without starting capture, go to reference page: it must say INVALID/WAIT, **not** PASS or NO SIGNAL.
2. With known-safe 3.3 V signal, capture 100 Hz / 50% using the already validated PA7->PC1 loopback. STOP, choose the 100 Hz preset on the reference page; this is a **functional loopback check**, not independent calibration.
3. Compare against the wrong 1 kHz preset; verdict must be OUT OF TOLERANCE (given a completed valid capture), never false PASS.
4. With PC1 disconnected and safe input state, start and allow no-trigger timeout; expect NO SIGNAL only on confirmed no-edge timeout, not before START.
5. Check 1-2 observed edge cases, full/overflow and resource-denied BUSY; they must never be marked PASS.
6. Check DOWN/UP/BACK and STOP/RESTART, UART/PWM/Logger/Profile regressions and all owned IRQ/lease cleanup. Inspect result on actual 128x64 LCD.
7. Do not install the FAP or flash firmware before exact SDK/ABI, backup and explicitly approved installation scope are verified. External scope measurements remain with the instructor at the university.
