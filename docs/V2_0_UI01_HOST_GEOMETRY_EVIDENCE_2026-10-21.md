# LabMate v2.0 — UI-01 initial host geometry gate / evidence

**Date:** 2026-10-21  
**Status:** **PARTIAL HOST PASS — menu geometry + Scope chrome only. Full 17-screen UI gate PENDING.**  
**Purpose:** Record exact production source pins, host command, and the limited scope before integrating UI renderer changes.

## Source pins (read-only, copied to isolated local host worktree)

| File | Verified Git blob SHA |
|---|---|
| `src/labmate_navigation.c` | `762571cb1b03d168330a99194929ba79a994a527` |
| `src/labmate_navigation.h` | `8e2a3cd99f364bbce6930e639640313fcc2371b0` |
| `src/labmate_scope_ui.h` | `ed7379c877c541228f0395710091680b7276d800` |
| `tests/host_stubs/gui/gui.h` | `7a909b0a5f65469851a16976251380ffea5fa704` |

These four files were independently reproduced in a **local, non-device** host directory and their bytes checked with `git hash-object`, matching the GitHub read-only source blob SHAs. This is not a revalidation of the installed firmware or released FAP binary.

## Host test command (local GCC 14.2.0 on Linux)

```sh
cc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -Itests/host_stubs -Isrc \
  tests/test_v20_ui_geometry.c src/labmate_navigation.c \
  -o /tmp/labmate_ui_geometry
/tmp/labmate_ui_geometry
```

Actual local run compiled successfully and exited with status zero:

```text
UI-01 HOST PASS: pinned navigation + scope chrome 128x64 geometry
COVERAGE LIMIT: other renderers, SDK build, device remain UNTESTED
```

The tested, new source is `tests/test_v20_ui_geometry.c` (local Git blob `c06eb25936066de3017f208c2978c6c0b35bf79e`, SHA-256 `6f65a20a7172504c245985eef06b8590a258d0cf84f37b3d529214eb421b6bb4`). Before declaring this evidence reproducible from the PR, verify that committed file's Git blob SHA equals this exact test file.

## Assertions covered

- Real `labmate_navigation.c` group enumeration: 15 historical tool IDs, every tool reachable exactly once, five group ordering, INFO/About last, all first/middle/last menu viewport selections.
- Menu title and version-badge separation, longest real tool names within the existing 128px layout, rows before footer, root footer labels in bounds.
- **Real** inline `labmate_scope_ui_header` and `labmate_scope_ui_footer`: title/page/PC1 and action-text boundaries, adjacent text non-overlap, ASCII glyph-only host contract, boundary-maximum strings, missing center action, invalid-length no-paint preflight, and Scope plot/footer region separation.
- Host Canvas stubs assert 128x64 bounds and prevent text rectangle overlaps. Conservative monospace estimates follow existing host tests (FontPrimary 8x11, FontSecondary 6x8). These are host model assertions, not measured physical font raster metrics.

## Limits / non-claims

- The menu geometry in this initial test models pinned `draw_menu` coordinates; it does **not** execute all of `src/labmate_ui_screens.c` or detect unreviewed future menu layout changes.
- It does **not** cover every state in the 17 existing screen enum entries; UART, I2C, 1-Wire, Profile, CSV/History, Pulse, Logger and their overflow/error/confirmation states require renderer-linked follow-on tests.
- Existing v1.9 Scope renderer tests have been inventoried but **not freshly rerun** in this evidence entry. No SDK build, Flipper installation, real physical calibration, I2C/1-Wire sensor, firmware flash or CI run occurred.
- A passing host test is NOT a v2.0 feature, NOT an E11 compiled FAP, and NOT a Stable publication gate PASS.

## NEXT: UI-01 continuation

After GitHub test source blob confirmation, extend Canvas host fixtures to every current renderer and control state, establish repeatable host suite/CI, and only then perform one UI-only renderer change. Preserve original app/tool IDs, Profile CRC, legacy CSV, E11 native ownership, STOP/BACK and original releases. Keep PR #21 draft and targeted at `dev/v1.9-logic-scope`.
