# LabMate Ultimate v2.0 — canonical GitHub source rework ledger

**Date:** 2026-10-22. **Source:** GitHub `sehmusadsoy-ui/flipper-labmate`, `dev/v2.0-signal-doctor`, Draft PR #21 against `dev/v1.9-logic-scope`.

**Owner instruction:** Use current GitHub repository/history and already approved v2.0 roadmap as the canonical baseline, **not** any separately uploaded ZIP archive. This work remains on the isolated v2.0 development branch. No Stable/main/release/Flipper/firmware/SD alteration.

## Mandatory v2.0 product contract

Refer to `docs/V2_0_TECHNICAL_ROADMAP_2026-10-21.md` and `ROADMAP.md`. All four pillars are mandatory: **Signal Doctor**, **Unified Dashboard**, **real-sample Advanced Analytics**, and a **cohesive professional 128×64 UI across all tools**. Preserve numeric tool/screen/profile IDs, 17 legacy/current tools, `MEASURE → OUTPUT → RECORDS → COMM → INFO` with INFO last, CSV and Profile S1–S3+CRC, safe IRQ/GPIO/TIM leases/STOP/BACK, E11 primary firmware; normal Momentum follows an independent compatibility workstream. Do not fabricate high-speed edges, analog measurements, no-signal proof or component-failure diagnoses.

## Newly implemented GitHub-source changes

| Area | Code changes and boundaries |
|---|---|
| Professional launcher | `src/labmate_menu_grid.h` and `src/labmate_ui_screens.c` introduce a two-column, five-tile 128×64 root that shows all groups simultaneously with inverse focus, while keeping original group/tool IDs. Root directional controls become spatial; all original submenu tool actions and INFO-last contract remain. Fixed child label/disclosure overlap and button-hint length. |
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

## Subsequent mandatory release gates

1. Check out the **current exact GitHub development commit** afresh into an isolated directory; never build the user-supplied ZIP or overwrite the previously backed-up WSL candidate.
2. Pass `python3 scripts/audit-v20-ultimate-sources.py` and **entire** `sh scripts/test-v20-offline-full-host.sh` suite including source-extracted UI geometry and new symptom guards. Fix failures in development source, do not bypass assertions.
3. Pin untouched E11 SDK source and run a new isolated native E11 FAP `APPCHK` review (e.g. via `scripts/build-v20-ultimate-e11-review.sh` in a **new unused workspace**). Capture **new** FAP SHA-256/MD5/bytes and actual build log; never reuse old candidate hash.
4. Run a consolidated device acceptance on the *new exact FAP*: all original + new screens and error states, input semantics, USB/I2C/OneWire/GPIO resource safeguards, Doctor no-false-PASS behavior, real 100 Hz/1 kHz PA7→PC1 loopback, Counter/Logger/Profile/CSV readback and STOP/BACK ownership; keep optional hardware calibration separately marked DEFERRED.
5. Do not promote a `v2.0 Stable` tag, release, main merge or firmware update without these gates and explicit owner decision.

**Current conclusion: v2.0 development source has substantive work, but premium-everywhere visual acceptance and full E11 native/device verification remain unclosed. Stable = NO-GO.**
