# E11 Button + Scope / Compare + Sample A/B — pre-device acceptance

**Development source**: exact commit under `dev/v2.0-e11-compare-sample-pixel-step4-20261028`.
**Workflow**: `.github/workflows/v20-e11-final-ui-predevice.yml`.
**Boundary**: no firmware flashing, FAP download/copy, SD cleanup, branch merge, or Stable write.

## Approved source-stage implementation

1. Step 1 — shared pixel UI kit: Waiting / Match / Off badges, measured
   one-line header, units, digital trace and Scope four-dot paging.
2. Step 2 — Button: Ready, Live, Stopped, Busy, Error; stable Open/Closed
   and pending Settling; completed-only Bounce/Settle/Hold/Bounces.
3. Step 3 — Scope/Reference: real PC1 wave from validated edge history,
   active/live and completed/held distinctions, no stale frequency;
   reference target/decision evaluated only against accepted metrics.
4. Step 4 — Compare/Sample A/B: sequential, independently saved PC1
   captures. B requires newer generation than A. Signed B-A frequency
   differences are **absolute** Hz/kHz, not percentage. Sample storage has
   no raw waveform, so filled Sample screens show real metrics instead
   of fictional oscillograms.

## Gates and evidence

| Gate | Status |
|---|---|
| Step 1 primitive GCC + Clang / native API 87.1 | PASS in prior reviews |
| Step 2 Button (4096 state cases per compiler) | PASS in prior reviews |
| Step 3 Scope/Reference data + bounds | PASS in prior reviews |
| Step 4 Compare/Sample pairs and guards | PASS, Actions 40766889387 |
| Pinned Momentum E11 SDK API 87.1 FAP / SDKCHK / APPCHK | PASS, Actions 40766889352 |
| Consolidated current UI/capture + Phase 2B..2K + evidence suites | **PASS**, Actions 40773486845 (GCC+Clang) |
| Original pair generation/save + persisted navigation IDs (GCC + Clang) | **PASS**, Actions 40773486845 |
| Physical full 128×64 screenshots, resource conflicts, SD, PC1 edges | **OPEN** |
| UI02 / UI03 COMM exact current renderer tests | PASS on migration branch |
| UI05B Button / Alerts exact current renderer tests | PASS on migration branch |
| UI06C pure status plus exact GPIO | PASS (retained compatible gate) |
| UI04 Profiles / History / Log Detail exact production render (300 cases per compiler) | **PASS**, Actions 40771017169 (GCC+Clang) |
| UI05 Logger exact production render (240 cases per compiler) | **PASS**, Actions 40771605748 (GCC+Clang) |
| UI05D Frequency/Pulse/PWM current render (4,704 cases per compiler) | **PASS**, Actions 40773486845 (GCC+Clang) |
| UI06 quiet pair/triple footer (11+5 valid, 10 rejected per compiler) | **PASS**, Actions 40773486845 (GCC+Clang) |
| Remaining unmigrated historical UI runners | **None**; physical acceptance still **OPEN** |

### Follow-up physical acceptance (single labmate.fap only)

Keep the user's current approved FAP untouched until a consolidated trial is
intentionally requested. Do **not** multiply Trial/Final/Step FAP copies.
A source commit and successful CI compile do **not** install on Flipper.

On device, check Ready/Live/Stopped/Busy/Error, Button stable/pending
states, input DOWN/OK/UP semantics, Scope real PC1 transitions and HOLD
conditions, Reference No signal/Busy/Match/Off, Sample A save, newer B
capture+save, real B-A difference, and four-page traversal. Test electrical
inputs only within validated 3.3V limits and common ground.

Do not promote to Stable without on-device acceptance and non-regression
for firmware E11 API 87.1 plus compatibility/legacy UI fixture disposition.


## Legacy harness triage (E11; branch-only, no production diff)

The old CI runner inventory was audited rather than counted from memory:
11 historical `test-v20-ui*-host.sh` runners; three already covered by
pre-device CI (UI01, UI05C Counter, UI05E GPIO). Eight were excluded.

An isolated diagnostic run showed **seven old failures, one pass (UI06C)**:
https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40768877702

Current-source replacements now include:
- **UI02/UI03:** exact production I2C, 1-Wire, UART pixel renderers (24+56+32
  scenarios per compiler), using controlled host I/O snapshot types only.
- **UI05B:** existing Step2 exact Button renderer (4096 combinations per
  compiler), plus exact-source Alerts (72 source/limit/status cases).
- **UI06C:** original status truth table remains passing and runs the current
  exact GPIO source renderer through UI05E.

**UI04 migrated:** exact current Profiles / History / Log Detail bodies, with
216 + 44 + 40 read-only state cases under each of GCC and Clang. Combined
pre-device CI **PASS**, Actions 40771017169; no device or FAP work.

**UI05 migrated to CI gate:** current Logger exact renderer (3 sources × 2 validity
states × 10 busy/error/recording/save states × 4 scale boundaries = 240 cases per
compiler), testing header/status precedence, mode, measurements, key hints,
bounds, and zero app-state mutation. The combined GCC+Clang pre-device CI
**PASS** is recorded in Actions run 40771605748. This does not certify SD
writes or real Flipper pixels.

**UI05D migrated:** exact current Frequency/Pulse/PWM drawing functions plus
source-linked UI Kit text, header, pulse line and sparkline primitives. 288
Frequency + 384 PWM + 4,032 Pulse fixtures per compiler; GCC/Clang **PASS**,
Actions 40773486845. Secondary-font host geometry is approximate, not a
physical Flipper font-raster certification.

**UI06 migrated:** original quiet pair/triple footer functions source-linked,
with 11 pair cases, 5 triple cases, and 10 invalid-input rejection cases per
compiler, plus the original layout constants test. GCC/Clang **PASS**,
Actions 40773486845. The obsolete `ui_footer_info` fixture and the old
inverse footer-band assumption are not the current implementation.

**All eight initially excluded legacy runner names have current-source
dispositions** (UI06C retained; seven migrated). The complete combined gate
reports 8 UI/safety + 10 core + 5 evidence suites passing. These source-side
results **do not** establish real device pixel raster, 3.3 V PC1 signal
handling, SD writes, resource contention, or physical firmware E11 behavior.
Never treat CI PASS as authority to overwrite the approved FAP or Stable.
