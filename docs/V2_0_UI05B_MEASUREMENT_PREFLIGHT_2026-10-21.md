# LabMate v2.0 — UI-05B measurement display preflight and host-run gate

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor`; PR #21 remains **Draft**, base `dev/v1.9-logic-scope`.  
**Status:** **12 SOURCE-BASED STATIC LAYOUT CHECKS PASS; NEW GCC/CLANG UI-05B C EXECUTIONS PENDING.**  
**Do not infer:** real device PASS, firmware build, full six-renderer linked PASS, CI pass, stable readiness or actual pixel font raster inspection.

## 1. Source evidence and actual work

Reviewed exact connected GitHub sources, pinned to:
- `src/labmate_ui_screens.c`: Git blob `268cf8f5023a15a25f06fa0bc54904b38bfbd001`.
- `src/labmate_button_capture.c`: controls debounce settings `5,10,20,50` ms; arbitrary `255 ms` is **not** a legitimate user selection.
- `src/labmate_threshold.c`: four source maxima `50,000 Hz`, `95 %`, `1,000,000 edges`, `1,000 ms`.
- `src/labmate_threshold.h`: source IDs `LabMateAlertFrequency/PulseDuty/Counter/ButtonSettle`.

A connected-GitHub read-only source check verified presence of the actual fixed geometry instructions and computed 128×64 bounding intervals under the project's existing **FontPrimary = 8×11 / FontSecondary = 6×8 ASCII** host model. These are geometrical **static prechecks**, not compiled rendering results.

| Source-based check | Evidence | Result |
|---|---|---|
| Button debounce actual options | 5 / 10 / 20 / 50 ms | PASS |
| Button source vs `DB 50 ms` | x=3..74 vs x=77..124 | PASS |
| Button largest 32-bit right-column count | x=67..126 | PASS |
| Button left / right split | x=3..62, divider x=63, x=67..126 | PASS |
| Threshold official maxima | 50,000 Hz / 95% / 1,000,000 edges / 1,000 ms | PASS |
| Threshold longest source label | `BUTTON SETTLE`, right-aligned starts x=47 | PASS |
| Threshold longest valid limit | `1000000 edges`, right-aligned starts x=47 | PASS |
| Threshold wait text | `WAITING FOR INPUT` fits x=6..107 | PASS |
| Counter 20-digit decimal `UINT64_MAX` | x=3..122 using Secondary | PASS |
| PWM ordinary upper control | `50 kHz` before divider x=84; `95%` in right cell | PASS |
| Frequency MIN/MAX positions | MIN x=22, MAX right-aligned x=127 | PASS |
| Pulse 2×2 layout | columns x=3,68, divider x=64 | PASS |

**Limit:** these twelve static checks do not execute any Canvas callback. Actual renderer data bounds and read-only behavior require an executable host test.

## 2. New real-renderer host test — awaiting run

Added:
- `tests/test_v20_ui05b_button_threshold.c` — test-only Canvas model and state stubs; includes verbatim extracted `draw_button` and `draw_alerts` from production via the runner. Checks ASCII bounding rectangles, label intersection, badge/footer clipping, and that rendering does not change app state. Button fixtures include max uint32 press/release/hold and uint16 bounce counts with legitimate quiet-time selections. Threshold fixtures use each source's **actual configured maximum**.
- `scripts/test-v20-ui05b-host.sh` — extracts actual production renderer functions, compiles with **GCC and Clang**, links `src/labmate_threshold.c` for genuine threshold source/unit names, and requests AddressSanitizer + UndefinedBehaviorSanitizer.
- `.github/workflows/v20-ui-host-gates.yml` — read-only workflow, now includes UI-01 through UI-05B, restricted to the dedicated v2.0 development branch or its PR head. Contains **no SDK/FAP build, firmware flash, microSD action, release action or deployment**. `permissions.contents=read` and checkout disables persistent credentials.

**Reproduce from a Linux/WSL checkout of the exact branch:**

```sh
sh scripts/test-v20-ui05b-host.sh
```

The Button fixture sweeps **96** combinations and Threshold sweeps **48** valid-source combinations per compiler. These counts are test design, **NOT yet successful executions**; runner success and errors must be recorded before accepting this gate.

## 3. CI status not falsely upgraded

At the time of this review, the connected GitHub read of the repository's Actions runs returned **`total_count=0`**. No CI run exists to prove the new workflow successfully executed. The existence of the YAML workflow and test code is *not* a PASS result. Existing UI-01..05 previous local host evidence is recorded separately in the respective documents and must not be generalized to new UI-05B.

## 4. Next gate

1. Execute `sh scripts/test-v20-ui05b-host.sh` with the exact reviewed source, capture full GCC/Clang output and exit codes; fix only genuine reproducible failures.
2. Finish linked renderer state fixtures for **Frequency, Pulse, PWM Studio and Counter**, then GPIO, and rerun UI-01..05 regressions.
3. Only after the complete host geometry gate, begin the common professional 128×64 UI system as isolated reviewable source changes, followed by Dashboard and Signal Doctor (pure deterministic C host tests).
4. E11 SDK and physical Flipper tests stay independent; do not call a source/host pass physical calibration.

**Release decision: UI-05B PENDING, v2.0 Stable NO-GO.** Published v1.8/v1.9 releases, firmware, stable tags, Profile CRC and user SD/CSV data are unchanged.
