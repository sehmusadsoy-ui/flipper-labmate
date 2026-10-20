# LabMate v2.0 — UI-03 1-Wire display validity + UART host regression

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor` → PR #21 Draft into `dev/v1.9-logic-scope`  
**Status:** **UI-03 limited host PASS**. Full application UI and hardware acceptance **PENDING**.

## 1. Source and behavior audited

The real firmware driver stores `temperature_tenths` as **`int16_t`**, not `int32_t`. Its DS18B20 decoder already rejects samples outside **−55°C..+125°C** and accepts **9..12-bit** resolution; however, the old passive UI renderer checked only `status == Measured` and `has_temperature`. Inconsistent app snapshots could therefore draw impossible values under a `DONE` badge.

This is a **defensive display correctness** issue: there is no physical evidence that the hardware decoder produced such an invalid sample. The C unary-minus expression used for a promoted `int16_t` value is not inherently the `INT32_MIN` overflow previously hypothesized; this fix is about UI trust and bounded values, not a proven integer-overflow crash.

`src/labmate_uart_ui.c` was inspected and the **actual unmodified function body** was exercised for RX/TX, three baud selections, active/stopped/busy, invalid baud, dropped/error counters at `UINT32_MAX`, maximum 19-character terminal lines, twelve-character TX buffer and cursor position. No new 128×64 text overflow was reproduced under those valid UI data bounds, so UART production source was **not edited**.

Profiles and History renderers have also been source-inventoried; their dynamic filename/slot and confirmation states have **not** been fully covered by actual host-renderer state sweeps and remain an explicit next gate.

## 2. Red-before-green host evidence

Files copied into an isolated local host worktree and verified using `git hash-object` against GitHub:

| File | Verified Git blob SHA |
|---|---|
| Original `src/labmate_onewire_ui.c` (pre UI-03) | `6437cc5d468002a9aa0ba8afbc72feb94c4ea2e0` |
| `src/labmate_uart_ui.c` (unchanged) | `23c256f3cef5ca8cafdae5fcb80243f121003841` |
| Updated `src/labmate_onewire_ui.c` | `50f34705a2efd44d4fd9db2a0254ca65057cee40` |
| New `tests/test_v20_ui03_comm.c` | `9fa42a3fe3af1061752d4c7169dfbdc3f19f74ce` |
| New `scripts/test-v20-ui03-host.sh` | `592acf97e20033dfe618fd4add17acd4ab522294` |

The test uses the verbatim `draw_onewire` and `draw_uart` function bodies extracted from production `.c` files. Only Canvas / firmware type dependencies are stubbed. The host geometry model uses 8×11 primary / 6×8 secondary font rectangles and tests pixel bounds; this is **not** a physical Flipper display-font raster certificate.

**Red:** Unmodified renderer built under strict host GCC/UBSan, then aborted with assertion on the `INT16_MIN` invalid-temperature case, because it drew the numeric value rather than `INVALID TEMP DATA`. This is a reproducible host logic failure, not a hardware observation.

**Green:** UI now checks `has_temperature`, temperature `-550..1250` tenths Celsius, and resolution `9..12` before rendering numeric readings. Invalid samples show `ERR` badge + `INVALID TEMP DATA` or `NO VALID SAMPLE`; no GPIO reads, sensor conversions, PWM changes or logging side effects were added. Valid boundary readings still show genuine values.

## 3. Exact repeatable commands and results

From the repository root of the v2.0 development branch, with both GCC and Clang installed:

```sh
sh scripts/test-v20-ui03-host.sh
```

The runner creates a temporary host directory, extracts the **unmodified production renderer bodies**, compiles with:

```
-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
-fsanitize=address,undefined -fno-omit-frame-pointer
```

Observed on Linux local test host after the exact update (GCC, then Clang):

```text
UI-03 HOST PASS: 1-Wire sensor envelope and UART RX/TX boundaries
UI-03 HOST PASS: 1-Wire sensor envelope and UART RX/TX boundaries
```

Both executions exit **0**. Enumerated coverage per compiler: 8 actual 1-Wire status values (Idle through Stopped), 10 measured-data boundary/invalid cases, and 30 UART combinations (3 baud indices × 10 representative states), for 48 tested fixture cases per compiler. These are **not** 48 distinct hardware measurements.

## 4. Correction to existing UI-02 host fixture

`tests/test_v20_comm_render.c` had a separate source-parity defect: I²C `Ready` and 1-Wire `Idle` should be the first (`0`) enumerators, and the real 1-Wire `temperature_tenths` is `int16_t`. The host fixture was corrected to the matching numeric ordering, bounds and type without changing its eight-case I²C / eight-case 1-Wire sweep. Updated file blob SHA: `ae474e0d36ca10a4adb017b4a8c73ddd8c60d900`.

**Evidence distinction:** The corrected UI-02 fixture has **not** been separately re-executed under both compilers as part of this exact UI-03 evidence. Previous UI-02 host PASS applies to its then-current fixture; rerun the new one before marking this patch's UI-02 regression PASS.

## 5. Release / next gate

- **PASS:** UI-03 host validity and UART basic bounds using source-matched renderer bodies, GCC + Clang with ASan/UBSan.
- **PENDING:** corrected UI-02 full rerun; Profiles, History and UART extended malformed-input states; all 17 screen-state geometry acceptance; exact E11 SDK build, hardware tests and native firmware compatibility.
- **No changes:** published v1.8/v1.9 Stable tags and FAP assets, original microSD/Profile data, main branch, IRQ/native firmware lease code, UART IO, sensor bus transactions and physical Flipper firmware.

Next: UI-04 host-linked Profiles/History confirmation, storage/error, maximum count and text boundary cases. Do not update source renderers speculatively when no failure is reproduced.
