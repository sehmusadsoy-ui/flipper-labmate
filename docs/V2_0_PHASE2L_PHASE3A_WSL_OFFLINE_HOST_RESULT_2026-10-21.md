# LabMate v2.0 — Offline integrated host gate (WSL2 owner-run evidence)

**Date:** 2026-10-21  
**Project:** `sehmusadsoy-ui/flipper-labmate`  
**Development line:** `dev/v2.0-signal-doctor` / Draft PR #21  
**Evidence origin:** Console transcript supplied by the project owner from Ubuntu on Windows WSL2, **not a GitHub Actions run or assistant-controlled host execution**.

## Result: HOST SUITES PASS (owner-reported)

The owner downloaded the complete source ZIP from the v2.0 development branch and ran:

```sh
sh scripts/test-v20-offline-full-host.sh
```

First execution stopped during Phase 2K because `scripts/test-v20-phase2k-host.sh` attempted to inspect `"$tmp/counter_stop.inc"` **before** its AWK extraction created that file. This was a runner order bug, not evidence of a failing lease test. The one-line assertion was moved below extraction/existence checks in development commit `ecf00100309a13a68c3b7cfcc3f27f6142a48fe5`. The owner applied the identical minimal fix to the extracted local working copy and re-ran the host gate.

The user-supplied terminal transcript of the successful follow-up included:

```text
PHASE2L RUN: phase2k
Phase2K native-lease release gate PASS: 2048 reports, only 1 fully released
Phase2K extracted native STOP functions PASS: 9 success/failure/empty-handle cases
Phase2K extracted Button/Counter STOP PASS: 6 release scenarios
Phase2K extracted STOP-all integration PASS: 10 scope/capture/lease scenarios
Phase2K native-lease release gate PASS: 2048 reports, only 1 fully released
Phase2K extracted native STOP functions PASS: 9 success/failure/empty-handle cases
Phase2K extracted Button/Counter STOP PASS: 6 release scenarios
Phase2K extracted STOP-all integration PASS: 10 scope/capture/lease scenarios
Phase2K source-linked STOP native-lease gate PASS (host only)

PHASE2L HOST SUITE PASS: 22 suites, GCC+Clang (each runner owns its checks)
HOST ONLY | E11 SDK/FAP: NOT TESTED HERE | DEVICE_WRITES: ZERO
PHASE3A SIGNAL DOCTOR HOST PASS: 38 evidence scenarios + 8 bad-input gates
PHASE3A SIGNAL DOCTOR HOST PASS: 38 evidence scenarios + 8 bad-input gates
PHASE3A HOST ONLY PASS: GCC+Clang; SDK/Flipper/FAP NOT TESTED
V20 OFFLINE HOST PASS: Phase 2L + Phase 3A (NOT E11 SDK/FAP OR PHYSICAL DEVICE)
```

**Interpretation:** Both GCC and Clang branches completed; Phase 2L's 22 test runners passed and Phase 3A's independent Signal Doctor runner passed. This resolves the earlier **full-host execution PENDING** status for the tested local source copy. It does not establish that the entire exact latest GitHub head was tested: the owner ran a downloaded ZIP plus the narrow Phase 2K local correction, and no full-tree cryptographic attestation has yet been supplied.

## Controls and outstanding gates

- **PASS (user WSL log):** Integrated host gate, 22 Phase 2L suites plus Phase 3A on GCC and Clang.
- **PASS (GitHub source):** Phase 2K assertion-order correction committed on the development branch and its contents read back.
- **NOT TESTED:** Native E11 patched Momentum SDK source compilation, FAP/link/API/ELF verification.
- **NOT TESTED:** Real Flipper hardware timing, GPIO IRQ/lease behavior, microSD persistence, STOP/BACK.
- **NOT CONFIRMED:** Any GitHub Actions run; no hosted CI PASS should be claimed.
- **NO-GO:** v2.0 stable release, installation, firmware flash, or changes to published v1.8/v1.9 releases.

## Next safe gate

First run the *existing* pinned-E11 SDK verifier unit tests on the owner's WSL checkout, without touching hardware:

```sh
cd ~/labmate-v20-full/flipper-labmate-dev-v2.0-signal-doctor
python3 -m unittest discover -v -s tests -p 'test_verify_v19_e11_sdk_fap.py'
python3 -m unittest discover -v -s tests -p 'test_check_v19_review_bundle.py'
command -v arm-none-eabi-gcc || true
```

Only after that should we plan a separately reviewed local pinned-source E11 compile. Build-only is not install/flash authorization. Retain existing CSV/Profiles data and published Stable tags unchanged.
