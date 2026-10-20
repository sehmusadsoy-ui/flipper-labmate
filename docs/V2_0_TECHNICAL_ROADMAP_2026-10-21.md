# LabMate v2.0 — Technical Master Roadmap / Signal Doctor

**Decision date:** 2026-10-21
**Status:** APPROVED PRODUCT AND ENGINEERING STRATEGY / IMPLEMENTATION NOT STARTED.
**Milestone name:** **LabMate Ultimate / Signal Doctor**.
**Priority:** Preserve the canonical feature roadmap: **Signal Doctor → unified measurement dashboard → advanced statistics → professional application-wide UX**, with quality and compatibility integrated in every stage.
**Owner decisions:** Primary firmware = *patched Momentum E11*; **ordinary Momentum is a separate compatibility workstream**; **one consistent professional UI across the entire application**; missing physical tests remain a **parallel equipment-dependent backlog**, never implicitly PASS.

## 0. Verified upstream baseline and immutable constraints

- Original, successfully published public [v1.9 E11-only Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.9), **single original app** `labmate`, single intended on-device FAP path `/ext/apps/Tools/labmate.fap`.
- Frozen exact compiled source commit and tag `v1.9`: `72eb58d6c65d31f510acf6f532ee23c543a9149d`; released FAP: **101,468 bytes**, SHA256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2`.
- E11 Momentum firmware **source** baseline: `d3f89dfe2ef6b01839201598e9be1590cba80322`, SDK API 87.1 plus custom lease/try-add-IRQ callback exports. **The source pin is not a fresh independent installed-firmware binary attestation.**
- The v1.9 dev branch head before starting v2.0 was `eda2be6657e429478f89b942afc324af545a6276`, verified as **8 commits ahead** of the exact v1.9 tagged source, with **only documentation and release-script diffs**, not application source changes. New isolated v2.0 branch `dev/v2.0-signal-doctor` begins from this reviewed head. Do not branch from ordinary `main` or merge a huge E11 delta into ordinary code to start v2.0.
- Ordinary-Momentum [v1.8 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) is intentionally GitHub's **Latest**; the separate [v1.8 E11 compatibility prerelease](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum) and [v1.9 Stable (E11 only)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.9) are all retained unchanged.
- The `main` manifest remains v1.8. The E11 source PR #13 and v1.9 scope PR #15 remain DRAFT/unmerged; publication of a tagged binary does not imply `main` source compatibility. No branch force push, release retagging, ABI guesswork or blanket merge.
- Preserve **`MEASURE → OUTPUT → RECORDS → COMM → INFO`** (INFO/About strictly last and COMM directly above), original numeric tool/screen IDs, old CSV filenames/layout and Profile S1–S3/CRC compatibility. No paid/Free decision supersedes the mandatory Signal Doctor/dashboard work.
- v1.9 source components to reuse rather than replace: `src/labmate.c`, `src/labmate_internal.h`, `src/labmate_navigation.c`, `src/labmate_view.c`, `src/labmate_ui_primitives.c`, `src/labmate_scope_bridge.c`, bounded `labmate_scope_buffer`, `labmate_scope_compare`, `labmate_scope_tolerance` and native E11 IRQ resource guards.
- **Known 1.9 demonstrated signal envelope:** physical PC1 100 Hz and 1 kHz at 50%; **not** an independent bandwidth or calibrated-timebase guarantee. Scope uses **256 observed edge records**, stop-after-32 auto rule, 5 s session maximum, 1 s trigger wait, 200 ms quiet timeout and <=100 ms poll-gap guard. It is single digital channel, **not analog nor simultaneous multi-channel**.

## 1. Target product contract — v2.0 must deliver ALL FOUR pillars

1. **Signal Doctor:** explain symptoms from genuine measurements with reproducible, bounded, testable rules; rank evidence and next check. Never assert a specific board/component is defective based only on an observed trace or internal loopback.
2. **Unified Dashboard:** show recent **validated** Frequency / Pulse / Scope / Counter / Logger observations and status with provenance (pin, time, source, signal state, truncated/error flags). A dashboard is *not* permission for simultaneous GPIO/IRQ acquisitions; use safe, serial ownership or explicit source availability.
3. **Advanced signal analytics:** statistics based solely on captured cycles/events and historical CSV where semantics match: mean, min/max, deviation/jitter estimate with valid sample count; no fabricated sample or interpolation. Mark unsupported quantities `N/A`.
4. **Professional 128×64 monochrome UI across ALL tools:** shared typography, grid, statuses, navigation, action footer, selection focus, errors and empty/loading/invalid states. Preserve responsive input, clean STOP/BACK and all original tools.

**Explicitly excluded unless separately prototyped, independently benchmarked and approved:** analog voltage scope, analog amplitude plots, concurrent multichannel high-speed capture, unfounded MHz/sample-rate claims, automatic active GPIO probing, automatic generator start, automatic firmware flash, rewriting legacy CSV/Profiles, speculative Premium gating.

## 2. Engineering phases and mandatory gates

| Phase | Implementation scope | Evidence / acceptance gate |
|---|---|---|
| **0 — Baseline and safety** | Open isolated branch, freeze tag/ABI/data invariants, inventory screens, GPIO owners and test gaps, define acceptance IDs, PC-only read-only repository audit | Exact release source/asset pins; source-tree diff classification; host code untouched; no USB/device/SD writes; reviewable docs-only Draft PR |
| **1 — UI design system** | Shared 128×64 screen anatomy + `UiTheme`-like constants, font/baseline/gutter metrics, header/metric blocks/status/error badges and footer actions; standard input hints; no change to measurement logic | Host GUI-stub/draw-boundary tests for every screen/state; zero clipping, overlap, unsupported glyph and conflicting button hints; 128×64 screen inspection; legacy navigation/input regressions |
| **2 — Unified measurement snapshot/dashboard** | Define *new, explicitly versioned internal snapshot* (proposal only) carrying origin, pin, timestamps, measurement units, good/invalid/no-signal/busy quality, actual sample count, overflow/error; produce snapshots from existing tools without changing their IRQ algorithms; dashboard with safe stale-data indication | Pure C aggregation tests; no live capture while conflicting owner busy; no reconstructed or stale values labelled LIVE; history/profile/data unchanged; bounded RAM and redraw |
| **3 — Signal Doctor** | A **pure C, deterministic, read-only rule engine**, testable without Flipper HAL; rules for no valid signal, stuck HIGH/LOW after genuine observation window, missing pulses/dropout only with sufficient temporal evidence, out-of-tolerance frequency/duty, unstable pulses; explanation + next safe check + confidence/quality | Each rule tested with positive, negative, missing-data, overflow, incompatible timebase and contradictory evidence. No PASS or fault diagnosis for no-signal/insufficient evidence. No automatic GPIO/UART/PWM access; multilingual prose only if rendering permits |
| **4 — Advanced analytics and workflows** | Compute real min/max/mean and bounded spread using observed valid cycles; view normalized readings and history, optional explicit versioned CSV export; step-by-step troubleshooting screens integrated with original Logger/Profiles | Host integer/saturation/wrap/invalid datasets; old/new CSV header and CRC fixture tests; no migration or write unless expressly authorized and backed up |
| **5 — E11 hardening + independent normal Momentum track** | For E11: resource-lease, IRQ/stack/performance and native-service collision audits; no regressions in UART/I2C/1-Wire/PWM/GPIO/Counter. For normal Momentum: independently list unsupported native E11 interfaces, design fail-closed shim or consciously remove unsupported functions in a separately labelled build | E11 exact-SDK build and APPCHK evidence; status of actual CI explicitly reported; resource refusal/STOP/BACK normal & fault-path tests; a normal SDK build is **NOT** proof of functional compatibility; no ordinary Latest promotion without separate acceptance |
| **6 — v2.0 release acceptance** | Full GUI + all instruments physical regression, multi-minute sessions, external-reference measurements as available, compatibility+upgrade/rollback guide, exact FAP source and SHA256, release-channel decision | Operator device acceptance, independent equipment status clearly marked, GitHub published asset readback; only accepted exact binary gets Stable. No auto merge, firmware flash or tag mutation |

**Phasing:** Common UI foundations may be developed before full Doctor functionality; pure-data rule tests can run independently once snapshot semantics are frozen. UI integration waits for coherent safe measurement contracts. Equipment-dependent physical tests are conducted in parallel **when available**, not blocking unrelated host-only milestones. Critical discovered correctness or safety failures block affected features irrespective of equipment availability.

## 3. Professional UI design contract (Flipper Zero)

128×64 **monochrome**, physically legible and direct-key-driven. **One shared design system across all screens**, not isolated decoration of Logic Scope.

- Define a shared safe screen layout: title/context/pin, primary observed value, secondary status/units, content region, action-hint footer. All coordinates/width calculations and font labels are centralized; no 2-pixel collisions or cropped text.
- Consistent inverse/outline selection, font weights, key legends **matching real physical button semantics**, and explicit RUN/HOLD/STOP/ARMED/NO SIGNAL/BUSY/ERROR indication without ambiguity. Keep back/stop available on all navigable routes, including long names, empty log, invalid samples and resource busy.
- Preserve root menu order and Info/About last, plus all existing tool features. Do not silently turn a displayed measurement into a new GPIO consumer.
- Scope graph: keep **actual observed** transitions, bounded viewport, no phantom pretrigger or calibrated graticule claims; meaningful labels and no modal overlap.
- Prepare a **screen inventory + state matrix** before implementing a new style. Candidate views: root/submenu, GPIO, Frequency, Pulse, Generator, Counter, Button, Alerts, Logger, History/Details, Profiles, UART, I2C, OneWire, Scope four pages, About, and planned Dashboard/Doctor.
- Use host-GUI snapshots/geometry tests as early regression artifacts; hand-review final screens on real Flipper. UI-only patch must never secretly change IRQ, storage, PWM or native firmware files.
- Maintain at least the existing 10 Hz normal redraw control unless measured CPU/latency data justifies another value. Plan actual **measured** heap/stack/render/ISR budgets in Phase 0/5; no invented performance benchmark.

## 4. Signal Doctor data and rule interface (DESIGN PROPOSAL, not shipped)

Separate real capture/measurement from inference. A **versioned, immutable measurement snapshot** might contain:

```text
MeasurementSnapshotV1:
  tool / pin / source / capture_generation
  timebase_hz / observation_start_ms / observation_end_ms
  frequency_millihz / duty_permille / high_ticks / low_ticks / period_ticks
  valid_cycle_count / observed_edge_count / dropped_edge_count
  quality = VALID | INSUFFICIENT | NO_SIGNAL_CONFIRMED | BUSY | OVERFLOW |
            CLOCK_UNSAFE | INVALID | STALE
  ownership_teardown_confirmed
