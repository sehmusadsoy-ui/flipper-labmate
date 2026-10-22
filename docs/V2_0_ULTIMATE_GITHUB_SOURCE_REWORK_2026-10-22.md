# LabMate Ultimate v2.0 — canonical GitHub source rework ledger

**Date:** 2026-10-22. **Source:** GitHub `sehmusadsoy-ui/flipper-labmate`, `dev/v2.0-signal-doctor`, Draft PR #21 against `dev/v1.9-logic-scope`.

**Owner instruction:** Use current GitHub repository/history and already approved v2.0 roadmap as the canonical baseline, **not** any separately uploaded ZIP archive. This work remains on the isolated v2.0 development branch. No Stable/main/release/Flipper/firmware/SD alteration.

## Mandatory v2.0 product contract

Refer to `docs/V2_0_TECHNICAL_ROADMAP_2026-10-21.md` and `ROADMAP.md`. All four pillars are mandatory: **Signal Doctor**, **Unified Dashboard**, **real-sample Advanced Analytics**, and a **cohesive professional 128×64 UI across all tools**. Preserve numeric tool/screen/profile IDs, 17 legacy/current tools, `MEASURE → OUTPUT → RECORDS → COMM → INFO` with INFO last, CSV and Profile S1–S3+CRC, safe IRQ/GPIO/TIM leases/STOP/BACK, E11 primary firmware; normal Momentum follows an independent compatibility workstream. Do not fabricate high-speed edges, analog measurements, no-signal proof or component-failure diagnoses.

## Newly implemented GitHub-source changes

| Area | Code changes and boundaries |
|---|---|
| Professional launcher | `src/labmate_menu_grid.h` and `src/labmate_ui_screens.c` introduce a two-column, five-tile 128×64 root that shows all groups simultaneously with inverse focus, while keeping original group/tool IDs. Root directional controls become spatial; all original submenu tool actions and INFO-last contract remain. Fixed child label/disclosure overlap and button-hint length. |
| Shared instrument headers | Frequency, Pulse and PWM Studio now use the same `ui_draw_header` typography, left accent and separator as the other instrument screens, rather than individual title code. Their original status badges, metric layout and measurement logic were left intact. `UI-05D` source-extracted test harness now also models the shared header and its Pulse STATS exception. **Updated host/SDK result PENDING.** |
| Source-linked visual regression | `tests/test_v20_ultimate_root_grid.c`, `tests/test_v20_ultimate_menu_renderer.c` and associated shell runners model all root and submenu selections; the latter extracts and compiles production `draw_menu` rather than testing a merely similar reimplementation. |
| Dashboard state isolation | `src/labmate_input_menu.c` clears the *individual* Frequency/Pulse slot on new capture, no longer erasing unrelated stored Scope/Counter/Logger data. Source model still rejects stale/busy/error numeric reads. |
| Actual Scope timing analytics | `src/labmate_scope_diagnostics.[ch]` computes min/max, mean, mean absolute deviation (MAD), spread and optional suggestive doubled-period timing gap from complete real observed PC1 cycles. Called after successful owned IRQ/lease teardown in `src/labmate_scope_bridge.c`, not from ISR or live redraw. At least four cycles and repeated near-min periods required for gap suggestion. A doubled period does NOT independently prove a physically missing pulse. |
| Scope → Doctor | Sealed, exact-generation Scope PC1 measurement is now a third Doctor source alongside Frequency and Pulse; reference/duty comparisons fail closed on too few samples, invalid provenance or owner/clock problems. Advisory notes suggestive timing anomalies, not hardware failure. |
| Sampled GPIO Monitor evidence | `src/labmate_level_witness.[ch]` tracks actual exclusively leased input reads, rejects wrong pin, clock/gaps >250ms, lost ownership, insufficient duration and incomplete release. Doctor's fourth source can show **HIGH SAMPLED**, **LOW SAMPLED**, **LEVEL CHANGED**, or **NO LEVEL EVIDENCE** with “VERIFY WITH SCOPE”. Polling is not continuous pin-state proof; never call a line definitely STUCK merely from these samples. |
| Fail-closed build gates | `scripts/test-v20-offline-full-host.sh`, `scripts/audit-v20-ultimate-sources.py` and the v2.0 GitHub workflow definitions now include dedicated host runners for new root navigation, exact menu renderer, Scope timing and GPIO level evidence. E11 build workflow requires complete offline host gates before SDK review. |

## Verification evidence and limitations

