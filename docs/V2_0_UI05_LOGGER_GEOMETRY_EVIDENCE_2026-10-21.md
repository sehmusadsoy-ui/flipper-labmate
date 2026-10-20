# LabMate v2.0 — UI-05 Logger host geometry regression

**Date:** 2026-10-21
**Scope:** UI-05-A Logger text bounds, lifecycle/status/measurement formatting, passive render state.
**Gate:** **HOST PASS** for the tested Logger screen only. Other measurement screens and full Phase 1 remain PENDING.
**Branch:** dev/v2.0-signal-doctor; PR #21 remains Draft into dev/v1.9-logic-scope.

## Source pins and reproduction

The exact production draw_logger function was retrieved from GitHub and its text verified with a locally reproduced source fragment. The committed runner extracts the *actual unmodified production function body* from src/labmate_ui_screens.c. Only Canvas and firmware types/timebase are host stubs.

| Evidence | Verified value |
|---|---|
| Full pre-fix production source Git blob | 35c98c2f5fba216857547fba0abd94fe71ea4645 |
| Pre-fix draw_logger length / CRC32 | 3798 / 6166b8b0 |
| Full post-fix production source Git blob | 268cf8f5023a15a25f06fa0bc54904b38bfbd001 |
| Post-fix draw_logger length / CRC32 | 3791 / faea4817 |
| Committed test Git blob | 43975a451bad5fcaec8c5579efc01b3936fe52c6 |
| Committed runner Git blob | 72e859c36cfff34013e927c8d36a68b52de2f425 |

The post-upload GitHub file blobs matched the byte-exact locally executed test and runner files. CRC32 attests fragment matching only, **not** published FAP or firmware integrity.

## RED: original failure

The original busy footer in draw_logger called canvas_draw_str at (7,62) with the 21-character label "SD BUSY - PLEASE WAIT". Using the established host FontSecondary 6px-per-ASCII-glyph geometry model, it ended at x=132 while the 128px screen ends at x=127.

Observed before editing production source:

    TEXT OUTSIDE 128x64: 'SD BUSY - PLEASE WAIT' at x=7 y=62 right=132
    UI-05 Logger host: 120 source/state fixtures, 36 failing fixtures

The 36 failing fixtures result from 3 sources × 2 valid/invalid measurements × 3 busy states × 2 normal/extreme numeric values. No physical Flipper screenshot was involved.

## GREEN: one-line UI correction

Changed **only the Logger busy caption** from "SD BUSY - PLEASE WAIT" to "SD BUSY - WAIT" at the same canvas coordinates (7,62). The previous Profiles fix is retained. This does not affect storage calls, CSV format, GPIO, IRQ, resource/lease ownership, key bindings, measurement or generator behavior.

Actual command on the local Linux host:

    sh scripts/test-v20-ui05-host.sh

The script compiles under GCC 14.2 and Clang 17.0, with:

    -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
    -fsanitize=address,undefined -fno-omit-frame-pointer

Actual post-fix outputs (both exit code 0):

    UI-05 Logger host: 120 source/state fixtures, 0 failing fixtures
    UI-05 Logger host: 120 source/state fixtures, 0 failing fixtures

The 120 fixture cases per compiler are 3 Logger source modes × 2 measurement-validity states × 10 recording/busy/error/save lifecycle states × 2 ordinary/boundary 32-bit values. The test checks text bounds, text collisions, badge containment and that draw_logger does not mutate the application state. Its pulse_cycles_to_us conversion is a deterministic host stub, not independent timebase validation.

The UI-04 isolated regression was also executed again locally, producing two zero-exit outputs:

    UI-04 HOST PASS: profiles=216 history=44 detail=40
    UI-04 HOST PASS: profiles=216 history=44 detail=40

## Remaining gates

**UI-05-A = HOST PASS only.** Actual renderer-linked tests of Frequency, Pulse, PWM Studio, Counter, Button, Threshold and GPIO, and full Flipper E11 SDK/device rendering, remain PENDING. This host test does not prove correct on-device font raster, firmware compatibility, SD failure recovery, signal measurement accuracy or GitHub Actions status.

Both Stable releases, published FAP assets, microSD files, profiles and firmware remain untouched. The PR must remain Draft until the remaining acceptance checks are genuinely satisfied.
