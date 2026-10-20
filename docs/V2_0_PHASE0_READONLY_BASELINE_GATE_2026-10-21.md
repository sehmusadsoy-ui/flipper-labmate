# LabMate v2.0 — P0-01 READ-ONLY baseline and first implementation gate

**Date:** 2026-10-21
**Status:** PC/GitHub **source provenance checked**, new branch/doc-only preparation; **NO v2.0 physical tests/builds performed**.

## A. Foundational checks performed via read-only GitHub queries

| ID | Probe | Observed result | Assessment |
|---|---|---|---|
| G-01 | Latest public v1.9 Release | Stable (`draft=false`, `prerelease=false`), published 2026-10-20, **E11-only** | VERIFIED by GitHub metadata |
| G-02 | Frozen source tag `v1.9` | `72eb58d6c65d31f510acf6f532ee23c543a9149d` | VERIFIED by Git ref |
| G-03 | v1.9 FAP release asset | 101468 bytes; SHA256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2` | VERIFIED by release metadata and prior Windows full byte readback; NOT newly downloaded here |
| G-04 | Ordinary GitHub Latest | `v1.8`, untouched | VERIFIED |
| G-05 | Ordinary `main` | Non-E11 source; last recorded `ba0004e00206b13331dd58e65157f785dbc4f114` (documentation-only landing-page update) | Read-only branch metadata; **not a v2.0 merge target** |
| G-06 | E11 v1.9 development branch | `dev/v1.9-logic-scope` at `eda2be6657e429478f89b942afc324af545a6276` | VERIFIED |
| G-07 | `v1.9` tag vs E11 dev branch | Dev branch ahead by **8 commits**; GitHub compare lists **only** 2 docs added + 3 release scripts added + 1 release script modified, **0** `src/`, test or `application.fam` changes | VERIFIED, **source identity maintained relative to v1.9 tag** |
| G-08 | Draft PRs | PR #13 E11 source and PR #15 Logic Scope both open/unmerged/draft at inspection | VERIFIED; **do not merge wholesale** |
| G-09 | v2.0 development branch | `dev/v2.0-signal-doctor` created from exact G-06 SHA | VERIFIED from branch creation response |
| G-10 | Firmware source ABI | E11 SDK source baseline `d3f89dfe2ef6b01839201598e9be1590cba80322` / SDK API 87.1 | Historic pinned build evidence only; **actual installed firmware image binary NOT newly attested** |

**Release archive safeguard:** v1.8 ordinary, historical v1.8 E11 and v1.9 E11-only original FAP assets and tags must remain byte-for-byte unchanged. P0-01 never downloads to / writes through USB to Flipper. No FAP deployment, no firmware flash, no SD or Profiles operation, no old installer.

## B. Source modules to inventory before changing one line

| Cluster | Starting source path(s) | Read-only questions for UI-00 |
|---|---|---|
| Event loop and app state | `src/labmate.c`, `src/labmate_internal.h` | What is owned by IRQ vs GUI? Which state is valid, live, held or stale? |
| Screen dispatch | `src/labmate_view.c` | Which physical screens/states draw via which function? What is current redraw cadence and button flow? |
| Legacy tools' renderer | `src/labmate_ui_screens.c` | Bounding boxes, title/value/footer collisions, overflow cases, long strings |
| Shared presentation functions | `src/labmate_ui_primitives.c` | Fonts, badge geometry, button labels and group/menu conventions |
| Menu navigation | `src/labmate_navigation.c` / `.h` | Preserve tool IDs, group order, About last and physical controls |
| Scope display and compare | `src/labmate_scope_display.c`, `src/labmate_scope_pair_view.c`, `src/labmate_scope_reference_view.c` | Real plotted edges, multiple pages, FAIL/PASS quality status, status/footer geometry |
| IRQ/measurement correctness | `src/labmate_scope_native.c`, `src/labmate_scope_bridge.c`, `src/labmate_scope_buffer.c`, `src/labmate_scope_compare.c` | **Read only** while designing UI. E11 lease/IRQ ownership and error states |
| Tests | `tests/test_labmate_ui_keylabels.c`, `tests/test_labmate_scope_display.c`, `tests/test_labmate_scope_pair_view.c`, `tests/test_scope_reference_view.c`, `tests/test_scope_pc1_pin_gate.c`, `tests/test_scope_buffer_timeguard.c` | Enumerate observed states and missing screen tests; **test runs PENDING** |

## C. First coding gate (NEXT ACTION, NOT DONE)

**UI-00 / P0-02:** build a **read-only 128×64 screen/state/layout inventory** and then (separate reviewed commit) implement a host-only pure UI geometry validator against the existing pinned source.

- Inventory must include all existing tools plus planned Dashboard and Doctor states, highlight real button meanings, unit/precision, overflow/truncation, BUSY/no-signal and every STOP/BACK path.
- Define rectangle nonintersection rules: content vs footer, title vs badge, pixel clipping, short/long numeric displays and glyph safety. For scope page, guarantee graph confined to viewport; never draw fabricated signal where no accepted capture exists.
- The first new test **must not** touch hardware, firmware SDK files, storage codec, profile slots, released binaries or ISR source. Treat mock/host evidence as host only.
- Before writing even the UI test, record actual source/git blob pins and a host compile command in a follow-on audit note. Do not claim host PASS until the exact command is run and logged. GitHub Actions was disabled in the v1.9 cycle; a workflow definition is not a passed run.
- After small host-test PASS and a genuine diff review, progress to one **UI-only** change on dev branch; preserve old screens and compare before/after rendering. No full UI rewrite in one commit.

## D. Parallel source and physical work queues

### Ordinary Momentum COMP-00 (READ ONLY)

- Catalogue E11-only lease and try-add IRQ API symbols and all additional I2C/1-Wire interfaces. Record what exists in the ordinary matched API before selecting shims.
- No normal-Momentum FAP compilation or release until independent exact SDK/API agreement and actual feature validation. Do not allow misleading feature 'PASS' merely because an API stub links.

### Hardware availability ledger (DEFERRED until equipment)

| ID | Evidence required | Equipment / policy |
|---|---|---|
| HW-01 | real button bounce/settle/debounce | dry-contact pushbutton |
| HW-02 | independent frequency/duty/OFF and amplitude | instructor's university oscilloscope; no purchase assumption |
| HW-03 | media-full/missing/corrupt CSV/profile handling | **spare disposable microSD**, original card untouched |
| HW-04 | external 3.3 V reference and supported alternative pins | independently safe pulse generator/USB logic analyzer |
| HW-05 | prolonged STOP/BACK/Logger/PWM sessions and data retention | backed-up Flipper and repeatable log |
| QA-01 | Microsoft Excel CSV import | when Excel legally available; LibreOffice success not enough |
| E11-I2C | real BME280 ACK, no device/lock timeout | known 3.3 V I2C breakout and safe wiring |
| E11-1W | actual DS18B20 CRC/conversion | correctly powered 3.3 V DS18B20 and correct pull-up |
| E11-OWN | native foreign client IRQ/lease arbitration | instrumented native E11 test, independent resource owner |
| E11-RECOVERY | exact firmware rollback and read-only backup attestation | reviewed device-specific image/recovery process, explicit authorization |

**No equipment bought, delivered or attached by the assistant; no HW test in this table is newly PASS.** Maintain the existing main backlog and extend it in a separate reviewed change only when more specific evidence is located.

## E. P0-01 pass conditions and output contract

P0-01 is **PASS as a source-/repository-only preparation** when:
1. New branch exists, anchored to an exact identified source SHA; all public tags unchanged.
2. This audit and the v2.0 technical roadmap are committed only to the new branch.
3. A small DRAFT PR explicitly targeting **`dev/v1.9-logic-scope`** exists, with **only** the new documentation files in its diff. It must not target ordinary `main` or imply general Momentum support.
4. No `src/`, `tests/`, `application.fam`, `scripts/`, `*.fap` or `*.dfu` changed in P0-01.
5. No Windows host tests, SDK builds or device operations are claimed as having been run in this first step.

**The next operational step after P0-01:** owner review of this exact roadmap and then **UI-00** state/layout inventory as another docs-only commit. The next *coding* action is the deterministic 128×64 UI test harness, with genuine host execution results before any on-device UI refactor.
