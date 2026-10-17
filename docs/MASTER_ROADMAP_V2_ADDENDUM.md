# LabMate Master Roadmap — Compatibility and Quality Addendum (2026-10-15)

> **Dated update — 2026-10-17:** This addendum was approved on 2026-10-15 and
> preserved as originally authored below; items describing E11 as
> 'ACTIVE / not published' are historical instructions at that date.
> A compatibility-limited [E11 Custom Momentum pre-release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum)
> was subsequently published on 2026-10-17; original
> [v1.8 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8)
> remains the ordinary Latest release, and the E11 integration PR #13
> remains Draft/unmerged to main. Operator-reported UI/UART/PWM/STOP/
> CSV/Profile evidence PASSED on one matched device. Remaining hardware
> fixtures, full native-service arbitration and exact custom-firmware
> rollback are **not** thereby automatically PASS/closed.
> The current reconciliation of both roadmaps is
> [v1.9 pre-start audit](V1_9_PRESTART_TWO_ROADMAP_AUDIT_2026-10-17.md).
> In a conflict, original feature commitments in `ROADMAP.md` retain
> precedence. No v1.9 implementation or v2.0 release has been claimed.



> **Operator-approved supplementary plan, NOT a replacement roadmap.**
> The operator approved the expanded reliability/firmware-compatibility
> approach on 2026-10-15 **only on condition that the old roadmap stays
> intact and future development does not drift from it**.
>
> **Canonical roadmap:** [`../ROADMAP.md`](../ROADMAP.md), including
> its original 2026-10-08 vision, version milestones and development rules.
> **Current v1.8 original-scope checklist:**
> [`V1_8_ORIGINAL_SCOPE_COMPLETION.md`](V1_8_ORIGINAL_SCOPE_COMPLETION.md).
> **Physical evidence / release gates:**
> [`V1_8_PHYSICAL_ACCEPTANCE_GATE.md`](V1_8_PHYSICAL_ACCEPTANCE_GATE.md).
>
> The prior `ROADMAP.md` and historical GitHub Stable tags, releases,
> checksums and device results are **not edited or retroactively redefined**
> by this addendum. If any proposed addendum work conflicts with the
> original feature scope or release order, **the original roadmap wins**.
> Changing that precedence requires a separate explicit operator decision.

## The preserved milestones — no renaming or scope replacement

| Milestone | Original, mandatory feature direction | Additional quality/compatibility work | Release condition |
| --- | --- | --- | --- |
| **v1.5 — Data Logger** | CSV frequency/pulse capture, session history, safe rate-limited SD writes, Excel-compatible structure and useful file status | Independent CSV audit/host-device hash evidence; actual Microsoft Excel remains untested when unavailable | Historical Stable and evidence preserved |
| **v1.6 — Code and UI Refactoring** | Modular app, grouped menus, saved profiles, centralized GPIO/peripheral ownership, single-app PowerShell/USB installation, resource/screen regression | Finish incomplete local cleanup, audit **firmware-wide** shared resource ownership against other services (not just LabMate local flags) | Previously published historical Stable preserved; critical incomplete ownership work incorporated into v1.8 completion |
| **v1.7 — PWM Studio and Counter** | Adjustable PWM duty and custom frequency; true event counter, Button Analyzer, Threshold Alerts; physical switching/measurement tests | Honest measured-accuracy and capture-limit tracking; avoid calling no-wire UI checks electrical calibration | Previously published historical Stable preserved; new firmware/FAP regressions required where relevant |
| **v1.8 — Communication Tools** | 3.3 V UART Terminal; real I2C Explorer with owned/peripheral-safe bus; optional real 1-Wire DS18B20 if feasible; timeout/conflict/release | Pinned matched Momentum/FAP, read-only checksum audit, safe backup/rollback plan and firmware service owner review | **ACTIVE — complete original scope in DEV, obtain operator physical acceptance; do not start v1.9 or publish revised v1.8 Stable early** |
| **v1.9 — Logic Scope and Signal Compare** | Bounded **digital** HIGH/LOW timeline; timestamp/event capture, triggers/overflow, reference profiles and tolerance-based comparison; realistic CPU/RAM performance tests | Momentum version/API/SDK compatibility checks, upgrade preflight, recovery documentation, diagnostic errors and automated regression workflows **support** the original v1.9 features; they do **not** replace Logic Scope or Signal Compare | Start only when v1.8 completion gate is explicitly resolved |
| **v2.0 — LabMate Ultimate** | **Signal Doctor**, unified dashboard, measurement-driven troubleshooting, advanced signal analysis/statistics and polished instrument UI | Explore free/Premium architecture, transparent feature boundaries and maintainable offline experience as an **additional design track**. Licensing/monetization details require a separate product decision; never remove original Signal Doctor or dashboard targets | Start only after v1.9 Stable and its original feature acceptance |

### Preservation of historical project facts

- The already published original `v1.8` Stable asset was an explicitly
  **reduced-scope** release, a fact retained in `ROADMAP.md`.
  Its past PASS results must not be rewritten as physical I2C/DS18B20
  results. Current original-scope **completion** is reopened in
  `dev/v1.8-completion` / Draft PR #13; this is not a new v1.8.1.
