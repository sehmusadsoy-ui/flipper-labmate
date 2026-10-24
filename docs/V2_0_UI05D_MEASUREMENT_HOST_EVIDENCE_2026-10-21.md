# LabMate Ultimate v2.0 — UI-05D Frequency, Pulse, PWM host gate

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor`; **PR #21 is Draft** against `dev/v1.9-logic-scope`.  
**Result:** **UI-05D source-linked host geometry PASS** (GCC 14.2 and Clang 17, 3,264 states per compiler).  
**Non-claims:** no E11 SDK/FAP build, physical measurement, pixel-raster screenshot, Github Actions successful run, stock Momentum compatibility or v2.0 Stable readiness.

## Source integrity and test mechanism

Actual `src/labmate_ui_screens.c` was inspected from the connected GitHub branch at Git blob SHA `268cf8f5023a15a25f06fa0bc54904b38bfbd001`. Eight relevant **unmodified** function bodies were copied into an isolated local test directory and their text lengths/CRC32 values independently compared with the exact remote GitHub source:

| Function | Text length | CRC32 |
|---|---:|---|
| `frequency_format_compact` | 1,530 | `ed925a9c` |
| `frequency_format_edges` | 367 | `c6f2b5d0` |
| `draw_frequency` | 2,876 | `99e49c19` |
| `draw_generator` | 2,051 | `1662e2bf` |
| `pulse_ui_format_value` | 615 | `efdae973` |
| `pulse_ui_metric` | 502 | `f7eca578` |
| `draw_pulse_stats` | 2,550 | `3ff1a3dc` |
| `draw_pulse` | 2,226 | `c7a9f5f2` |

CRC32 compares source fragments, not firmware or binary trust. The locally executed **test source and runner** are byte-identical to GitHub after upload, confirmed using Git blob identity:

- `tests/test_v20_ui05d_measurement.c` — `14b1fd5a1e0c94e60ff657fa1a6314c99d2e95f3`.
- `scripts/test-v20-ui05d-host.sh` — `d61bf950596e3fc2bd70e8c6a881acfa01ba127b`.

The runner extracts those real functions from the production source as host `.inc` files in a private temporary directory; firmware-specific types and Canvas/font calls are narrow stubs. The test does **not** reimplement display algorithms. The helper used for converting Pulse CPU cycles to microseconds is a **host-only 64-MHz clock model**; this does not attest device timing.

## Actual execution and scenarios

Command (from v2.0 branch checkout on Linux/WSL):

```sh
sh scripts/test-v20-ui05d-host.sh
```

Compiler flags: `-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer`.

Both **GCC 14.2** and **Clang 17** locally compiled and executed with **exit code 0**. The two observed output lines:

```text
UI-05D GEOMETRY: frequency=192 pwm=384 pulse=2688
UI-05D GEOMETRY: frequency=192 pwm=384 pulse=2688
```

- **Frequency: 192 cases/compiler** — 12 boundary/transition/UINT32_MAX milli-Hz values × LOW/HIGH source × 4 LIVE/HOLD/BUSY/ALRT states × MIN/MAX validity. Edge count includes UINT32_MAX. Checks status badge, text collisions, full LCD bounds and no app state mutation.
- **PWM Studio: 384 cases/compiler** — 15 real presets plus CUSTOM × duty 5%/50%/95% × RUN/STOP/BUSY/ERR × two test iteration modes (real CUSTOM edit exercised only when custom index is selected). Tests PA7 source label, upper-right badge, column layout, footer boundaries and passive draw.
- **Pulse Analyzer: 2,688 cases/compiler** — 8 known pin names × LIVE/STATS × valid/invalid × 7 CPU cycle extremes × duty 0/50/100% × LIVE/HOLD/BUSY/ALRT. Valid STATS at 100% explicitly checks `100.0%` text. Host checks 128×64 bounds, displayed text overlaps and snapshot immutability.

**All 3,264 states per compiler passed** in the available ASCII font geometry model (primary glyph 8×11; secondary 6×8); these are **not** real electrical measurements or proof of on-device font raster/refresh behavior. No untested input state or sensor sample is claimed accepted.

## Production change and next acceptance gate

**No production application change was necessary**: tests did not reproduce a geometry violation within these bounded cases. Only the new test, runner, CI workflow addition and this evidence were committed. `.github/workflows/v20-ui-host-gates.yml` now includes a UI-05D read-only step in the v2.0 PR; a workflow definition does **not** establish GitHub Actions success.

**Still pending for Phase 1:** GPIO render and adverse/odd states, fully integrated UI render validation with real Canvas SDK fonts, E11 SDK/FAP build, on-device layout, menu key input, native IRQ STOP/BACK and compatibility. The professional shared UI visual design, Dashboard and Signal Doctor implementations have **not** been started by these tests. Keep PR Draft and old Stable/FAP/firmware/Profile/CSV artifacts untouched.
