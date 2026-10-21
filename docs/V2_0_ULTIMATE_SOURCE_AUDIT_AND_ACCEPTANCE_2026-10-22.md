# LabMate Ultimate v2.0 — source completion audit / E11 RC gate

**Date:** 2026-10-22. **Development branch:** `dev/v2.0-signal-doctor`; Draft PR #21.  
**Target:** v2.0 Ultimate on *patched Momentum E11*. Stock Momentum is a separate workstream, never silently asserted compatible.  
**Owner request:** complete the product, stop piecemeal user testing, deliver a coherent candidate requiring only a final bounded Flipper acceptance pass.

## Audit reference and nonnegotiable limits

Source of truth: `docs/V2_0_TECHNICAL_ROADMAP_2026-10-21.md` plus original `ROADMAP.md` and `docs/MASTER_ROADMAP_V2_ADDENDUM.md`. Four mandatory pillars: (1) Signal Doctor; (2) Unified Measurement Dashboard; (3) advanced real-sample analysis; (4) application-wide professional 128x64 design. Protected v1.8/v1.9 release assets, old tool IDs 0–15, existing CSV/Profiles schema, E11 firmware, SD backups, and device FAP must remain untouched until an accepted new hash has been reviewed.

**Already observed on actual Flipper with earlier Phase3D candidate (NOT the updated source):**
- 115104-byte trial FAP MD5 `7333aea05d157e915ee5a9c4de0a2296` coexisted with untouched 101468-byte v1.9 Stable MD5 `066f017c695bb5a17158a7b26c8f4838`.
- New app opened and showed 16 guides + Signal Doctor but label remained `v1.9DEV`, and Doctor's y=52 status collided with footer. **Physical visual acceptance FAILED.**
- Native 100 Hz/1 kHz v1.8/v1.9 loopback PASS results are historical, NOT v2.0 functional PASS.

## Code changes made following the owner's full-rework request

| Pillar / safety area | Source implementation in current branch | Exact current acceptance |
|---|---|---|
| Version and launcher | `application.fam` now `LabMate Ultimate`, `fap_version="2.0"`; About uses `v2.0DEV` and Ultimate branding | SOURCE UPDATED; new FAP + device readback pending |
| UI geometry | Doctor rows moved to y=22/31/40 with status y=50; 52 divider no longer shares a text baseline. Added host geometry assertions. | SOURCE FIX; physical readback pending |
| Common visual chrome | Shared inverse footers and slim instrument headers now apply to migrated tools, root menu, About, Doctor and Dashboard. UI source avoids ISR/HAL writes. | SOURCE UPDATED; complete per-screen 128x64 acceptance still pending |
| Unified Dashboard | Appends tool ID 16 under RECORDS, preserving historic tool IDs and root `MEASURE → OUTPUT → RECORDS → COMM → INFO`. Two-page five-source overview, statistics, and provenance panes, no forced simultaneous GPIO acquisition. | SOURCE IMPLEMENTED; native build/device acceptance pending |
| Frequency/Pulse | Existing E11 native capture STOP→released-lease→sealed snapshot producers remain in use; Dashboard now clears individual restarted source slot, not all previous sources | PRIOR PHASE3D BUILT, NEW INTEGRATION NOT YET BUILT |
| Logic Scope | On native STOP with callback/lease fully released, completed genuine cycles and safely bounded frequency/duty can be projected. Scope min/max period ticks displayed from actual captured cycles | SOURCE IMPLEMENTED; new FAP/device acceptance pending |
| TIM2 Counter | Each actual owned RUN contributes a non-overflowed counter delta only after native lease teardown, never historical cumulative count masquerading as one RUN | SOURCE IMPLEMENTED; new FAP/device acceptance pending |
| Logger | Successful persisted CSV row count can appear after clean file sync/close and native capture teardown; this is **row count, NOT proof every row is electrically valid** | SOURCE IMPLEMENTED; SD fault tests pending |
| Advanced statistics | Bounded 64-session mean/min/max for genuine sealed Frequency/Pulse snapshots; Scope actual min/max period ticks. No artificial interpolation or heap accumulation. | PURE HOST RUNNERS ADDED; NOT yet executed on owner's updated checkout |
| Signal Doctor reasoning | Existing source/release/sample-validated freq/duty checks; new separate evidence/next-check advisory page with explicit insufficiency/busy/error, no part-failure accusation | SOURCE IMPLEMENTED; on-device response and false positives pending |
| Source-only regressions | Phase2L 22-suite + Phase3A/B/C/D suites plus new Dashboard, stats, Doctor-advice GCC+Clang ASan/UBSan gates. CI path filters updated. | RUNNERS WIRED; no observed current-run CI/WSL PASS yet |
| E11 release packaging | `scripts/build-v20-ultimate-e11-review.sh` invokes host suites, exact pinned E11 isolated SDK compile, FAP APPCHK/API/ELF review and emits byte hashes/source fingerprint/provenance. | READY TO RUN; original SDK and device unchanged |

