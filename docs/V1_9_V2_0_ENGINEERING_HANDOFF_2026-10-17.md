# LabMate v1.9 / v2.0 — engineering handoff and acceptance plan

**Status:** Planning only (no v1.9 implementation, build, FAP publish or device installation).
**2026-10-17 E11 source starting point:** `5ee4a2d6eeb28ca0c3c4e0c45d327f7e459fda77` on `dev/v1.8-completion`, already owner-tested final-label FAP source frozen at `99cb65d0194dc59d423cfa439c90618ac6b9f114`. The new `dev/v1.9-logic-scope` branch was created from E11's review head. E11's 387-file Draft PR #13 remains **unmerged** to `main`.
**Maintenance baseline:** original normal Momentum `v1.8` Stable and public E11 **Custom Momentum** prerelease remain separate, immutable, user-installable historical references. Latest ordinary GitHub Stable must stay original `v1.8` until a separately accepted future release.

## Strategy and source continuity

- Continue **on Momentum** as requested, initially the actually tested **patched E11 custom Momentum ABI**. Do not claim stock, official or arbitrary custom firmware support for the E11-derived v1.9 code; later conversion to ordinary Momentum requires independent SDK and native-ABI compatibility validation.
- Single LabMate app/FAP with menus `MEASURE → OUTPUT → RECORDS → COMM → INFO`, INFO/About always last; no demo FAP, no `v1.8.1` detour or gratuitous version fragmentation.
- Keep release **version-specific**: normal Stable only when its exact target compatibility and FAP are verified; compatibility-limited prerelease when native custom firmware is required. A prerelease is not inherently inferior to a Stable on its proven hardware, but doesn't make arbitrary-device install safe.
- Preserve Profiles (including S1), CRC A/B file format, historical CSV logs and monotonic Logger filenames. New record formats must be backward compatible or versioned; never silently reset/migrate/delete user data.
- Do not merge the full E11 Draft PR #13 blindly into `main`. Extract coherent source + native dependency + long-term regression tests into staged reviewable changes, keeping historic reviewer/test evidence reachable. No mass delete/rebase/force push that destroys provenance.

## v1.9 — digital Logic Scope and Signal Compare (accepted objective)

**Digital-only** logic-scope display, not analog oscilloscope or RF/precision-certified instrument.

### Phase 0 — verify baseline before coding

1. Re-check source/native ABI pin ownership and the same `v1.8`-labeled exact final FAP evidence. Do not extrapolate from old Stage C host tests.
2. Determine user-facing capture pins and whether safe two-channel concurrency is actually supported; until demonstrated, start with **one confirmed GPIO channel** and explicitly decline unsupported modes.
3. Plan resource owner leases for EXTI/TIM/DMA, including native JS, PWM PA7, Counter PB3/TIM2 and UART/I2C conflicts; START must refuse an occupied resource **before changing its configuration**. STOP/BACK must relinquish all owned resources only.
4. Complete the bench P0 fixtures in `docs/DEFERRED_HARDWARE_TESTS.md`: known-safe 3.3 V independent pulse source, 8-channel logic analyzer, timebase-capable scope, known-good SD backup, dry contact, real 3.3 V I2C peripheral and real externally powered DS18B20. Don't invent physical PASS for untested cases.

### Phase 1 — bounded capture engine

- One GPIO digital edge timestamp sample path. ISR/callback O(1), **no heap allocations, file I/O, UI calls or blocking locks in interrupt context**. Use an initially fixed-capacity capture buffer (design starting point 256–512 edges, tuned only after real measured SRAM/latency).
- Explicit `ARMED / RUN / HOLD / STOP / ERR / BUSY`; buffer-full indication, dropped edge count, timestamp wrap handling, timeout, zero-signal behavior and clean START after STOP.
- Trigger mode: rising, falling and optional level subject to real hardware proof. Capture pre/post-trigger only if supported by bounded storage, measurable worst-case latency and correct resource release.
- UI: digital HIGH/LOW timeline and measured period/high/low/duty without fabricating missing edges; no misleading analog magnitude. Keep screen refresh and capture separate, minimize rendering cadence on 128×64 Flipper.
- Independent signal reference (e.g. existing ESP32-S2 or 3.3 V RP2040 Pico) and external 8-channel logic analyzer for low/high frequency, startup/shutdown, overload and IRQ-resource conflicts.

### Phase 2 — Signal Compare