- Earlier `LabMate-Ultimate-v2.0DEV-E11-REVIEW.fap` **123584 bytes** SHA-256 `e9a8098a49df586716423cd66d37dfd6215fedf9006cb913bcef6676d807d1b1` was successfully built against pinned E11 and used for an earlier trial. **That exact FAP predates the changes above. It is NOT a build of current GitHub source.**
- Isolated pure C logic equivalent to the new level witness, Scope diagnostics, and menu grid passed local GCC/Clang strict host assertions with ASan/UBSan. This is **not full checkout host PASS** or E11 ARM/API/APPCHK PASS for the newer branch revision. New exact `draw_menu` renderer test has not been executed in a complete source checkout.
- Current GitHub Actions query shows no confirmed branch runs. Never claim CI green by implication.
- Real Flipper screen/raster inspection on current source, renderer-wide geometry, all old tools' special screens/statuses, long-run benchmark and E11 resource contention are still pending. New code may uncover native build errors.
- Existing original CSV/Profiles are unchanged. No additional SD writes or automatic hardware probing for diagnostics.
- The new GPIO witness only observes samples: pulses between polls can be missed. Scope “gap?” requires independent source/reference corroboration and is only an evidence-based suggestion.
- Normal Momentum compatibility, independently calibrated bandwidth/timebase, external components/I2C/1-Wire, SD corruption fault injection and hardware fixtures remain separate/unverified tracks.

## 2026-10-22 continuation — remaining two common-UI footer exceptions

- **Pulse STATS:** Replaced bespoke unboxed captions with the shared inverse action band. Four measurement rows now have baselines `22/31/40/49` (above the y=52 footer rule) and left/right numeric columns representing **MIN / MAX**, documented in the Pulse About tool guide. When LIVE, keys are `vRST`, `OK HOLD`, `^MAIN`. When HOLD, DOWN reset is genuinely disabled in the input handler; use the truthful shared paired footer `(UP) MAIN`, `(OK) LIVE` rather than advertising a nonfunctional reset.
- **History Detail:** Added `ui_footer_info` to the shared primitives so a genuine `(BACK)LIST` key and passive `READ ONLY` indicator use the same inverse footer. Never pretend READ ONLY is a clickable key. The primitive prevalidates ASCII, label lengths and null input before painting.
- **Real source-linked host gates:** `UI-04` now extracts production History Detail, shared key formatter and informational footer. `UI-05D` now extracts production pair/triple footers and their dependencies, instead of a dummy pair that hid inverse-background faults. The shared footer unit test now checks invalid inputs, actual color restoration and geometry. The app-wide static contract permits none of the former footer exceptions.
- **Verified here:** read-only GitHub current-source audit found all **16 legacy C renderers** using shared header + shared footer and no forbidden native resource call in their renderer bodies; Pulse four 8px rows and live/hold footer branching matched source assertions. Separately, a **self-contained C11 source-matching copy** of `ui_format_key` and `ui_footer_info` passed GCC and Clang with strict warnings + sanitizers for valid and rejected labels. That selective compilation is **not a substitute** for running the real GitHub checkout's UI-04/UI-05D/Phase2L suite, nor the E11 APPCHK or physical UI.
- **Pending:** run actual source-linked GCC/Clang full suite including new history/pulse test branches, build freshly pinned E11 FAP and confirm on-device all-screen pixel appearance. Both initial and later acceptance candidates retain their own hashes; never substitute the previous 123584-byte FAP as evidence of this new source.

## 2026-10-22: Native Pulse restart / UI correctness hardening

- Source audit found a concrete misleading-state bug: on a held Pulse screen, `labmate_pulse_capture_start(app)` can reject an E11 EXTI/lease request, yet the app-thread handler unconditionally set `app->hold = false`. The panel could therefore transition toward LIVE without a confirmed active Pulse IRQ or native owner, and the next OK would be interpreted as STOP rather than a retry.
- Commit `198cd29edd47291e5bec349ccbf65a75e1b8e1fc` changes the Pulse resume path to retain HOLD unless the IRQ is active, owner equals `LabMateCapturePulse`, capture is not blocked, and there is no unresolved native release fault. No extra GPIO reads, lease acquisitions or IRQ callbacks were added.
- Added pure `labmate_pulse_ui_state.[ch]`, an exhaustive 16-case independent policy test and a source-linked app-thread audit. Mandatory to both `test-v20-offline-full-host.sh` and UI GitHub workflow. The actual production function is checked by the source runner.
- A locally copied **matching pure-C test and implementation** compiled and executed with GCC 14.2 and Clang 17, `-std=c11 -O1 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined`: **16/16 PASS on both compilers**. This validates the tiny helper behavior, **not** a successful full GitHub checkout integration or E11 ARM/FAP build.
- No install, EEPROM/SD write, firmware flash, Stable or main branch mutation. The previous 123584-byte FAP remains an older, different hash and does not contain this change.