- Original later roadmap titles are **v1.9 Logic Scope and Signal
  Compare** and **v2.0 LabMate Ultimate / Signal Doctor**. Any prior
  shorthand suggesting that v1.9 becomes only
  "Compatibility & Reliability" or v2.0 becomes only "Premium"
  is superseded by this clarification. Both additions are **enablers**,
  never silent substitutions for original milestone features.
- Retain the root order `MEASURE → OUTPUT → RECORDS → COMM → INFO`.
  **INFO/About must remain last**, with COMM immediately before it.
  Keep one canonical app ID and path
  `/ext/apps/Tools/labmate.fap`, existing tool IDs,
  profile binary compatibility and CSV formats.
- Preserve old Stable tags/releases and rollback files unchanged;
  no automatic USB device action or firmware flash from CI.

## Immediate ordered work — finish **v1.8**, not v1.9

1. **Latest development FAP:** verify the completed patched Momentum
   + LabMate full-build CI run
   [38645876409](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38645876409).
   Inspect official artifact `11931799735`, its `SHA256SUMS.txt`,
   `PROVENANCE.txt`, exact FAP and DFU digests and
   `APPCHK`. Do **not** infer any new FAP SHA until actually read.
   Installed firmware is the pinned customized Momentum
   `d3f89dfe2ef6b01839201598e9be1590cba80322`;
   the original paired expected DFU digest is
   `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`.
   The installed older UARTFIX FAP SHA-256 is
   `eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf`.
2. **Safe FAP-only staging, then device acceptance:** if exact DFU
   equality and FAP provenance are proven, prepare a fail-closed
   **stage-only** verification procedure; preserve the user's backups.
   Obtain explicit approval prior to any FAP USB install. Do not
   reflexively reflash firmware. Repeat source-change-specific
   capture/EXIT cleanup, UART throughput, PWM/Logger, I2C empty-bus
   cancel, 1-Wire no-sensor, Profiles/CSV preservation as appropriate.
3. **Complete v1.6-level firmware service coordination:** audit real
   TIM1/TIM2/EXTI/GPIO/UART/I2C/1-Wire ownership, failed acquire
   and STOP/BACK/restart. Distinguish real exported firmware
   locks/leases from LabMate-only `capture_owner` and
   `comm_owner`. Where global ownership cannot be implemented
   safely with supported firmware contracts, do not fake completeness:
   explicitly document the incompatibility/deny risky operations
   and require operator agreement on any outstanding release blocker.
4. **Real signal tests and optional hardware fixtures:** repeat real
   3.3 V-safe source checks against a known compatible peer where
   pinout/power/ownership are independently verified; record the
   exact waveform/threshold/button/counter evidence. Real I2C
   positive ACK and real DS18B20 CRC/conversion cannot be marked
   PASS without safe available fixtures; the optional sensor
   may be explicitly deferred only by operator decision, not
   silently removed. A screen reading `NONE` is not a sensor PASS.
5. **Data/restore and final approval:** preserve S1/S2 and existing
   files; independently verify relevant backups. Historical
   `log_0056.csv` content and host/device hash and disposable S3
   SAVE/LOAD/DELETE already have physical evidence, not power-fail
   recovery or a rehearsed firmware restore. Decide which missing
   **individual equipment-dependent tests** may be documented as
   DEFERRED under the original gate. Fix genuine functional
   blockers before any Stable decision.
6. **Stable boundary:** only after a checksummed exact-source
   pair, operator on-device regressions, release notes and an
   explicit approval should a revised **in-place v1.8 asset**
   be considered. Do not silently retag the historical v1.8
   source. No `v1.8.1`, no merge of v1.9 PR #10, and no early
   v2.0 Premium implementation.

## Compatibility maintenance design, without changing milestone content

- Maintain a **read-only compatibility matrix** for each
  Momentum version/commit, firmware API/SDK version, patched
  bounded external I2C capability, single compatible FAP SHA,
  tested external peer(s) and exact device acceptance.
- Standard Momentum builds may fail closed for unsupported
  I2C firmware APIs. A stock-SDK CI build must not be claimed
  fully functional if the feature reports `FW API`. Avoid
  mixing a patched-API FAP with an unpatched firmware.
- If a future Momentum version ships, first inspect changed
  APIs/pin owners, rebuild against that exact version, run
  source/SDK/host tests, verify matched binaries, preserve
  backup/rollback options and **request user approval** before
  installation. A new upstream version never silently upgrades
  the user's Flipper.
- No second production LabMate app, no multiple stale FAP files,
  no misleading self-calibration or perfect-measurement claims.
- These tasks can be **designed** during v1.8 completion as
  maintenance infrastructure. They do **not** authorize starting
  new v1.9 Logic Scope implementation before v1.8 is accepted.

## Evidence and change-control rules

1. `SOURCE IMPLEMENTED`, `CI PASS`, `PHYSICAL DEVICE PASS`
   and `NOT TESTED / BLOCKED` are separate status levels.
2. Work on DEV/Draft PR, commit each small change, review CI,
   perform one safe real-device test at a time.
3. No feature removal, reassignment to another version, deviation
   from the original `ROADMAP.md` or relaxed release gate
   without an **explicit additional operator decision**.
4. Historical tests and SHA-256 checksums are immutable evidence.
   New changes do not inherit previous physical acceptance
   automatically. Avoid destructive testing on original data.
5. Keep this addendum and `ROADMAP.md` side by side. If status
   wording becomes stale, record dated evidence in the physical
   acceptance log without modifying the original feature goals.
