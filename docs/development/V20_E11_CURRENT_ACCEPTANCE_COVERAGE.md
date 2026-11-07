# Current E11 software acceptance and historical assertion mapping

2026-11-07. Base: `55b862970722a681c735de91e9efa78eddadc3dc`. Supported scope is the approved E11 baseline, not every feature ever tried on the other v2 branches. No product UI was changed to satisfy historical tests. No device, firmware or SD writes are performed by these host runners.

Canonical current entry point: `sh scripts/test-v20-e11-current-software-host.sh`. Inventory entry point: `sh scripts/audit-v20-e11-legacy-coverage.sh`. The inventory executes that canonical gate once, propagates every current failure, and separately requires the historical LevelWitness entry point to return 77. It never counts 77 as PASS. `test-v20-offline-full-host.sh` is a compatibility alias to the canonical gate.

`tests/test_v20_coverage_inventory.py` failure-injects the exact inventory in temporary fixtures: a current exit23 must propagate; a valid retired77 + current0 reports both distinctly and executes current only once; a retired guard exit9 fails closed; an unexpected retired PASS is an error. These four tests prevent the former always-green inventory behavior from returning.

Original red evidence remains in the 2026-11-06 local audit logs (`host-qa.md`, `host-effective-results.json`, `host-logs/`). Original Python contracts and offline/inventory scripts are also retained verbatim under `tests/historical/*.txt`. The historical C LevelWitness, ScopeDiagnostics and tile-menu fixtures remain in `tests/` as historical records; the named runners now declare their mapping below. New tests compile current production helpers/bodies, rather than restoring removed product code.

## Complete old C assertion mapping

| Historical assertion(s) | Current assertion / explicit boundary |
|---|---|
| Frequency live policy: every one of 64 high-pin / high-active / low-active / owner / blocked / release-fault combinations | Identical loop and expected expression retained in `test_v20_frequency_ui_state.c`, now including production `labmate_capture_live.h`; old missing `.c` link removed because the helper is inline. The `valid == 2` assertion is unchanged. |
| Frequency runner's menu entry, mode switch, Pulse mode, retry ownership source checks | Original source checks retained verbatim in the runner. |
| Pulse resume: all 16 IRQ / owner / blocked / release-fault combinations | Identical loop, `live == (mask == 3)` and `accepted == 1` retained against production `labmate_capture_live.h`. |
| Pulse runner's actual OK-resume and menu-entry call site / fault checks, and prohibition of unconditional `hold=false` | Original source checks retained verbatim. |
| Scope uniform edge train computes valid four cycles and mean 1000 | `test_v20_scope_diagnostics_current.c` calls real `labmate_scope_metrics_from_edges` + `labmate_scope_period_stats`, checks Ready / 4 cycles / mean 1000. |
| Scope uniform `spread_permille == 0`, no suspected gap | Current period statistics must return spread 0; real Doctor symptom analysis must return Ready, flags 0 and gap_count 0. |
| Scope uniform mean absolute deviation 0 | **RETIRED output, no equivalent claim.** `LabMateScopeDiagnostics` / MAD implementation was deleted in approved commit `880beaca6a932168cd6c06c0f30f01410eab62f4`. Current spread is not relabeled MAD. |
| Scope one doubled period: min 1000, max 2000, mean 1250 | Exact values checked through current period-statistics API; current descriptive spread additionally checked as 800 permille. |
| Scope doubled-period gap suspicion | Current actual Doctor median-interval policy must flag MISSING_PULSE, detect two doubled half-intervals and report worst ratio 2000 permille. This is the current policy, not the old `gap_suspected` algorithm. |
| Scope doubled-period MAD 375 | **RETIRED output, unproven**, not asserted or simulated. |
| Scope repeated same-level edge returns false and invalidates output | Current metrics returns Invalid and cannot yield period stats; current Doctor returns Unsafe with zero flags. Different API status spelling is explicit. |
| Scope zero delta rejected | Same metrics Invalid / no stats / Doctor Unsafe + zero flags assertions. |
| Scope zero timebase rejected | Current metrics ClockInvalid / no period stats. Doctor clock-fault policy is not inferred from merely passing a zero numeric timebase. |
| Scope count 2 rejected | Current metrics Insufficient / no period stats; Doctor Insufficient + zero flags. |
| Scope null edges rejected | Current metrics Invalid / no stats; Doctor Unsafe + zero flags. |
| Scope null output rejected | Current Doctor and period-statistics APIs reject null output. |
| LevelWitness sampled HIGH; sampled LOW; changed observation -> Transitions | **RETIRED and unmapped.** The complete polling witness feature was removed in approved `880beac`. Current GPIO's display-only trace is not evidence certification. |
| LevelWitness insufficient requested observation duration; pin change; 300ms poll gap; failed native release | **RETIRED and unmapped.** No current-module assertions claim these were exercised. |
| LevelWitness invalid pin 8; zero clock; null witness | **RETIRED and unmapped.** `test-v20-level-witness-host.sh` checks production no longer contains this module or references, then exits **77 / NOT ACCEPTANCE**. The old C fixture is preserved. If references reappear the retirement guard fails. |
| Old menu Canvas: nonempty printable ASCII, bounded rectangles/lines/glyphs, no text overlap, restored black color | Preserved in new `test_v20_menu_current.c` using extracted unchanged production `draw_menu`, all five routing/name/icon helpers, and eleven real current chrome/text/tween functions. |
| Old menu iterates all five root selections and all 17 submenu selections | Preserved and expanded to 651 selections/transitions: all routes, every list previous/selected pair and six tween frames plus settled state, both carousel directions, and out-of-range selected fallback. |
| Old root must have ten text paints and icon-free cards x=7/71, y=24/36/48 | **RETIRED grid geometry.** Current root asserts brand/version at baseline 8, title 46, detail 55; current literal group names and V2.0 are independently asserted. Current icon count, icon bounds and actual chrome are checked. |
| Old root footer three labels at y=61, x=2/45/96 with 30px glyph width | **RETIRED footer geometry**, replaced by approved carousel and page dots. No product footer was added. Real current page-dot drawing executes in the new geometry test. |
| Old submenu x=99,y=9 focused-index badge | **RETIRED badge.** Current three-row list checks every visible tool's row, title fit, focus-pill position, route count, text/icon bounds and optional fourth hint. |
| Old icon function frame internals | Icon ABI calls and rectangle bounds are mocked and counted. **Actual glyph/bitmap raster remains unproven here**, requiring device screen review. |

