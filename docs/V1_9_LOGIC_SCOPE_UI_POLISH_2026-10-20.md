# LabMate v1.9 Logic Scope — professional 128×64 UI polish

**Status:** Development source; not a Stable release. Presentation + read-only page selection only. No firmware flash, no device write, no trigger or HAL lease changes.

## Screen geometry

| Region | Pixels | Purpose |
|---|---|---|
| Header | y 0–13 | LOGIC SCOPE / PC1, A/B COMPARE, REFERENCE |
| Scope viewport | x 1–126, y 15–40 | Border and sparse dashed division markers; observed trace at y 20/35 |
| Status | baseline y 50 | Real edge count, LIVE/HOLD/NO TRIG; ZOOM only when cropped |
| Footer | baseline y 62 | Only applicable controls, at most 20 secondary-font glyphs |
| Compare / reference | baselines y 23, 32/34, 42/43, 51 | Four independent, legible information lines |

Grid divisions are visual guides, NOT calibrated voltage/time divisions. Waveform projection uses **up to 13 latest actually captured edges**, so it must never fabricate a pre-trigger trace, a transition after the last edge, or a full-window measurement. Full 256-edge capture is retained for A/B and reference metrics. No waveform in BUSY/UNSUPPORTED/ERROR or before 2 real edges. No data/audio/storage/rendering from the ISR.

## Controls

| Page/state | Key | Actual action |
|---|---|---|
| Scope idle | OK | Start PC1 IRQ capture |
| Scope active | OK | Safe STOP |
| Scope idle | DOWN | Plot → A/B summary → Reference → Plot |
| A/B idle | UP | Summary (A,B, B−A) → A timing → B timing → Summary |
| Scope or A/B idle | LEFT / RIGHT | Store complete sequential A / newer-generation B |
| Reference idle | UP | 100 Hz/50% ↔ 1 kHz/50% reference |
| Any Scope page | BACK | Safely STOP/release IRQ+lease before exit |
| Scope active | UP / DOWN | Disabled until STOP |

Footer labels:
- Idle plot: OK:RUN DN:PG BK:EXIT
- Active plot: OK:STOP BK:EXIT
- A/B summary: UP:MORE DN:PG BK:OUT
- A/B timings: UP:NEXT DN:PG BK:OUT
- Reference: UP:REF DN:PG BK:EXIT

A/B snapshots are sequential acquisitions on the SAME PC1 input, not dual simultaneous channels. Summary gives real frequency, duty, frequency B−A and duty B−A, with no invented tolerance verdict. Detail views give measured mean HIGH, LOW, PERIOD in µs/ms and duty. Prefix-limited data is marked with an asterisk if present. Dynamic formatting is checked to fit the screen before drawing.

Reference screen separates target, verdict, real observed frequency and duty. The existing full-millihertz tolerance calculator is still checked on each render before rounded LCD labels are shown: changing presets must not reuse a stale PASS. Invalid capture must never display PASS.

## Required checks before trial

Host compiler tests:
- tests/test_labmate_scope_display.c — four-sided box, grid, waveform confinement, 20-glyph footer, invalid input zero paint
- tests/test_labmate_scope_pair_view.c — summary/delta, A/B high-low-period detail, text bounds, invalid pages
- tests/test_scope_reference_view.c — target/result labels, true PASS, no forged/stale PASS
- tests/test_labmate_scope_focus.c — last 13 real events with no interpolation

Build locally using native Windows MSYS2 UCRT64 GCC host tests, followed by fbt.cmd fap_labmate in the isolated already patched E11 SDK based on Momentum d3f89dfe2ef6b01839201598e9be1590cba80322. Back up prior locally built 97,724-byte v1.9 FAP before replacing it on PC. Check exported native API imports and new binary SHA256; DO NOT install or flash during build. Preserve Stable v1.8, prior v1.9 installation and all 12 app data files.

Separate real-device plan after new explicit installation authorization: OPEN idle/no-signal; PA7→PC1 3.3 V 100 Hz/50% and 1 kHz/50% square waves; edge count, zoom, STOP/BACK; A/B snapshots and readable A/B timings (100 Hz: 5 ms high/low; 1 kHz: 500 µs high/low); reference 100 Hz/1 kHz switching; Pulse/Frequency/PWM/Logger/Profile regression; no signal false PASS. Existing firmware binary ABI not independently attested merely by matched E11 SDK build; do not claim global timer/EXTI safety.

GitHub Actions execution is NOT used as evidence: account Actions execution was blocked. Source commit alone is not a device test or Stable release.