## 2026-10-22 — Updated 128×64 launcher and honest first-launch instrument state

- Root now keeps the fixed `ULTIMATE` title and `v2.0DEV` badge above five two-column cards. The previous footer only mentioned column and row movement, concealing how to enter a group. Root uses the real existing inverse `ui_footer_triple`: `<>COL`, `^vROW`, `OK GO`. No virtual buttons or touch-screen affordances are implied.
- Submenus retain all original tool IDs, category order and actions. The upper-right badge now shows the selected **1-based tool index / actual group size** (e.g., `3/7` under MEASURE), while the version identity remains on the root. The source-extracted exact `draw_menu` host fixture was updated to check all five root selections, the three physical-control hints and each submenu's counter geometry. Its full GCC/Clang run against the current checkout is **not yet observed**.
- Additional E11 UI safety: both initial menu entry into Pulse and subsequent resume from HOLD now derive the displayed LIVE/held state from an active Pulse IRQ, matching native Pulse capture owner, no blocked capture and no outstanding release fault. Merely calling START is not evidence that the E11 GPIO/EXTI lease was granted. Both paths are included in the source-linked host gate; no native pin or firmware policy was relaxed.
- A **schematic visual preview** drawn from the current C canvas geometry (root, MEASURE submenu, empty Dashboard, Doctor setup) was generated for discussion. It is *not* a Flipper display photograph, native firmware framebuffer, or pixel-exact Flipper font raster. The user has not yet accepted the UI appearance.
- **Release still NO-GO:** current revision lacks a full verified host matrix, E11 native FAP and physical device visual review. Existing `123584`-byte FAP is historical and must not be presented as an output of this newer source.

## Subsequent mandatory release gates

1. Check out the **current exact GitHub development commit** afresh into an isolated directory; never build the user-supplied ZIP or overwrite the previously backed-up WSL candidate.
2. Pass `python3 scripts/audit-v20-ultimate-sources.py` and **entire** `sh scripts/test-v20-offline-full-host.sh` suite including source-extracted UI geometry and new symptom guards. Fix failures in development source, do not bypass assertions.
3. Pin untouched E11 SDK source and run a new isolated native E11 FAP `APPCHK` review (e.g. via `scripts/build-v20-ultimate-e11-review.sh` in a **new unused workspace**). Capture **new** FAP SHA-256/MD5/bytes and actual build log; never reuse old candidate hash.
4. Run a consolidated device acceptance on the *new exact FAP*: all original + new screens and error states, input semantics, USB/I2C/OneWire/GPIO resource safeguards, Doctor no-false-PASS behavior, real 100 Hz/1 kHz PA7→PC1 loopback, Counter/Logger/Profile/CSV readback and STOP/BACK ownership; keep optional hardware calibration separately marked DEFERRED.
5. Do not promote a `v2.0 Stable` tag, release, main merge or firmware update without these gates and explicit owner decision.

**Current conclusion: v2.0 development source has substantive work, but premium-everywhere visual acceptance and full E11 native/device verification remain unclosed. Stable = NO-GO.**

## Full-screen consistency audit update

- `src/labmate_ui_screens.c`: Frequency, Pulse and PWM Studio are now migrated to the same `ui_draw_header` used by GPIO, Logger, Profiles, History, Button, Counter, Alerts and About. Three independent hand-drawn title/separator duplicates were removed; pin badges, native measurements and button semantics remain intact. The source-extracted `tests/test_v20_ui05d_measurement.c` harness now models the shared title rail and recognizes Pulse STATS's special footer arrangement.
- `scripts/test-v20-ultimate-ui-contract.py` is a source-level invariant for **16 existing renderer functions**, plus new Doctor/Dashboard and dedicated Scope chrome, requiring shared heading and control-footer except explicitly documented special cases. Wired to the full offline gate, CI workflow and v2.0 source audit.
- **Superseded by the continuation above:** Pulse STATS no longer uses the bespoke y=62 footer, and History Detail now uses a shared inverted passive-information footer. Shared-footer source contracts are implemented, but the exact updated host suite and physical 128×64 raster acceptance are still pending.
- There is **still no successful complete host/E11 SDK/APPCHK run for these new source commits**. The previous v2.0 FAP hash MUST NOT be reused for new code. Current status is development source, not a release candidate.
