# LabMate Ultimate v2.0 — UI-05E GPIO Monitor Host Geometry Gate

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor` to `dev/v1.9-logic-scope`, PR #21 **Draft/Open**  
**Result:** **UI-05E GPIO HOST PASS: 2,400 states on GCC + 2,400 on Clang**  
**Non-claims:** no E11 SDK build, real Flipper display / GPIO acquisition validation, CI green run, sensor accuracy, firmware flash, or Stable readiness.

## Actual production source fidelity

- Existing `src/labmate_ui_screens.c` Git blob `268cf8f5023a15a25f06fa0bc54904b38bfbd001` was read directly from GitHub.
- The exact production `draw_gpio` function body was reproduced locally and checked against the remote source: **2,353 characters, CRC32 `26d315c7`**. The local host source fragment file has one trailing newline; it is deliberately excluded from the function CRC.
- `src/labmate_ui_primitives.c` Git blob `81b00e440ebba508b3f73d7b075e51b273bbbf82` was read to match `ui_badge`, `ui_key` and header semantics.
- Exact Git blob identities of newly committed test sources were compared with the independently executed local files:
  - `tests/test_v20_ui05e_gpio.c` — `6e10268db401fcacd51c244727ee2f2e3d91bf45`.
  - `scripts/test-v20-ui05e-host.sh` — `cffd34024350043a0bd77082ac13ac540291039a`.

The script extracts the real `draw_gpio` function from the repository into a temporary directory. Canvas, GUI/font and application state are test-only stubs; hardware acquisition code is neither compiled nor invoked.

## Actual host execution

From the repository root:

```sh
sh scripts/test-v20-ui05e-host.sh
```

Both GCC and Clang locally compiled and ran with `-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer`. Observed output:

```text
UI-05E GPIO host PASS: 2400 source/level/status/PWM combinations
UI-05E GPIO host PASS: 2400 source/level/status/PWM combinations
```

Each process exit status: **0**. Combinations per compiler: 8 distinct historic GPIO pin names × 15 edge-count boundary values (including 0, 9,999/10,000, 999,999/1,000,000 and `UINT32_MAX`) × 2 electrical level snapshots × 5 LIVE/HOLD/BUSY/ERR priority states × 2 PWM-reservation flags. Tests verify bounded status badges, pin label, level display, edge-count text, `PA7 BUSY` vs `POLL`, footer labels, text rectangle overlap, 128×64 pixel extents, contrast reset and no passive-render mutation of the source snapshot.

**2,400 cases per compiler are host UI combinations, NOT actual electrical measurements.** Actual Flipper font width and contrast behavior still require SDK/device validation.

## Cross-package local regression rerun

Isolated host fixture directories retained from earlier v2.0 work were rerun on the same local Linux environment, without firmware, device or SD writes:

| Package | Result |
|---|---|
| UI-01 menu + Scope geometry/navigation | PASS; 3 cases × GCC/Clang |
| UI-02 I2C / 1-Wire status geometries | PASS; 16 states × GCC/Clang |
| UI-04 Profiles / History / History Detail | PASS; 216+44+40 states × GCC/Clang |
| UI-05A Logger | PASS; 120 states × GCC/Clang |
| UI-05B Button / Threshold | PASS; 96+48 states × GCC/Clang |
| UI-05C Counter | PASS; 640 states × GCC/Clang |
| UI-05D Frequency / PWM Studio / Pulse | PASS; 192+384+2688 states × GCC/Clang |
| UI-05E GPIO Monitor | PASS; 2400 states × GCC/Clang |

All eight locally invoked shell runners returned **exit code 0**. **UI-03 UART + 1-Wire detailed-case runner was not present in the eight retained test fixture directories and was not rerun in this combined check; its earlier separate host evidence remains documented.** This local rerun is not a CI run against an entire checked-out repository, because the container has no outbound GitHub DNS; test harnesses use independently hash-verified source excerpts.

## CI and release gates

The v2.0 branch's `.github/workflows/v20-ui-host-gates.yml` now invokes UI-05E after UI-05D. The workflow only defines read-only host checks, with no Flipper connectivity, SD writes, firmware install, SDK flash, artifact release or deployment. **GitHub Actions green execution is not established.**

- **UI-05E limited host geometry: PASS.**
- **Full shared professional UI redesign: NOT STARTED.**
- **SDK/full app E11 build, real LCD raster, actual STOP/BACK and physical measurements: PENDING.**
- **Normal Momentum support: separate workstream, NOT claimed.**
- **LabMate Ultimate v2.0 Stable: NO-GO.**

Stable v1.8/v1.9 release tags, FAP, firmware, microSD data, Profiles and existing CSV logs were not changed.
