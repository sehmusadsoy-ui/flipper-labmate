# LabMate v2.0 — WSL E11 verifier unit-test evidence (2026-10-21)

**Branch:** `dev/v2.0-signal-doctor` (Draft PR #21).  
**Evidence:** Owner-supplied Ubuntu WSL2 terminal transcript, following full Phase 2L + Phase 3A offline host PASS.  
**Policy:** No hardware writes, no firmware flash, no Stable changes.

## Unit-test results actually observed

1. `python3 -m unittest discover -v -s tests -p 'test_verify_v19_e11_sdk_fap.py'` reported **Ran 6 tests in 0.004s — OK**.
2. `python3 -m unittest discover -v -s tests -p 'test_check_v19_review_bundle.py'` reported **Ran 11 tests in 0.007s — OK**. Printed test names included negative checks for invalid source SHA, altered FAP bytes, duplicate/nested/extra members, missing no-install warning, stale provenance, unsupported ARM architecture, wrong firmware base, and a valid folder/ZIP case.
3. `command -v arm-none-eabi-gcc || echo 'ARM compiler not installed'` printed **ARM compiler not installed**; this establishes only absence on the current shell PATH. FBT may provision its own toolchain, so no claim that FAP compilation is impossible or that apt installation is required.

## Current status and next dependency

- **PASS:** Phase 2L full 22-suite GCC/Clang and Phase 3A Signal Doctor host-only tests (prior owner's transcript).
- **PASS:** E11 SDK/FAP verifier 6/6 self-tests and review bundle 11/11 self-tests (this owner's transcript).
- **PENDING:** exact pinned Momentum firmware checkout `d3f89dfe2ef6b01839201598e9be1590cba80322`; audited E11 patch chain; native `./fbt fap_labmate` compilation, exported ABI, linker and FAP signature verification.
- **PENDING:** real-device physical timing and STOP/BACK safety.
- **NO-GO:** v2.0 Stable, release, install, firmware flash or SD modifications.

**Note on source acquisition:** user currently works from a development-branch ZIP, not a `.git` checkout; the GitHub CI workflow's `git -C labmate rev-parse HEAD` assertion cannot be directly reused in that ZIP. FBT may auto-download toolchain and attempt git submodule synchronization, requiring network and appropriate repository layout. Keep such work scoped to a separate SDK workspace.