- Compare real acquired measurements to explicitly named reference presets with user-set absolute/percentage tolerances for frequency, duty, pulse width and missing events.
- Explain `PASS / OUT_OF_TOLERANCE / NO_SIGNAL / INVALID / BUSY` based on actual measured fields, never assume ideal waveform.
- Profile save/restore only through guarded non-destructive existing codec or a clearly versioned extension with CRC; back up files before any on-device write.
- Export additional CSV only with backward-compatible headers/new filenames, not silent overwrite of existing Logger logs.

### v1.9 acceptance gates

- Host SDK compile and bounded capture/wrap/overflow/timeout test matrix, native-source resource lease validation, static no-IRQ-blocking checks, FAP SHA256/provenance; CI proof must be actually visible, not just authored.
- Physical 3.3 V external source vs independently observed logic analyzer/oscilloscope for representative frequencies, duty, trigger and changing edges; STOP cuts capture/ownership, re-entry works, BUSY refusal protects foreign owner.
- Logger/Profile old+new persistence and full STOP/BACK/navigation regression with user data backed up; deliberate corrupt/full SD tests only on **spare** media with clear approval.
- Exact matched firmware compatibility + recovery classification documented. A build PASS or publication never substitutes for rollback rehearsal on a specific device.
- Create a **separately versioned v1.9 release** only after owner review, test evidence and scoped distribution decisions. `v1.9` is NOT released by this plan.

## v2.0 — LabMate Ultimate / Signal Doctor (not started)

- Build **on verified v1.9 measurements**: rule-based Signal Doctor (missing clock, stuck LOW/HIGH, unstable duty, dropouts) with explicit measurement confidence and explanations; do **not** certify board faults from Flipper loopback alone.
- Unified dashboard, convenient history/trend review, scenario-driven troubleshooting, CSV export and preserved profiles; every rule has synthetic positive/negative/unknown fixture and real-device proof.
- Strong limits: memory/CPU/energy, no hidden active output, safe GPIO 3.3 V constraints, ownership conflict policies, no automatic flash, clear compatibility labels.
- v2.0 final gate: prolonged real-device use, measured external truth source, documentation and release artifacts, honest unverified-scope list, no installation without explicit compatibility/backup guidance.

## Physical test equipment purchase priority

1. **P0 immediately useful:** 3.3 V I2C BME280 peripheral; externally VDD-powered 3.3 V DS18B20 breakout with 4.7 kΩ data pull-up (unless module already has one); dry-contact button; breadboard and all three 2.54mm Dupont jumper types; independent 8-channel USB logic analyzer; trusted multimeter; **independent digital oscilloscope** 2-channel preferred for PWM period and output OFF.
2. **P0 storage:** disposable **spare** microSD exclusively for missing/full/corrupt-storage trials. Never corrupt/remove the production card. The PC-only original backup must remain untouched.
3. **P1 independent stimulus:** existing known-good 3.3 V ESP32-S2 if no interference with past ST2 test fixture, or spare 3.3 V Raspberry Pi Pico; verified 125 kHz RFID card and 13.56 MHz NFC card for basic native owner tests. Do not confuse ISO14443A with ISO15693.
4. **P2 special fixtures, buy after compatibility confirmation:** exact ICM42688P SPI + accessible IRQ board, genuine DS1990A iButton + matching reader probe, **explicit ISO15693-tag type**, confirmed 3.3 V CC1101 radio board and legal test setup, validated Wiegand emulator. An arbitrary cheap RFID reader or mismatched IMU cannot close these tasks.
5. RF/firmware-global/native internal interrupt coexistence needs verified native test code and safe pin-level setup; **shopping alone cannot guarantee hardware gate closure**. Hardware test backlog entries HW-01…HW-19 and Excel QA-01 remain independently tracked.

## Commit/release safety invariants

- No force pushes, retagging, deleting old releases, replacing `v1.4`/`v1.8` assets, risky trial firmware flash, overwriting S1, or deleting existing CSV.
- Source changes must be isolated to the development branch; no `main` changes merely to make CI green.
- Evidence classification: **VERIFIED** exact live readback vs **OPERATOR PASS** vs **HOST/CI PASS** vs **DEFERRED/UNKNOWN**.
- New 1.9 work starts with a small reviewable capture-engine task, not with every planned feature committed at once. Existing E11 functions are regression baseline, not a reason to repeat every physical test unless binaries or shared contracts change.