```

These field names are a proposal, not current compiled source. Distinguish app-local timestamps from an externally calibrated wall clock; timestamps must be comparable before cross-tool inference. The dashboard may store only bounded, in-memory snapshots initially. No extra SD writes.

```text
SignalDoctorResultV1:
  finding_id / observed_symptom / evidence_fields / severity
  confidence = SUPPORTED | SUGGESTIVE | INSUFFICIENT
  recommended_next_safe_test / limitations
```

Rule policy:
- **NO SIGNAL** only after confirmed observation/no-trigger timeout and valid acquisition. `INSUFFICIENT` before such proof.
- **STUCK HIGH/LOW** requires verified stationary level over a sufficient configured observation interval. A zero-edge screenshot alone never proves a line is stuck.
- **FREQUENCY/DUTY OUT OF RANGE** requires a valid measured sample and an explicitly selected reference/tolerance. Display quantitative error and how many cycles were used.
- **INSTABILITY / DROPOUT** requires multiple valid complete cycles and a justified baseline; one partial window or overflow cannot support it.
- **CONFIDENCE** is an evidence grade, not a numeric pseudo-probability unless empirically calibrated. Findings are *diagnostic hypotheses*, never automatic fault certifications.
- No hidden output drive, reconfiguring foreign pins, ISR storage, blocking mutex in ISR, or background telemetry.

## 5. Two compatibility workstreams with separate pass criteria

### A. Primary: patched E11 Momentum (active)

- Build against the **same pinned E11 firmware source/API** until a deliberately reviewed upgrade.
- Native acquisition must acquire true firmware leases/nonasserting callbacks before registering IRQ or changing pin mode; reject ownership conflict with no foreign register writes.
- Preserve `labmate.fap` and `appid=labmate`, exact prior v1.9 and original v1.8 binaries, PC+device FAP backups, original CSV/Profile S1–S3; no default firmware flashing.
- One active IRQ capture source at a time unless a *separately proved* supported combination is added; preserve PA7 PWM independence and safe STOP.

### B. Secondary: ordinary Momentum compatibility (parallel but independent)

- Start with **read-only capability matrix**, E11-only symbols, baseline SDK/API export differences; no copying E11 FAP onto a stock device.
- Choose independently per feature: shim through documented supported ordinary APIs, disable with an explicit error, or defer. **No silent feature degradation that the UI labels as working.**
- Build a **separate binary and separate documented release channel** only after genuine native/API proof and physical tests. Do not infer ordinary support from matching version numbers or C compilation.
- Keep ordinary [v1.8 Latest](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) until the independently accepted successor exists. v2.0 E11 Stable may be the first v2.0 target if ordinary work is still pending.

## 6. Outstanding historical validation carried as PARALLEL, not false PASS

- `HW-01` dry-contact button bounce/settle/debounce.
- `HW-02` independent PWM amplitude / frequency / duty / OFF verification. **Use the former university's oscilloscope with instructor; do not assume an oscilloscope purchase**.
- `HW-03` missing/full/corrupt-media failures only on **disposable spare microSD**.
- `HW-04` independent 3.3 V pulse stimulus, alternate digital input pins and extreme frequency/duty combinations; external logic analyzer useful.
- `HW-05` extended runtime (PWM, logger, navigation, STOP/RESTART), old CSV/Profiles preservation.
- `QA-01` Microsoft Excel actual CSV import; LibreOffice Calc already passed, Excel not tested.
- **E11-specific outstanding:** true BME280 I2C ACK, true DS18B20 CRC+conversion, unexpected external I2C lock/cancellation, independent foreign-client native IRQ/lease contention, actual resource lifecycle fault injection, and exact prior custom-firmware rollback.
- Historical handoff mentions `HW-01…HW-19` as broader native-device checks, but the main visible `docs/DEFERRED_HARDWARE_TESTS.md` explicitly lists only `HW-01…HW-05` and `QA-01`. **Do not invent missing HW-06…HW-19 statuses**; inventory their other source documents before claiming closure.
- Physical evidence template: exact FAP SHA + firmware source/native ABI, fixture/wiring/3.3 V, procedure, raw expected/observed figures and screenshots/logs, pass/fail/deferred with date.

## 7. Gates that forbid premature v2.0 Stable

- Source implemented ≠ host test PASS ≠ SDK build PASS ≠ physical operator PASS ≠ independent calibration.
- Explicit test matrices for every rule and screen; CPU/heap/stack/IRQ and GUI redraw limits measured, never assumed. Use the exact E11 SDK, verify FAP exported APIs, confirm no unapproved firmware actions.
- Unavailable optional equipment can remain **DEFERRED with approval and clear limitations**; any discovered wrong measurement, unsafe release, false Doctor PASS, data loss or false compatibility blocks the affected release.
- All original tool menus work; `MEASURE → OUTPUT → RECORDS → COMM → INFO` preserved; no cosmetic UI work deletes features. Old CSV and CRC Profiles remain readable.
- Publish v2.0 only after the integrated **Signal Doctor + Dashboard + Analytics + UI redesign** acceptance. No fake version-completion from a mock screen or merely compiling a FAP.
- v2.0 commercial/Premium design is optional, later and separate. No functionality locked or licensing scheme implemented without a new product decision.

## 8. Explicit first safe step

**P0-01 — docs/branch-only provenance and compatibility freeze.**
1. Create branch `dev/v2.0-signal-doctor` from inspected `dev/v1.9-logic-scope` head `eda2be6657e429478f89b942afc324af545a6276`. Verify source `src/` and `application.fam` remain the published v1.9 tag content.
2. Commit **only roadmap and read-only baseline audit**, no executable software changes. Open a DRAFT PR for review against `dev/v1.9-logic-scope`; never merge to ordinary `main`.
3. Define first deliverable `UI-00`: a **read-only inventory of actual existing screen states and view geometry** in `src/labmate_view.c`, `src/labmate_ui_screens.c`, `src/labmate_ui_primitives.c`, `src/labmate_navigation.c`, `src/labmate_scope_display.c`. Record baseline host tests. Future changes first add isolated UI boundary/flow host tests before editing renderers.
4. Parallel workstream `COMP-00`: read-only list of E11-only native exports and ordinary Momentum API alternatives, NOT a new FAP.
5. Run the first actual new host test/build only AFTER `P0-01` review. **No Flipper USB writes, firmware flashing, app installing, release tagging or CI auto publishing in P0-01**.

**Current progress classification after this document alone:** DECISIONS RECORDED and new branch prepared; *no v2.0 code implemented, host tests executed, E11 FAP built, physical tests performed, or compatibility unlocked*.
