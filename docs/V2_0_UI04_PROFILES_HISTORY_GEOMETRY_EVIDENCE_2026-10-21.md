# LabMate v2.0 — UI-04 Profiles & Log History 128×64 geometry audit

**Date:** 2026-10-21  
**Result:** **UI-04 LIMITED HOST PASS — 300 screen-state fixtures, GCC and Clang.**  
**Branch:** `dev/v2.0-signal-doctor`; **PR #21 remains Draft**, targeting `dev/v1.9-logic-scope`.  
**Baseline:** E11-only v1.9 source; no firmware installation or Stable binary modification.

## 1. Reproduced initial failure (before any source edit)

The production `draw_profiles` function in `src/labmate_ui_screens.c` displayed:

```c
canvas_draw_str(canvas, 7, 62, "SD BUSY - PLEASE WAIT");
```

In the existing host Canvas model, `FontSecondary` assumes a 6-pixel-wide ASCII glyph. The 21-character string occupies **126 pixels**, from x=7 through x=132 inclusive; the physical 128-pixel screen ends at x=127. Original source produced on GCC and Clang:

```
BOUNDS 'SD BUSY - PLEASE WAIT' x=7 y=62 right=132
PROFILES selected=0 action=0 present=0 scenario=1 faults=1
```

**Red result:** the full UI-04 host test aborted/fails at the busy Profile case. This is a host geometry violation, not a measured on-device screenshot.

## 2. Smallest corrective change

Changed exactly one string inside the **Profiles** busy branch:

```c
canvas_draw_str(canvas, 7, 62, "SD BUSY - WAIT");
```

The new label is 14 characters (84 pixels), ending at x=90. No change to the screen's SD operation, Profiles save/load/delete logic, CRC, storage codec, capture ownership, GPIO/PWM, logger, IRQ, firmware, or menu IDs.

Original production blob `src/labmate_ui_screens.c`: `f99c11e87a979a3257d49f30d84f7a53150d2398`. Corrected blob: `35c98c2f5fba216857547fba0abd94fe71ea4645`.

## 3. Real renderer body test infrastructure

The host runner `scripts/test-v20-ui04-host.sh` extracts the production **function bodies verbatim**, from `src/labmate_ui_screens.c`, using an AWK signature/top-level closing-brace rule. The extracted functions are `draw_profiles`, `draw_history` and `draw_history_detail`. Host stubs replace only firmware-specific types and GUI operations, never source logic.

| Committed test artifact | Exact local Git blob (checked against GitHub) |
|---|---|
| `tests/test_v20_ui04_harness.h` | `58de4244c8888e5ea311949da81578d10c98d0d4` |
| `tests/test_v20_ui04_records.c` | `cd6ea1466838477aa927b9e256b9cdb2de51809e` |
| `scripts/test-v20-ui04-host.sh` | `9ed8e01a5cf812e99f901b3451a36712542c6cd8` |

The three locally inspected functions were separately compared with the GitHub source using **source-fragment length and CRC32**:

| Function | Characters | CRC32 | Match |
|---|---:|---|---|
| `draw_profiles` | 4,368 | `f3a6f449` | MATCH |
| `draw_history` | 2,937 | `ea5faced` | MATCH |
| `draw_history_detail` | 2,168 | `f86ddc6a` | MATCH |

CRC32 is evidence of exact test-fixture matching here, **not** a cryptographic release hash or an installed firmware attestation.

## 4. Host execution and coverage

Run from the v2.0 branch repository root (Linux/WSL with GCC and Clang installed):

```sh
sh scripts/test-v20-ui04-host.sh
```

Actual test execution with both **GCC 14.2 and Clang 17**, `-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic`, AddressSanitizer and UndefinedBehaviorSanitizer, exited 0 per compiler:

```text
UI-04 HOST PASS: profiles=216 history=44 detail=40
UI-04 HOST PASS: profiles=216 history=44 detail=40
```

The **300 fixture cases per compiler** check 128×64 bounds, text overlaps, right-alignment and badge containment, confirmation prompts, empty slots, PWM/capture/Logger busy flags, corrupt/SD-error indicators, 0/1/3/32-file History lists, delete confirmation, 65535 filename ID, maximum 32-bit row count/time, and original App state remaining unmodified by draw routines.

**Do not misrepresent:** these 300 are **host render-state combinations**, not 300 independent hardware tests. They do not prove actual button press handlers, CRC recovery, real microSD corruption response, pixel raster on physical Flipper or E11 ABI.

## 5. Prior UI-02 test debt closed

After the UI-03 correction to `tests/test_v20_comm_render.c`, `src/labmate_onewire_ui.c` and that fixture were independently reproduced at their exact Git blobs:

- `src/labmate_onewire_ui.c`: `50f34705a2efd44d4fd9db2a0254ca65057cee40`
- `tests/test_v20_comm_render.c`: `ae474e0d36ca10a4adb017b4a8c73ddd8c60d900`

Re-ran `sh scripts/test-v20-ui02-host.sh`. Eight I2C and eight 1-Wire states completed **PASS with GCC and Clang**, no fixture enum mismatch. This closes the specific UI-02 rerun marked pending in UI-03.

## 6. Limitations, next work

- **UI-04 PASS means the specified Records screens pass the declared host model.** Whole-app Phase 1 is still **PENDING**.
- `draw_logger` contains a separate identical long busy string, `SD BUSY - PLEASE WAIT`. **Not edited here**, since the Logger renderer is outside this test; add real Logger render cases in UI-05 and fix based on reproduced results.
- The input/deferred file deletion code is not exercised here; the BACK/OK footer names were checked only in the passive renderer. Do not claim an SD-delete stress test or on-device permission probe.
- Keep v1.8 normal-Momentum Stable, v1.9 E11 Stable, user profiles/CSV and original firmware unchanged. PR #21 stays Draft against the E11 development branch; never merge to ordinary `main` without the separate compatibility work.