## Mandatory defects / uncovered promises — NEVER silently PASS

1. **No updated E11 binary is presently verified.** The older 115104-byte candidate SHA cannot authenticate any of these later source changes. GitHub Actions queries have returned zero observed runs; there is no online compiler PASS claim.
2. **Stuck HIGH/LOW, missing pulse and instability diagnosis are NOT complete**, because current source does not yet provide independently sealed time-window level, dropout and multi-cycle dispersion evidence sufficient to distinguish such symptoms safely. Existing no-edge output is not a stuck-level hardware verdict. The app must never invent them.
3. **Per-cycle full mean/jitter and normalized CSV/Profile workflows are not fully implemented**; the supported statistics are bounded *completed-session* frequency averages/min/max and real Scope min/max periods. Existing historical CSV and profile formats are intentionally retained, not silently migrated.
4. **Professional UI visual acceptance remains incomplete** across special Scope, UART, I²C and OneWire screen states and worst-case labels; shared components reduce inconsistency, but physical 128×64 screenshots are the authority.
5. **Ordinary Momentum compatibility** is a separate pending track and not an E11 acceptance prerequisite; no unsafe fallback or stock compatibility claim.
6. Physical test backlogs (independent external calibration, mechanical bounce, sensor I2C/OneWire, full-SD/CRC and long-run stress) remain equipment-dependent and unverified. Unavailable hardware never becomes implicit PASS.

## Single review command (no upload or flashing)

Use a *new download* of `dev/v2.0-signal-doctor` after this audit is committed. In extracted project root:

```sh
LABMATE_E11_WORK="$HOME/labmate-v20-ultimate-review-20261022" \
  bash scripts/build-v20-ultimate-e11-review.sh
```

Output if and only if all compilation gates succeed:

- `$HOME/labmate-v20-ultimate-review-20261022/LabMate-Ultimate-v2.0DEV-E11-REVIEW.fap`
- `$HOME/labmate-v20-ultimate-review-20261022/ULTIMATE_REVIEW_PROVENANCE.txt`
- Final `V20 ULTIMATE E11 HOST+FAP REVIEW: PASS | NO DEVICE WRITES`

An owner-run terminal transcript and actual SHA-256 must be reviewed before any further on-device FAP upload/launch, with **fresh scoped consent**. No automatic sidecar overwrite, restore, SD write, firmware flash, release, tag or Stable promotion.

### Follow-up source hardening, still NOT compiled

