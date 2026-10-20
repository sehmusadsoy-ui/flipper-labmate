# LabMate v2.0 — UI-02 COMM status-badge geometry / verified host evidence

**Date:** 2026-10-21
**Branch:** `dev/v2.0-signal-doctor` → draft PR #21 into `dev/v1.9-logic-scope`
**Result:** **UI-02 COMM BADGE HOST PASS** (limited to the 16 specified I2C/1-Wire renderer states).
**Not claimed:** full Phase 1 screen completion, E11 SDK build, on-device rendering, real sensor ACK/CRC or firmware support for stock Momentum.

## 1. Exact unchanged source reproduced on host

Production files were retrieved from the v2.0 GitHub branch, locally reproduced, and **Git blob SHA values checked with `git hash-object`** *before* altering anything:

| Production source | Baseline blob | Fixed blob |
|---|---|---|
| `src/labmate_i2c_ui.c` | `162426ea56e82f1f5ba8c5202be2d703049ac445` | `c093c96d5f2949a80daef000f544c4732c5ba2d7` |
| `src/labmate_onewire_ui.c` | `dfc632bf477eb858d6f5dcd9d1026fe416bd0213` | `6437cc5d468002a9aa0ba8afbc72feb94c4ea2e0` |

Both fixed blob SHAs were confirmed by the GitHub file update response and match the locally tested fixed source byte-for-byte.

## 2. Original defect reproduced (red test)

A host Canvas model was connected to the **unmodified function bodies** of `draw_i2c` and `draw_onewire`, extracted verbatim from the production source. Only firmware-specific include/types and shared UI primitives were represented by host stubs. Host font rectangles use FontPrimary=8x11, FontSecondary=6x8, matching the previous host testing assumption; this is not a device raster measurement.

The test checks `0..127` / `0..63` pixel limits, text rectangle overlap, badge text inside painted badge width, and display errors without changing hardware data. It enumerates 8 I2C and 8 1-Wire states per compiler, including bus busy, firmware API unavailable, no ACK, scanning, results, CRC error and absent sensor.

**Baseline run:** exit 1, **four violations spanning three states**:

| State | Observed geometry violation |
|---|---|
| I2C firmware API absent, badge `FW API` | text begins x=95, has 36 px width, extends past x=127; also outside 35 px badge frame |
| 1-Wire data error, badge `ERROR` | label spills past badge frame |
| 1-Wire ready, badge `READY` | label spills past badge frame |

Those are actual conditions of the source-level geometric host model, **not** proof of what a particular hardware font raster displays.

## 3. Minimal UI-only fixes

- I2C `ui_badge` rectangle changed from `x=91,width=35` to `x=82,width=44`: keeps `FW API` visible inside badge and LCD without renaming/truncating it.
- 1-Wire `ui_badge` rectangle changed from `x=93,width=33` to `x=91,width=35`: keeps `READY` and `ERROR` within the badge without overlapping the `1-WIRE TEMP` title.

No input map, measured value, native lease, capture IRQ, sensor transfer, generator, Profiles, CSV, firmware source, install script, FAP asset or stable release was changed.

## 4. Reproducible test-only files

- `tests/test_v20_comm_render.c` exact Git blob `f3ddb159c08d4e54bb7d3741a7be3fe993cd944c`.
- `scripts/test-v20-ui02-host.sh` exact Git blob `1221be9dd976445bccad7b84955bc93c46c8ce53`.
- This script extracts renderer function bodies in a disposable host temporary directory, compiles them with stub Canvas and runtime types, runs both GCC and Clang with warnings-as-errors and ASan/UBSan, and removes the temporary directory. It is never part of the firmware app's `sources=["src/*.c"]`.

Actual local command:

```sh
sh scripts/test-v20-ui02-host.sh
```

Tested on a Linux host with `gcc` and `clang`, using:

```
-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
-fsanitize=address,undefined -fno-omit-frame-pointer
```

**After source fixes:** both compiler executions exit 0. Observed final lines for each compiler:

```text
UI-02 COMM GEOMETRY PASS: 8 I2C + 8 1-Wire renderer states
```

And the runner reports:

```text
UI-02 HOST PASS: 16 renderer states per compiler (GCC + Clang)
```

## 5. Review gate and next steps

**UI-02 status: HOST PASS** specifically for described status-badge bounds.
**UI-01 whole-app / Phase 1: PENDING**: actual pixel-font raster, Frequency/Pulse/PWM/UART, History/Profiles/Logger, mixed overflow states, real GUI draw calls and E11 on-device review still require separate tests. Later revalidate oneWire numeric formatting for extreme/malformed data, including unsafe negative integer edge cases, without fabricating a sensor result.

The branch remains `dev/v2.0-signal-doctor`; PR remains draft against `dev/v1.9-logic-scope`. The previous v1.8 (normal Momentum) and v1.9 (E11) Stable releases remain immutable.
