# LabMate v2.0 — Phase 3B guarded Signal Doctor UI integration

**Branch:** `dev/v2.0-signal-doctor`; Draft PR #21. **Stable/Flipper untouched.**

## Implemented on development branch

- Appends tool ID 15, `LabMateToolDoctor`, **without renumbering IDs 0–14**. MEASURE now has seven entries and INFO remains the last root group. Existing navigation regression expectations updated.
- Appends `LabMateScreenDoctor` after historical screens; menu/input/view dispatch wired. No new capture starts from this tool. BACK exits to menu. 128x64 design uses the established headers, two three-row setting pages, badges, status and footer primitives.
- User-configured source Frequency/Pulse, reference Hz (starts at ZERO, deliberately unconfigured), frequency tolerance, duty reference/tolerance and minimum no-signal observation window. LEFT/RIGHT selects fields, UP/DOWN edits them, OK cycles reference-frequency editing step (1/10/100/1000 Hz). Settings exist only in RAM; no silent profile or microSD writes.
- Uses existing sealed `LabMateDashboardStore`, `labmate_doctor_evaluate`, and conservative quality statuses. NO DATA, BUSY, unsafe, insufficient or unset reference never show a numeric measurement or fault claim.
- The app's store is initialized empty. **Critical limitation: NO verified live Frequency/Pulse producer currently ingests evidence into that store.** The device UI correctly displays `SET REF FIRST` or `NO SEALED DATA` until a future proven capture handoff is implemented. This is NOT a completed live Signal Doctor measurement feature.

## Host test evidence and outstanding acceptance

Isolated **pure panel** GCC and Clang tests with `-Wall -Wextra -Werror -pedantic -fsanitize=address,undefined` passed locally (reference changes, no fabricated defaults, no-data/busy/invalid/insufficient state guards). The new `scripts/test-v20-phase3b-doctor-panel-host.sh` reproduces them from the complete repo; the offline master now invokes Phase 2L, Phase 3A, then Phase 3B.

The amended full Phase2L 22-suite regressions and new native E11 FAP have **not** yet been rerun on the owner's WSL workspace after this menu/renderer integration. Do not carry forward the pre-Phase3B FAP PASS to a new binary. The reproducible, copy-only `scripts/build-v20-phase3b-e11-isolated.sh` runs host gates, clones the pinned SDK into a distinct working directory, compiles FAP and checks ARM/ABI/hash. It never flashes or installs.

## Next mandatory work before feature or stable acceptance

1. Re-run all host regressions against Phase3B checked-out/downloaded sources; inspect any changed geometry or navigation expectations.
2. Build against pinned E11 SDK and run actual FAP verifier on that exact new binary.
3. Implement an auditable app-thread, real hardware **completed and released** capture-to-snapshot producer with actual same-generation observation duration, sample count, edge count, overflow and lease outcomes; ensure invalidation on new capture, BUSY, STOP/BACK, HOLD, wrong pins and stale source.
4. Host and on-device verification of end-to-end Frequency/Pulse Doctor evidence, false-positive/no-signal boundaries, 128x64 layout, resource arbitration, and physical metrology. Need explicit separate approval before any device write.

**Status:** Phase3B UI plumbing and isolated pure model PASS, overall live Doctor acceptance **NO-GO**. Never label v2.0 Stable yet.