- Captured Logger's **real armed pin and source** at successful CSV-open epoch, replacing mutable preferred-pin selection in the evidence record; guards against source change before display.
- New `src/labmate_scope_period_stats.[ch]` computes bounded mean/min/max and descriptive normalized period **spread** from at least two actually completed, nontruncated Scope cycles; it is explicitly **not** a calibrated jitter or automatic instability fault. Added GCC/Clang ASan/UBSan host runner `scripts/test-v20-scope-period-stats-host.sh` and GUI display `SPREAD ...%` or `SPREAD N/A`.
- New mandatory source-contract audit `scripts/audit-v20-ultimate-sources.py` checks canonical 17-tool IDs/order, version/launcher, Dashboard/Doctor dispatch and native-sealed source hooks before full host+SDK review.
- Doctor page indicators corrected to `1/3`, `2/3`, `3/3` and three-column real input hints so advisory page is discoverable without changing actual capture behavior.
- Live repo source readback confirmed 17 tool enum entries with historical IDs unchanged and Dashboard ID 16. **This is source-only, not compiler or physical PASS**.

**Release decision:** CURRENT SOURCE = expanded feature candidate with mandatory unclosed correctness/coverage gates; `v2.0 Stable` = **NO-GO**. The roadmap is not retroactively shrunk to claim completion. Only exact built and physically reviewed bytes can move to RC/Stable.


## Owner-run host compile regression — UI-05D (2026-10-22)

After the owner locally applied the exact About guide count case-insensitive fix, the v2.0 source audit progressed into the 22-suite Phase2L host suite and then failed at `ui05d`. The owner-provided GCC diagnostics point to the extracted `ui_footer_triple` production body in `/tmp/.../triple_footer.inc` referencing `canvas_draw_box`, `canvas_set_color`, `ColorWhite`, `ColorBlack`, which were absent from `tests/test_v20_ui05d_measurement.c`'s simulated Canvas environment. The failure is in host fixture compilation, not an observed native E11 error.

Production `src/labmate_ui_primitives.c` must retain its inverse footer; the surgical response was to add actual bounds-checking Canvas mocks for box/color to the host fixture, assert final drawing color reset, and distinguish the Generator's separately mocked two-key footer from Frequency/Pulse's extracted real three-key footer. GitHub commits `475c50ebec5e2582005193ac04a31390426294fc` and `e36bc769031b838cf43c78d0ee46dae60f07c7be`. The corrected test fixture Git blob SHA is `812f06669035211ef0f3e2c8052fa558e15951a5`, replacing older blob `05812806aae43c49cc5c12cd2816e74d509c40d6`.

**Verification status: PENDING.** No successful owner-run UI05D, full host matrix or native E11 build output received yet for this correction. Existing 115104-byte Phase3D FAP and v1.9DEV protected backup remain unchanged. Do not claim v2.0 Ultimate FAP PASS or authorize firmware flash.


## Follow-up UI-05D Pulse STATS branch assertion (owner-run, 2026-10-22)

Owner reran the locally hash-patched UI-05D suite. GCC advanced past previous missing Canvas API compile errors and hit:

