# E11 Button + Scope / Compare + Sample A/B — pre-device acceptance

**Development source**: exact commit under \`dev/v2.0-e11-compare-sample-pixel-step4-20261028\`.
**Workflow**: \`.github/workflows/v20-e11-final-ui-predevice.yml\`.
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
| Consolidated current UI/capture + Phase 2B..2K + evidence suites | See combined workflow |
| Original pair generation/save + persisted navigation IDs (GCC + Clang) | See combined workflow |
| Physical full 128×64 screenshots, resource conflicts, SD, PC1 edges | **OPEN** |
| Nine unconverted pre-pixel isolated UI fixture harnesses | **OPEN**, not waived |

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
