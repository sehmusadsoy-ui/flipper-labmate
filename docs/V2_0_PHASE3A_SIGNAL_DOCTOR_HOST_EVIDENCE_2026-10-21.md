# LabMate v2.0 — Phase 3A Signal Doctor host evidence (2026-10-21)

**Development ref:** `dev/v2.0-signal-doctor`; Draft PR #21.  
**Code commit:** `a88f0b6dd57a77abf56f9e53babde7191e476169`.  
**Acceptance:** **38 evidence scenarios + 8 invalid-input gates PASS, on GCC and Clang**; snapshot-file source identity verified; **E11 SDK compile, device integration, device safety/accuracy and entire 22-suite Phase 2L CI remain PENDING**. Stable release NO-GO.

## Why this exists without GitHub Actions
GitHub Actions is blocked or has zero registered runs (exact repository policy and any billing cause still unverified). Phase 3A is an **isolated, host-only feature slice**; it must not be mistaken for integrated CI acceptance. A local Linux shell or Windows WSL shell with GCC, Clang and sanitizers can reproduce this test without any hosted Actions budget.

## Source implementation
- `src/labmate_doctor.h` / `src/labmate_doctor.c`: passive, allocation-free advisory classifier from `LabMateSnapshotV1`.
- Caller-provided reference frequency/tolerances; no fabricated default target.
- Supports only genuine Frequency pins PC1/PB3 and Pulse EXTI pins PC0/PC1/PB2/PA4.
- `VALID` evidence requires existing `labmate_snapshot_v1_can_display_measurement` criteria: actual complete samples, safe timebase, no dropped edges, and successfully released ownership.
- Pulse additionally requires positive HIGH/LOW intervals and the exact integer-rounded duty ratio contract already in `labmate_snapshot_bridge.c`.
- Detects frequency deviation, duty deviation, both, or within expected reference.
- `NO SIG` **only** after an upstream producer has explicitly marked `LabMateSnapshotNoSignalConfirmed` AND observed 0 edges/0 samples, zeroed all measurement fields, a sufficiently long configured observation window, safe clock and confirmed resource release. The source never infers no-signal from a timeout, stale UI or HOLD.
- BUSY, insufficient, dropped samples, unsafe clock, overflow, stale, invalid proof, unsupported source/pin or release failure => `NotReady`. **No verdict represents certain hardware failure**.
- Does not read sensors/IRQ, create snapshots, mutate dashboard, acquire resources, access microSD or write firmware. Not wired to the on-device UI/entry points yet.

## Reproduced local test
Executed `sh scripts/test-v20-phase3a-doctor-host.sh` in an isolated Linux host fixture using the exact current GitHub `src/labmate_snapshot.{c,h}` sources (Git blob identities below). Both GCC and Clang compiled with C11, -Wall -Wextra -Werror -pedantic, ASan and UBSan. Each produced:

```
PHASE3A SIGNAL DOCTOR HOST PASS: 38 evidence scenarios + 8 bad-input gates
PHASE3A HOST ONLY PASS: GCC+Clang; SDK/Flipper/FAP NOT TESTED
```

Includes boundaries, reference-range comparison, malformed payloads, stale/BUSY/OVERFLOW/CLOCK statuses, held leases, lost edges, wrong pins, pulse width/duty inconsistency and round-up ties, minimum silence window, and overflow-safe arithmetic.

**Verified existing source identities:**
- `src/labmate_snapshot.c`: `1cd46551f2d65ef33fe71ee51310a64acf5de44f`.
- `src/labmate_snapshot.h`: `5e9b57212cb7110b215202bef352a80d21bd50b2`.

**New-source byte identity:** all four pushed code/test/script Git blobs independently matched the exact files tested locally. This proves only identity of the host fixture, not firmware integration.

## Reproduce without paid CI

```sh
# From a complete working tree on branch dev/v2.0-signal-doctor:
sh scripts/test-v20-phase3a-doctor-host.sh

# Separate Phase 2L whole-host gate; do not infer PASS until it is RUN:
sh scripts/test-v20-phase2l-integration-host.sh
```

Windows users can use an existing WSL Linux distribution with GCC/Clang; no firmware flashing or Flipper USB connection is needed.

## Outstanding acceptance
1. Run Phase 3A plus all 22 Phase 2L suites in one complete checkout.
2. Compile and verify against the precisely pinned E11 patched Momentum SDK; `./fbt fap_labmate` must succeed and ELF SDK gates pass.
3. Wire native **sealed** production snapshots and reference selection to read-only Signal Doctor UI, with strict STOP/BACK and source ownership regression.
4. Add end-to-end host/device tests for all status transitions and real signal observations.
5. Keep normal Momentum as separate build workstream, defer unavailable physical hardware tests and preserve v1.8/v1.9 Stable and microSD data.

**Phase 3A host-only PASS; v2.0 integrated SDK/device/Stable acceptance NO-GO.**