## Original Python UI contract: assertion-by-assertion disposition

The archived `test-v20-ultimate-ui-contract-before-e11-reconciliation.py.txt` is the line-reference source below. Its live filename delegates to `audit-v20-e11-software-contract.py`; this is an explicitly changed current contract, not a PASS of the original text expectations.

| Original assertion / original line(s) | Current disposition |
|---|---|
| All 16 renderers must call `ui_draw_header`, lines 38 | Historical helper spelling **retired**. Current 13-screen E11 contract checks actual current screen helpers; new software contract inspects all 16 actual bodies for passive I/O. Real menu/header/footer/draw integrations execute in canonical pixel suites. |
| All 16 must use pair/triple/info footer, lines 39–41 | Universal old footer **retired**; screen-specific current contracts apply. The root intentionally has no former footer. Actual pair/triple quiet footers remain covered by UI06; current menu geometry is compiled. |
| History detail read-only footer, lines 42–44 | Meaning retained: current body must contain READ ONLY / UiKitKeyBack / SD READ ERROR; UI04 executes actual records renderers. Old literal `ui_footer_info` spelling retired. |
| No GPIO/resource acquisition/storage writes from rendering, lines 45–47 | All 16 extracted production bodies checked for the original forbidden operations. GPIO may update only its existing presentation cache; no GPIO I/O is inferred from paint. |
| Root grid/tile use; text-first cards; old version/footer/index/disclosure positions, lines 48–64 | Old geometry explicitly retired as above; all current routes/tweens/visible rows compile in the actual-source menu test. Stable navigation IDs/counts/wrap are covered by root navigation + UI01 + pair/navigation integration. |
| Pulse STATS dispatch, both live/hold footer layouts and DUTY baseline, lines 65–73 | Existing UI05D compiles actual `draw_pulse`, `draw_pulse_stats` and current chrome against independently asserted states/values/geometry. Old literal strings/positions are not restored. |
| FREQ/PWM/PULSE shared-heading strings, lines 74–77 | Actual current renderers and current screen/state contracts are exercised by UI05D. Old heading helper/names retired. |
| Dashboard / Doctor shared header/footer, lines 78–89 | Old shared-helper requirements retired. Software contract checks current Doctor result dispatch, read-only presenter bodies and current Dashboard sealed provenance; panel/assessment, dashboard and stats suites run. Physical result-screen raster remains open. |
| Scope dedicated title/footer, lines 90–94 | Current display must keep measured complete/nontruncated validity gate, current pixel header and actual OK control; Scope reference/compare/sample current geometry tests run. The unused legacy helper spelling is not claimed. |
| Five group labels ending INFO, lines 95–97 | Group enum and persisted IDs remain stable; displayed final group was approved as SETTINGS. Current label table and 17-tool coverage are asserted. |
| Doctor and Dashboard tools present, line 98 | Current stable enum/order, menu route, input/view dispatch and retained help table checks preserved. |

## Original Ultimate source audit: every assertion family

The archived `audit-v20-ultimate-sources-before-e11-reconciliation.py.txt` is authoritative. `contains(path, tuple)` expands to one assertion per token; all tokens within each listed family have the same disposition unless individually called out.

