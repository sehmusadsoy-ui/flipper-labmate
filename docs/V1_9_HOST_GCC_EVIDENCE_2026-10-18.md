# LabMate v1.9 host GCC evidence — 2026-10-18

Status: **LOCAL HOST REGRESSION PASS; NOT GITHUB ACTIONS / SDK / HARDWARE ACCEPTANCE.**

## Scope

The assistant's isolated Linux execution environment cannot resolve github.com to clone the repository. Relevant public GitHub files were read through the connected repository service; selected exact UTF-8 source files were reconstructed locally. Local `git hash-object` values were compared to the GitHub blob SHAs for every verified program source, public function contract header and repository regression test listed below. Only dependent MCU/GUI **host headers** were substituted.

No Flipper firmware was installed, no E11 native ABI was linked, and no actual IRQ/GPIO/SD/UART was exercised.

## Host tests actually executed

| Component | Host command / evidence | Result |
| --- | --- | --- |
| Final-exit guard | GCC C11 `-Wall -Wextra -Werror -pedantic`; exact `src/labmate_scope_exit_guard.c` and `tests/test_scope_exit_guard.c`; native data layout supplied through a minimal host-only header | **PASS** |
| Tolerance evaluator | GCC C11 with the same strict warnings; exact `src/labmate_scope_tolerance.c` and `.h`, standalone local boundary/validity smoke; compare metrics type supplied by host-only header | **PASS** |
| Reference LCD | GCC C11 with the same strict warnings; exact `src/labmate_scope_reference_view.c/.h`, `src/labmate_scope_tolerance.c/.h`, `src/labmate_scope_compare.c/.h` and committed `tests/test_scope_reference_view.c`; GUI and edge-buffer type headers supplied by host stubs | **PASS** |
| Undefined behavior sanitizer | `-fsanitize=undefined -fno-sanitize-recover=all` on the same final-exit and reference-LCD host regressions | **PASS** |

### Verified Git blob SHAs

| Repo source file | Blob SHA |
| --- | --- |
| `src/labmate_scope_exit_guard.c` | `3f4aade45261b2bed31fff508a3504af1c26cc55` |
| `src/labmate_scope_exit_guard.h` | `804061b5652a65b6215fffb647bfb8d6a3711ec8` |
| `tests/test_scope_exit_guard.c` | `2a6f22117038d08c41beaa59ac78b9d852d0a5b8` |
| `src/labmate_scope_tolerance.c` | `7f3b6542012be62cf4352cb1a0585fc31ae51ec6` |
| `src/labmate_scope_tolerance.h` | `43e984b0cd2be69657ba5d533b637008c1fa91e9` |
| `src/labmate_scope_compare.c` | `13b47263606adce60b08090519aa4cb3cb2f99af` |
| `src/labmate_scope_compare.h` | `3417ea901485ba18244997929294d82df95605e6` |
| `src/labmate_scope_reference_view.c` | `a91377a6c674e723f00310c95bf87ee6017d6b0c` |
| `src/labmate_scope_reference_view.h` | `b45c84646c3306372100974845ec249e76af22e9` |
| `tests/test_scope_reference_view.c` | `fd7807441980798f3f04e4cca4eb9062cc8835a4` |

## Defects fixed while testing

1. A cached `PASS` could be displayed with a subsequently changed reference preset or changed metrics if the renderer were passed an outdated verdict. The renderer now independently reevaluates the full-precision result and refuses to draw on verdict/error mismatch. Regression checks both preset and sample mutation **before any drawing**. Source fix commit: `0ebc91a`; regression: `c337618`.
2. GCC `-Werror=format-truncation` caught an undersized `snprintf` destination in the reference renderer. The host buffer now covers the static format's full compiler-bound output without changing the physical screen's coordinate logic. Source fix commit: `09c4677`. Exact-blob host rebuild of the fixed renderer **PASS**.
3. Prior `UNVERIFIED` entries for the independent GitHub Actions workflow and Momentum SDK remain **UNVERIFIED**. The connected workflow-read API only returned pull-request-triggered runs and exposed no complete authoritative CI pass log. Do not relabel it PASS from these local results.

## Remaining acceptance gates

- Re-run the **entire** repository host suite on a checked-out branch in native GitHub Actions and inspect actual job output, not only a workflow file or an empty commit-status list.
- Compile `application.fam` and the complete FAP against the exact matching Momentum/E11 native-lease SDK, with exact target firmware and library symbols; preserve the v1.8 stable checksums.
- Verify reference page on 128x64 LCD, safe START/BUSY/STOP/BACK/RESTART, rejected callback/lease without foreign-register effects, and IRQ callback lifetime when release fails.
- Use PA7->PC1 loopback for functional test only. Independent timing/duty calibration requires an external instrument (planned university test); no calibration claims until measured.

No Stable tag or release changed; no Flipper flash or microSD modification occurred.

### Re-run after same-verdict margin regression

