# LabMate — two-roadmap reconciliation and v1.9 pre-start audit

**Audit date:** 2026-10-17
**Decision level:** source/release/read-only evidence reviewed; this is NOT new hardware testing, firmware flashing, a v1.9 feature implementation, or an assertion that all native services are fully secured.

## Source of truth and precedence

1. [Canonical product roadmap](../ROADMAP.md): v1.5 Data Logger, v1.6 Refactor, v1.7 PWM Studio & Counter, v1.8 Communications, **v1.9 Logic Scope & Signal Compare**, **v2.0 LabMate Ultimate / Signal Doctor**. It defines **WHAT must ship and in what order**.
2. [Master Roadmap V2 quality addendum](MASTER_ROADMAP_V2_ADDENDUM.md): firmware/Momentum ABI safety, recovery, cooperative ownership, confidence boundaries, test evidence, maintainability and optional free/premium architecture study. It defines **HOW to validate** and explicitly **does not replace** v1.9 or v2.0 functionality. When the two conflict, canonical feature and release goals win unless the operator explicitly approves a change.
3. [E11 functional / release evidence](V1_8_E11_FINAL_RELEASE_GATE_2026-10-17.md) on E11 development branch, [deferred hardware backlog](DEFERRED_HARDWARE_TESTS.md), [v1.9/v2.0 engineering handoff](https://github.com/sehmusadsoy-ui/flipper-labmate/blob/dev/v1.9-logic-scope/docs/V1_9_V2_0_ENGINEERING_HANDOFF_2026-10-17.md). The latter two development documents are not yet merged to ordinary `main`.

## What is actually completed

| Original milestone | Accepted published result | Specific outstanding caveat |
| --- | --- | --- |
| v1.0–v1.4 basics and measurement | Historical GitHub releases preserved; normal device functional checks recorded | Historical SDK/API matching needed; not a guarantee of arbitrary firmware or professional calibration |
| v1.5 CSV Data Logger | Published; new/fresh CSV, history and persistence also operator-tested on exact E11 FAP | Deliberate full/corrupt SD and Excel on actual Microsoft Excel not verified |
| v1.6 / v1.6.1 modularity, Profiles and local ownership | Published Stable versions, guarded Profile CRC A/B, combined firmware/native E11 experiments; routine persistence PASS | **Global firmware-wide native service cooperation and live foreign-client lease contention not fully verified/implemented across every service** |
| v1.7 PWM Studio, genuine Counter, Button Analyzer and Alerts | Published and functional E11 100 Hz/1 kHz loopback and STOP/RESTART PASS | Real button bounce, electrically independent duty accuracy and OFF voltage still deferred |
| Ordinary v1.8 Stable UART / Counter RESUME | Published 2026-10-14, remains GitHub Latest; source and FAP SHA256 pinned | Its original I2C/1-Wire scope was explicitly reduced; do NOT claim these available in normal v1.8 |
| Expanded v1.8 E11 Custom Momentum | Public compatibility-limited [pre-release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum), exact 81,528-byte FAP SHA256 `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`. Matched-device UI/UART, PWM/STOP, scratch Logger/Profile routine acceptance PASS at operator-report scope | Depends on **patched matched Momentum native ABI**, not compatible as a standalone stock-Momentum FAP; exact custom firmware rollback/upgrade route not demonstrated; unmerged [Draft PR #13](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/13) |

**Legacy issue:** independent `v1.1` release/tag does not exist (historical development milestone). Do not recreate or fake a v1.1 tag for symmetry.

## Remaining work, separated by whether it blocks safe v1.9 implementation

### A. Pre-code engineering blockers — do these *before or alongside the first capture-engine implementation*

| Priority | Open work and evidence gate | Why it matters |
| --- | --- | --- |
| **P0** | Freeze a clean v1.9 baseline: identify which `src/` files, `application.fam`, patched firmware/native dependencies and supported CI tests actually produced the owner-tested E11 binary. Keep exact SHA and historic FAP tags. | An E11 prerelease binary exists, but its complete native-dependent development PR #13 remains a very large Draft, not `main`. Don't merge 387 review files blindly. |
| **P0** | Produce a practical one-page **capture resource matrix** with inputs, EXTI lines, TIM1/TIM2, DMA/DMAMUX, UART, I2C and foreign Momentum owners; decide one first safe capture pin and expected BUSY behavior. | Logic Scope would otherwise repeat past source/IRQ ownership conflicts. A local app lock does not guarantee firmware-wide ownership. |
| **P0** | Precisely scope and test **STOP/BACK/RESTART**, refused START without foreign register/callback writes, bounded ISR ring buffer, wraparound, loss indicators and 128×64 redraw budget *before adding UI bells and whistles*. | v1.9 is a digital measurement instrument, not demo waveform animation; its signal cannot be fabricated. |
| **P0** | Preserve existing S1/S2/S3 profile binary formats and historical CSV records with a scratch-only baseline; mark compatible future schema changes and never rewrite production records. | Existing user data safety must survive v1.9 code work. No reason to demand additional historical CSV/Profile device tests until shared storage code actually changes. |
| **P1** | Separate permanent source/runtime/native tests from historically narrow CI experiment files. PR #13 is **387 files and 1256 commits** by GitHub metadata as of audit; keep evidence under archive/reference, do not delete blindly. | Reviewable integration and professional repo layout, without losing scientific evidence or changing released assets. |
| **P1** | Prepare firmware/SD backup **recovery classification** (tested FAP-only recovery versus full custom firmware restore) and a safe bounded smoke procedure for later v1.9 installation. | No exact byte-identical prior custom firmware restore is currently demonstrated. A release warning is not the same as recovery PASS. |

**Pre-code decision:** Hardware purchase and university oscilloscope visit do **not** need to stop software-only v1.9 design, native resource audit or host-based ring-buffer tests. But no **new firmware flash** or **device-dependent signal accuracy claim** follows from host PASS. Before requesting a new installed FAP, verify the actual matched Momentum ABI, user backups, recovery strategy and separately approved install scope.

### B. Deferred equipment-based validation — do once hardware or university laboratory is available

| Backlog | Fixture / check | Status |
| --- | --- | --- |
| HW-01 | Real 3.3 V dry-contact button bouncing and selectable debounce | NOT TESTED |
| HW-02 | **University oscilloscope with instructor**, independent PA7 output frequency/duty, 5/50/95% duty samples, PWM STOP/EXIT OFF/DC and reference generator vs Flipper readings | NOT TESTED; **no personal oscilloscope purchase** |
| HW-03 / 05 | Independent spare microSD error/media trials, duration and re-open integrity | NOT TESTED; production logs and S1 preserved |
| HW-04 | Independent 3.3 V source, alternate supported Pulse pins and boundary frequencies | NOT TESTED across full range |
| HW-06 | Real **BME280** 3.3 V PC0 SCL / PC1 SDA I2C3 ACK, correct 7-bit address, STOP/re-entry | No positive peripheral ACK yet |
| HW-07 | Real externally VDD-powered **DS18B20** on PA4 with appropriate 3.3 V data pull-up, CRC/temperature/conversion and STOP | No real positive sensor result yet |
| HW-08 | Native global client contention (JS GPIO/PWM/PulseReader/IRQ/timers), real refusal before register modifications | Unverified firmware integration, not simply a missing purchase |
| HW-09–19 | Additional native RFID, CC1101/Sub-GHz, iButton, NFC, Wiegand, ISO15693, IMU, serial owners | Specific test fixtures and compatible native-code work; **not required to buy all before v1.9 starts**, but never mark full firmware-global integration PASS |
| QA-01 | Excel opening existing CSV format in Microsoft Excel | NOT TESTED; LibreOffice Calc import previously PASS |

**Owner equipment plan (2026-10-17):** purchase the small Robotistan bench kit; **exclude personal oscilloscope** and do independent scope measurements at the former university with an instructor. Plan only; not a claim that university measurement/stock purchase is already completed.

## Version-specific promises going forward

### v1.9 — mandatory functionality, no substitution

- Digital edge-capture **Logic Scope** with bounded buffers, real sampled HIGH/LOW timeline, explicit triggers, overflow/drop/timeout and honest signal-validity states; UI tailored to Flipper's RAM/CPU/128×64 display.
- **Signal Compare**: real measurements vs named presets/tolerances; PASS/FAIL/NO SIGNAL/INVALID rooted in observed data, never idealized metrics.
- Physical tests with independent 3.3 V reference, capture STOP/BACK and foreign resource-owner BUSY; retention of UART/PWM/Counter/Button/Logger/Profile without data loss.
- Correct firmware channel: initially **matched E11-custom Momentum**; only claim ordinary Momentum Stable when exact ABI and device acceptance independently prove ordinary compatibility.
- Publish v1.9 only with pinned source/FAP, independent evidence and explicitly scoped release; do not label a draft/CI-only v1.9 as Stable.

### v2.0 — mandatory outcome, no early Premium substitution

- **Signal Doctor** rule-based explanations (missing clock, stuck high/low, jitter/dropouts) grounded in measured data with uncertainty and user guidance, not claims of board-level diagnosis without evidence.
- Unified measurement dashboard and instrument workflow, useful advanced real stats, CSV / profile backward compatibility, fast readable UI.
- Full quality/regression/long-run acceptance before release.
- Optional free/Premium structure is **research only** until explicit later product decision; it may not replace the Signal Doctor, dashboard or other original v2.0 requirements.

## Immediate safe next action

1. **Finish the repository presentation work and link both roadmaps on `main` without source/binary edits**.
2. Review native-resource/capture contracts in a small v1.9 Draft branch, not PR #13 mega-merge.
3. Prepare host tests for bounded digital timestamp buffer and acceptable resource refusal; device modifications only with later explicit approval.
4. Record physical fixture results as they arrive, with instructor-led independent scope and separate user data backup.

**Audit conclusion:** ordinary v1.8 and E11 public compatibility-limited releases are correctly preserved. **v1.9 planning can continue immediately; v1.9 implementation must start by resolving P0 source/owner contract questions, not by pretending full E11 native integration is complete.** No overdue milestone has been secretly converted into paid-only functionality.
