# LabMate Ultimate v2.0 — UI-06C status-label contract and GPIO integration

**Date:** 2026-10-21  
**PR:** #21, `dev/v2.0-signal-doctor` into `dev/v1.9-logic-scope`, remains **Draft/Open**.  
**Gate:** **Pure-status host PASS + source-identical GPIO-renderer host PASS**. Complete repository UI-06 and GitHub Actions/E11 SDK/device **PENDING**.

## Change scope

- Added **`src/labmate_ui_status.h`**: pure standard-C status enum and two static-inline functions with no HAL/SDK, timing, memory allocation, GPIO, UART, I2C, 1-Wire or SD dependencies.
- Replaced the original four-way text conditional **only** inside `draw_gpio` in `src/labmate_ui_screens.c` with `labmate_ui_status_label(labmate_ui_gpio_monitor_status(...))`.
- Preserved priority **release fault → ERR; otherwise resource blocked → BUSY; otherwise HOLD; otherwise LIVE**. Unexpected enum values display `ERR`; no unsafe inferred `RUN`.
- Preserved badge placement x=91 / width=35, filled/outline expression, HIGH/LOW, counter, PA7 reservation and shared x=2/x=66 footer, and all existing hardware/input calls outside renderer.
- Updated `tests/test_v20_ui05e_gpio.c` to import the actual production status header and `scripts/test-v20-ui05e-host.sh` to resolve its include path.
- Added `tests/test_v20_ui06c_status.c` and `scripts/test-v20-ui06c-host.sh`; read-only `.github/workflows/v20-ui-host-gates.yml` includes both source path trigger and UI-06C step.

## Independently verified source identities

| Artifact | Exact Git blob SHA |
|---|---|
| `src/labmate_ui_status.h` | `5742e025421cc91d8edf5f2c94877983b4ef00e6` |
| `tests/test_v20_ui06c_status.c` | `ea57a377d5cb6d09fabcda1c3a2fb136e01df630` |
| Updated `src/labmate_ui_screens.c` | `be78699d7b8e1773841f0ddbcc37bfa0b8e7ea27` |

The local compiled status header and test files were verified with `git hash-object` against their GitHub blobs. The **complete current production `draw_gpio` function body** was copied byte-for-byte from connected GitHub source to an isolated host fixture and compared independently: **2,364 characters, CRC32 `47ca8ae8`**, no trailing newline included in checksum. CRC32 authenticates the tested source fragment only, not firmware/FAP assets.

## Actual local host executions

Pure status tests (standard C11 + `-Wall -Wextra -Werror -pedantic -O1 -g -fsanitize=address,undefined`) **passed with GCC and Clang**, exit 0 each:

```text
UI-06C GPIO pure status contract PASS: 8 states + 2 invalid status values
UI-06C GPIO pure status contract PASS: 8 states + 2 invalid status values
```

These check all eight combinations of fault/busy/hold, label width inside original GPIO badge, and two invalid enum values falling back to `ERR`.

A separate **production-function-identical isolated host integration test** invoked actual `draw_gpio` for **2,400** pin / counter / level / busy / error / hold / PA7-PWM combinations per compiler, with bounded ASCII Canvas mocks, ASan and UBSan enabled. Both compilers exited 0:

```text
UI-06C production-identical GPIO renderer integration PASS: 2400 states
UI-06C production-identical GPIO renderer integration PASS: 2400 states
```

The fixture does not include the **entire** `src/labmate_ui_screens.c` translation unit and its narrow Canvas primitives are host stubs. Thus this **does not** prove the exact full repository script has executed, the Flipper GUI font raster, or a successful E11 SDK build.

## Repeatable repository test path

From the checked-out `dev/v2.0-signal-doctor` root:

```sh
sh scripts/test-v20-ui06c-host.sh
```

The script compiles the committed pure-status fixture with both compilers, then invokes the existing source-extracting `scripts/test-v20-ui05e-host.sh` on real GPIO renderer code; both use GCC/Clang plus ASan/UBSan and temporary host files only. The script and CI step are now present in GitHub, **but a full checkout execution/CI-success log has not been observed**.

GitHub Actions for this branch still reports **0 workflow runs** at the end of this change. A workflow YAML file is not proof of CI success. UI-06's earlier Frequency/Pulse full-module combined regression also remains pending until independently run.

## Release safety

No changes were made to published v1.8 normal-Momentum or v1.9 E11 Stable releases, tagged FAP, `application.fam`, GPIO/TIM/IRQ leases, PWM output, CSV, Profiles CRC, Flipper firmware, install scripts, or microSD contents.

**UI-06C: limited host PASS; E11 SDK/device and full UI-06 suite PENDING. v2.0 Stable NO-GO.**
