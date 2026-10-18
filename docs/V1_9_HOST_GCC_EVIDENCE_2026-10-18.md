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
| `tests/test_scope_reference_view.c` | `11914fe721bc9828f9036525fc403761acdb7f29` |

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