| Original assertion family | Replacement or explicit retirement |
|---|---|
| App ID, name, manifest/display version, no v1.9DEV | Retained in current source contract, plus explicit `sources=["src/*.c"]` host-test exclusion. |
| Historical tool enum/order, Invalid sentinel | Retained verbatim as the full 18-entry sequence including Count. |
| Navigation group sizes, records ordering, Doctor/Dashboard labels | Current actual navigation C tests cover group sizes, all 17 tools exactly once, valid names and stable IDs. INFO display label changed to SETTINGS; other group order remains checked. |
| About's literal “17 tool guides” | Old dead help-table literal retired; current `LABMATE_INFO_GUIDE_COUNT == 17` and bounded `labmate_info_guide()` lookup checked. |
| Doctor/Dashboard screen enums, input/view cases, menu/help entries | Retained. |
| Doctor status y=50 / ADVISORY ONLY literal / old layout constants and shared footer y=52 | Old renderer-specific layout/text retired. Current Doctor result dispatch/passivity, assessment source models and approved source guard apply; **no claim of current full font raster proof**. |
| Dashboard sources, read-measurement, stats, evidence page, SEALED/NOT LIVE text | Current contract retains all five source labels and API/wiring/evidence-page checks. Existing dashboard tests also retain the original SEALED/NOT LIVE literal check; current historical-only detail is checked additionally. |
| Advice NO SEALED DATA / CAPTURE + STOP / NO EDGES SEEN | Retained. |
| Stats can-display quality gate / bounded max sessions | Retained, plus actual GCC/Clang statistics tests. |
| Period metrics Ready / >=2 cycles / no truncation / spread | Actual `test_v20_scope_period_stats.c` remains in canonical core; migrated scope tests add real edge-to-statistics cases. |
| Scope diagnostics MAD / gap API | MAD explicitly retired. Cycle/spread/gap/invalid cases mapped above to current real production APIs. |
| Frequency/Pulse standalone state modules and Pulse retry call | Functions moved to production inline header; every original truth-table assertion and source retry checks preserved. |
| LevelWitness module, begin/observe/finish/invalidate wiring, Doctor GPIO source/polling/NO LEVEL EVIDENCE labels | **Retired in entirety, unmapped**, exit77. Not substituted with Scope stuck-line symptoms or GPIO display trace. |
| Menu tile/grid helpers, root-move wiring | **Retired geometry**, current actual menu + full navigation tests replace supported routes; no old tile helper is restored. |
| Clear-source in menu input | Location changed: current contract requires real clear-source calls in Frequency/Pulse bridges, Scope bridge, Counter and Logger; actual store source-isolation tests remain in canonical suite. |
| Frequency/Pulse finish -> dashboard ingest -> stats record | Retained for both production bridge files. |
| Scope native safe reinit + dashboard ingest | Retained. |
| Counter pending-lease gate, session start total, dashboard ingest | Retained. |
| Logger captured pin/source, finalize, dashboard ingest | Retained. New persistence integration additionally tests real write/flush/close/fault paths. |
| Four presenters contain no native GPIO/bus/acquire/storage open/write | Retained. |
| Mandatory runner files exist | Canonical shell invokes every current required runner directly and fails if missing. Retired LevelWitness is explicitly separate; old filenames remain compatibility routes with this mapping, not extra independent successes. |

## CI and source guard

The combined workflow accepts the existing development branch and `audit/software-fixes-20261107`; manual invocation and relevant manifest/source/test/script/coverage-ledger edits trigger the current inventory. It is read-only with respect to GitHub contents and cannot install a FAP or publish a Release.

The UI source guard includes index + working-tree state. Native/input sources remain frozen against the accepted ancestor. Only two exact reviewed replacements are allowed: OneWire failed-release-safe menu reentry and Logger's close-before-retry block after a CREATE_NEW collision. Every other menu/logger alteration fails the guard. Approved draw bodies remain frozen.

“Current supported software host acceptance PASS” means only this documented scope. It excludes retired features and does not establish loader/OOM soak stability, real SD durability/fault recovery, resource contention, a screen's actual font/bitmap raster, signal calibration, or electrical behavior. Those statuses must be reported separately; this gate must never print “only physical tests remain.”

## Local validation, 2026-11-07

One final `inventory → canonical` execution completed with exit0 in 73.65 seconds after the software corrections and migration. It exercised the full current UI/core/evidence gates, real persistence/deferred adapters, the unchanged 64/16 LIVE truth tables, 651 current menu scenarios per compiler, current Scope edge/statistics/symptom cases and four inventory exit-status regressions. LevelWitness returned77 separately and was **not** counted as passing.

Local evidence: `audit/current-software-final-2026-11-07.log` and `.json` outside the repository copy. The run used HEAD `55b8629` plus the staged/working-tree corrections, not a final published commit SHA. New GitHub CI remains necessary for any eventual review commit. No new release/device claim follows from this host result.
