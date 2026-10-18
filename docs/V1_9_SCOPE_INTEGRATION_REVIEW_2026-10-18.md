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
| LS-06 | A/B pair metrics: require complete distinct captures; invalid/no signal/overflow must never report an idealized PASS | NOT VERIFIED IN THIS REVIEW |
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