Commit `31bf18e` adds a case where the last capture changes from 50.0% to 49.5% duty: both would be inside tolerance and individually `PASS`, but the old result's numerical error fields are stale. The renderer correctly refuses to draw the stale result even though the status label would not change. The committed updated test blob `fd7807441980798f3f04e4cca4eb9062cc8835a4` was hash-checked and executed again against the matching source files with strict GCC and UBSan: **PASS**. This remains a local host test with GUI/edge-buffer type stubs, not a Flipper FAP acceptance.

## Native Scope reinitialization regression — 2026-10-18

**Source-level safety finding:** `labmate_scope_native_init()` previously checked `active`, native `owner.handle`, `owner.phase` and `fault_sticky` but could clear session bookkeeping through `memset` even when an IRQ enable bit or stale `callback_detached`, `pin_restored`, or `fault_cleanup_phase` indicated unresolved native cleanup.

**Fix:** `labmate_scope_native_reinit_safe()` now applies a single fail-closed predicate to all native cleanup fields. The pure predicate is shared by `labmate_scope_native_init()` and `labmate_scope_exit_storage_safe()`; the latter additionally requires `session_initialized`. The PC1 resource admission gate independently refuses stale callback, pin-restore and cleanup-phase flags. No GPIO or foreign owner is reconfigured on refusal.

Exact GitHub blob bytes of these committed files were compared against local `git hash-object` results:

| File | Git blob SHA |
| --- | --- |
| `src/labmate_scope_exit_guard.h` | `9e8c2c3a77cd7ac09a808efddf64d443b2176308` |
| `src/labmate_scope_exit_guard.c` | `28a00c3e265dbe0579ba5f66268226b53acbb6d9` |
| `tests/test_scope_exit_guard.c` | `71a6c761c262f17ffcafc6db154d0c09c5fc490c` |

**Actually executed locally:** GCC 14.2, C11 `-Wall -Wextra -Werror -pedantic` host test **PASS** and GCC UBSan `-fsanitize=undefined -fno-sanitize-recover=all` **PASS**; the test uses the isolated host type stub and does not compile `labmate_scope_native.c` against the matched Momentum E11 SDK. New PC1 gate tests are committed but a complete exact-repo/GitHub Actions run has NOT been obtained.

Source/test commits: `d35f740`, `066d48b`, `5b4ea0d`, `9974968`, `35c6f20`, `83af385`. Device install, flash, and PR merge remain blocked until full CI and FAP link acceptance.

## PC1 native owner gate and direct-lease regression — 2026-10-18

**Actually executed in a local GCC Linux environment using exact GitHub file bytes** (no SDK/GUI/HAL stubs in this particular pure-C suite). After reconstructing the six repository sources listed below, local `git hash-object` output exactly matched the GitHub Contents API blob SHA values. Both commands returned **PASS**:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -Isrc \
  tests/test_scope_pc1_pin_gate.c src/labmate_scope_gate.c \
  src/labmate_resource_policy.c -o build/pc1-pin-gate-exact
./build/pc1-pin-gate-exact

cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -fsanitize=undefined -fno-sanitize-recover=all -Isrc \
  tests/test_scope_pc1_pin_gate.c src/labmate_scope_gate.c \
  src/labmate_resource_policy.c -o build/pc1-pin-gate-exact-ubsan
./build/pc1-pin-gate-exact-ubsan
```

| Exact GitHub path | Git blob SHA |
| --- | --- |
| `src/labmate_scope_gate.c` | `c06a77f06b7f466b87609ba0d9db5052cb1e32b4` |
| `src/labmate_scope_gate.h` | `12d6339feb1016d200aea17a8776062659cd7ae3` |
| `src/labmate_resource_policy.c` | `00e595f9b9c711cb25a3b824614d6617eacafb79` |
| `src/labmate_resource_policy.h` | `6842755950ad614d81fa2eb47ffc743fba4d340e` |
| `src/labmate_comm_resource.h` | `aa5ae54020c4700e5a8814ec85a16ef0820189f2` |
| `tests/test_scope_pc1_pin_gate.c` | `29e56d397b5cf0e40d02dbb11e1a20fba97de7ad` |

**Behavior:** Both PC1 admission and `labmate_scope_owner_lease_acquired` now fail closed on stale `callback_detached`, `pin_restored`, or non-idle `fault_cleanup_phase` state; the new test asserts the direct bookkeeping call does not erase evidence of unfinished native cleanup. It also verifies that an owned callback and pin are not detached/restored twice when an owned lease release fails then a later release-only retry succeeds.

Source/test commits `d37cdb2`, `bd5a0dd`, `ecf71d8`. This is a **real byte-provenance-confirmed host regression** of the unchanged pure-C code, not a successful v1.9 GitHub Actions run or patched Momentum FAP compile. External firmware ownership, actual ISR/lease cleanup, safe STOP/BACK and the independent oscilloscope timing acceptance remain **unverified**.
