# LabMate Ultimate v2.0 — UI-06 shared three-action footer gate

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor` → draft PR #21 into `dev/v1.9-logic-scope`  
**Result:** source-matched isolated footer host **PASS**; full checked-out-repo UI-06 regression and E11 SDK/device **PENDING**.  
**Safety:** no flash, FAP replacement, microSD access, firmware changes, GPIO/IRQ/Timer operation, CSV/Profile changes or Stable tag edits.

## Implemented production changes

1. `src/labmate_ui_primitives.h` declares `ui_footer_triple(Canvas*, left, center, right)`, a stateless 128×64 monochrome action footer.
2. `src/labmate_ui_primitives.c` defines a preflight that rejects NULL/empty labels, unsupported non-ASCII characters and glyph counts exceeding **7/7/5** in three cells. Invalid calls do **not** draw a partial footer. Valid calls draw one separator at y=52 and FontSecondary captions at **x=2/45/96, y=61**.
3. `src/labmate_ui_screens.c`: **Frequency Meter** main view and **Pulse Analyzer** main view now call the new shared primitive while retaining existing action legends: `<> MODE` / `<>PIN`, `OK LIVE`/`OK HOLD`, `^RST`/`^STAT`.
4. **Pulse STATS view is unchanged**: its last measurement row ends at y=54, so reusing the main-view divider at y=52 would be unsafe. Its existing y=62 legend is intentionally kept independent.
5. `tests/test_labmate_ui_keylabels.c`: expands the existing real-shared-primitives test with geometry, exact captions and preflight rejection assertions. `scripts/test-v20-ui05d-host.sh` and `tests/test_v20_ui05d_measurement.c` now include **production-extracted** helper bodies in the Frequency/Pulse/PWM regression rather than replacing them with lookalike stubs.
6. `scripts/test-v20-ui06-host.sh`: builds `tests/test_labmate_ui_keylabels.c` against the **full actual `src/labmate_ui_primitives.c`** using GCC + Clang with ASan/UBSan, then calls the existing 3,264-scenario `test-v20-ui05d-host.sh`. Added to read-only `.github/workflows/v20-ui-host-gates.yml`, with changes to relevant path filters.

## Verified local source-matched component test

The two newly committed shared footer function bodies were compared against the connected GitHub version with **length and CRC32**, and were byte-for-byte identical to the functions in the locally compiled isolated host model:

| Production function fragment | Length | CRC32 |
|---|---:|---|
| `ui_footer_triple_label_valid` | 301 characters | `bb5eb12d` |
| `ui_footer_triple` | 489 characters | `1ae5fd75` |

Full production primitives Git blob: `24a356e4df8649e2be042f5a7da7a9c4e7628f48`.

Local isolated Linux compilation, using strict C11 warnings-as-errors, `-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`, executed under **GCC 14.2** and **Clang 17**. The test used a bounded Canvas mock and ran five valid triple legends (including both Frequency and Pulse LIVE/HOLD) plus eight invalid labels, including excessive length, NULL, empty and non-ASCII inputs. Both processes exited **0**.

```text
UI-06 triple-footer host PASS: 5 layouts + 8 rejected labels, atomic/no-overlap
UI-06 triple-footer host PASS: 5 layouts + 8 rejected labels, atomic/no-overlap
```

**Critical evidence distinction:** this is a **source-fragment-matched helper test**, not a successful run of the new `scripts/test-v20-ui06-host.sh` from a fully checked-out repository. The latter's full real shared-primitives link and the updated 3,264-case Frequency/Pulse/PWM integration suite still need an executable independent PASS. The unchanged prior UI-05D PASS predates UI-06 and must **not** be silently rolled forward.

## Read-only GitHub inspection

- PR #21 stayed **Open / Draft** against `dev/v1.9-logic-scope`, never merged to `main`.
- The connected GitHub Actions list for `dev/v2.0-signal-doctor` still reported **0 runs**; the commit combined-status list was empty. **CI = PENDING**, not PASS.
- Existing v1.8 normal Momentum and v1.9 E11 Stable, original FAP hashes, old Profile S1–S3/CRC and CSV history were not changed.
- The only source files changed for this UI-06 slice were `src/labmate_ui_primitives.h`, `src/labmate_ui_primitives.c` and the two main-view footer blocks in `src/labmate_ui_screens.c`.

## Exact reproducible gate after checkout

```sh
sh scripts/test-v20-ui06-host.sh
```

This runs the actual full shared-primitives test and then the migrated Frequency/Pulse/PWM renderer state regression. Once a zero-exit run is available, retain the exact source SHA/log and, separately, obtain an E11 SDK app build and human review on physical 128×64 Flipper. Neither a host snippet PASS nor a CI workflow definition certifies firmware or hardware behavior.

**UI-06 status: limited footer host PASS / integrated gate PENDING / v2.0 Stable NO-GO.**


## UI-06B centralized grid metrics (2026-10-21)

The shared 128×64 design contract is now a **pure C, zero-HAL header**, `src/labmate_ui_layout.h`: width/height; title baseline and rule; pair and triple footer positions/character caps. The firmware-side `src/labmate_ui_primitives.c` consumes those constants in `ui_draw_header`, `ui_footer_pair`, `ui_key` (baseline), and `ui_footer_triple`. This changes **only named layout constants**, not key meanings, external interfaces, screen IDs, resource owners, timing, CSV or Profiles data.

The host's conservative six-pixel ASCII character advance is intentionally **defined in the test only**, not presented as a physical display font guarantee in production layout metrics.

**Verified Git blobs (read back from GitHub):**

- `src/labmate_ui_layout.h`: `c1f2e3d42a88b204be14d582263be90973f01eee`.
- `tests/test_v20_ui06_layout.c`: `1082555bdcf19b029a94da9452afadd523758463`.
- Updated `src/labmate_ui_primitives.c`: `f472a2597d2bc5208ac582df44f4afe5bcbcd3af`.

An independent isolated Linux host run compiled `tests/test_v20_ui06_layout.c` **byte-for-byte**, with the exact GitHub version of the new header, using `gcc` 14.2 and `clang` 17 under strict C11, `-Wall -Wextra -Werror -pedantic -fsanitize=address,undefined`. Each compilation/runtime exited **0** with:

```text
UI-06 static layout 128x64 pair/triple contract PASS
```

The test asserts that header/title/content/footer stay in range and that maximum valid key hints cannot overlap across two or three cells under the host text-width model. The actual newly updated `ui_footer_triple_label_valid` and `ui_footer_triple` production function bodies were independently extracted and matched to GitHub at **301 chars / CRC32 `bb5eb12d`** and **833 chars / CRC32 `2a32abe1`**. GCC and Clang both executed a bounded Canvas test of those byte-identical functions: **five allowed combinations, eight reject cases, and NULL Canvas**, each exit status 0. This is a direct function-fragment host test, **not** an entire repository full-module build.

`tests/test_v20_ui05d_measurement.c` and `scripts/test-v20-ui05d-host.sh` were updated to include the real `labmate_ui_layout.h` and production extracted shared footer bodies. `scripts/test-v20-ui06-host.sh` now runs the compile-time metrics test as well as the earlier shared-primitives and Frequency/Pulse regression steps; CI workflow path triggers include `src/labmate_ui_layout.h`.

**Pending exactly as before:** execution of the updated full UI-06 runner against a complete checked-out repository; independent GitHub Actions green job; E11 SDK FAP compilation; actual device LCD and input behavior. Neither the header's source hash nor the isolated fragment tests proves those independent gates.