```text
ui05d-gcc: .../tests/test_v20_ui05d_measurement.c:213:
pulse_test: Assertion `c.color==ColorBlack && c.boxes>=1U' failed.
Aborted
```

This is an overly broad **host test assertion**. Exact production `draw_pulse` source returns early to its special `draw_pulse_stats` view and renders individual caption labels at y=62, without invoking `ui_footer_triple` or drawing the footer background box. Main Pulse view does call the shared inverse triple footer and does draw the background box. The assertion previously incorrectly required both views to draw it.

Fix in development source commit `6658d23f3f4f380a634c0b64ec2d965fac618cb6`, **only** `tests/test_v20_ui05d_measurement.c`:

```c
assert(c.color==ColorBlack);
if(view == 0U) assert(c.boxes >= 1U);
else assert(c.boxes == 0U);
```

Current corrected host fixture Git blob: `e0291f953d0856e822ddd4f6600413aa2411435d`, previous fixture blob `812f06669035211ef0f3e2c8052fa558e15951a5`. UI producer, E11 capture HAL, Flipper device and installed FAP **unchanged**. **Retest status PENDING**; no proof that this source passed GCC/Clang or native SDK review. Keep release NO-GO.


## Phase2K owner-host regression: Counter STOP fixture missing Dashboard evidence (2026-10-22)

The owner supplied a complete pasted terminal log (after successfully applying the UI05D Pulse STATS fix). The updated GCC/Clang `UI-05D` passed: `frequency=192 pwm=384 pulse=2688` on both compilers; UI01–UI06, snapshot and Phase2B–2J host suites passed. The **22nd Phase2L suite Phase2K failed to compile** the verbatim extracted `labmate_event_counter_stop` in `tests/test_v20_phase2k_button_counter.c`: its historical fake `LabMateApp` lacked `counter_run_tick_hz`, `counter_run_generation`, `counter_total`, `counter_run_start_total`, and `doctor_store`, and it did not include the real `LabMateSnapshotV1` contract or dashboard ingest API.

**Source-side corrective commits:**
- `d02b40165276847656b4661200d31de714b35989`: extend only the host Button/Counter STOP fixture to model the production 64-bit counters and run metadata. Link real `labmate_dashboard_store.h`. Add four explicit successful-lease/43-event, zero-edge, failed-lease and changed-clock validation cases while retaining the six historical release scenarios.
- `d1dff55819a349f9b1d3df38c5b4e5eaf55a340d`: compile this fixture against actual `src/labmate_dashboard_store.c` and `src/labmate_snapshot.c`, not an inert dashboard mock.

**Pinned host test-only Git blobs:** `tests/test_v20_phase2k_button_counter.c` old `c4b81c3c15be11e1d567ed670fa0190710f4f5a0` → new `b5276c9a96b05dc02d5cf80b715501cd7561be60`; `scripts/test-v20-phase2k-host.sh` old `a84517cde5325ffce3320f1cbfee332fd485646e` → new `9aa0d55532777c560a9710d7574a92cb3ae06fe4`. The local patcher checks both old/new blob hashes before updating WSL source tests and never mutates production code or device.

**Latest observed owner result:** Phase2L stopped at Phase2K; **new Phase2K gate NOT YET RUN**, complete host integration still FAIL/BLOCKED; **no new E11 FAP compile was executed**. Device test and v2.0 Stable remain NO-GO.


## Owner-run Phase3B Doctor layout cross-enum compile warning (2026-10-22)

The latest owner-provided local build transcript verifies **22/22 Phase2L host suites PASS (GCC + Clang)**, **Phase3A 38 evidence scenarios and eight invalid-input gates PASS**, and Phase3B reference editing policy PASS. The Phase3B 128x64 layout fixture then stops compiling due to `-Werror=enum-compare` for the comparison between `LABMATE_DOCTOR_STATUS_Y` and `LABMATE_UI_FOOTER_RULE_Y`. The constants are numerically 50 and 52 but declared in **different anonymous enum types**.

Fix: `tests/test_v20_doctor_layout.c` updated in commit `acd3245d36f57d7991cd547135f03a02c6f8d962`, keeping the geometry `_Static_assert` and applying `(int)` to each side. Git source blob old `0973a8641299a8290cb78ed7406b5d3c3a232d5b`, new `1cd344ae1a4b055f20765260cbc72452d4d80c66`. A standalone equivalent cross-enum geometry compilation was locally verified under GCC and Clang with `-Wall -Wextra -Werror -pedantic -fsanitize=address,undefined`, but the **full repository Phase3B test has NOT been rerun** with this fix, and therefore no wider PASS is claimed.

No production app code, firmware, microSD data or installed FAP was changed by this fix. Remaining Phase3C/3D/Ultimate suite, E11 APPCHK/ABI/FAP and device physical acceptance stay unverified for current source. Preserve current owner-installed 115104-byte Phase3D sidecar and independently matched 101468-byte v1.9DEV rollback copy. NO Stable or firmware flash.
