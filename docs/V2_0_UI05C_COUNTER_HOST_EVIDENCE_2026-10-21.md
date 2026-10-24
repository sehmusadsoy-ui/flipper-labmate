# LabMate v2.0 — UI-05C Counter 64-bit renderer host evidence

**Date:** 2026-10-21  
**Gate:** **UI-05C Counter host PASS** — GCC 14.2 + Clang 17.0 with ASan and UBSan.  
**Scope:** E11-based v2.0 Draft PR #21, `dev/v2.0-signal-doctor` → `dev/v1.9-logic-scope`.  
**Not claimed:** digital pulse measurement calibration, TIM2 hardware behavior, GitHub Actions CI PASS, E11 FAP build, actual Flipper pixels, normal Momentum support or v2.0 Stable readiness.

## 1. Exact source fidelity

The local host fixture includes only the unchanged, complete `draw_counter()` production function body extracted from the GitHub v2.0 branch. The function was verified against GitHub as **2,725 characters / CRC32 `e1256f13`**. The local isolated `src/labmate_ui_screens.c` includes just this identical function, not the entire production `src/labmate_ui_screens.c` file (Git blob `268cf8f5023a15a25f06fa0bc54904b38bfbd001`).

The local `src/labmate_counter_math.c` and `src/labmate_counter_math.h` are **Git-blob-identical** to the original source:
- `src/labmate_counter_math.c` — `0e5c7d48ee849b9b58600e6dea2458434cc6fa7d`.
- `src/labmate_counter_math.h` — `77b9046e7699ed0f47307d458852f4161e3fcc8a`.

The committed host test and script also match the exact bytes tested locally:
- `tests/test_v20_ui05c_counter.c` — `db5b02b405495bd1fac268e98378fe0aa6ad38cf`.
- `scripts/test-v20-ui05c-host.sh` — `056961eab3a4cf2dc71bff708e3a83815d641829`.

CRC32 is used for function-fragment equality checks, not for firmware authenticity; Git blobs identify source/test file contents and not the installed FAP.

## 2. Actual host test and result

From repository root of the v2.0 development branch on Linux or WSL:

```sh
sh scripts/test-v20-ui05c-host.sh
```

The runner extracts the original `draw_counter` function body, links the original pure `src/labmate_counter_math.c`, and compiles on **GCC 14.2** and **Clang 17.0** with:

```
-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
-fsanitize=address,undefined -fno-omit-frame-pointer
```

The actual local output was:

```text
UI-05C Counter host: 640 cases, 0 failures
UI-05C Counter host: 640 cases, 0 failures
```

Both compiler/test runs exited **0**, exercising 10 representative `uint64_t` counter values (including 0, multi-digit transitions, 11/12-digit split, and `UINT64_MAX = 18446744073709551615`) × 8 elapsed-time states (including 59/60 seconds, 3599/3600 seconds, 99-hour threshold, and `UINT32_MAX`) × 8 combinations of RUN, BUSY and latched alert states. Host Canvas checks 128×64 text bounds and text overlap, badge containment and no mutation of application state during draw. The long `UINT64_MAX` count is also checked for complete, non-truncated text.

**Interpretation:** 640 host presentation states *per compiler* passed; these are **not** 640 device measurements. Original Counter renderer production code was not edited.

## 3. CI wiring and next gate

The new `scripts/test-v20-ui05c-host.sh` is included in `.github/workflows/v20-ui-host-gates.yml` after UI-05B. Workflow configuration was added to PR #21 with read-only contents permission and no flash, FAP deploy, firmware write, SDK install or microSD access. **There is no confirmed GitHub Actions run or CI green check in this evidence.** A YAML file's presence is not CI PASS.

**Outstanding UI-05:** Frequency Meter, Pulse Analyzer, PWM Studio, GPIO and full cross-tool GUI font verification remain. The common professional 128×64 design system, Dashboard and Signal Doctor have not yet been implemented.

**Release:** PR remains Draft. v1.8 ordinary Stable, v1.9 E11 Stable, installed firmware and all user Profiles/CSV data are untouched. Complete Phase 1 and v2.0 Stable are **PENDING**.
