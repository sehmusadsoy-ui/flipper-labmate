# v1.9 Logic Scope — UI redesign after real Flipper screenshots

**Status:** Development; not Stable, and not yet built/installed for physical review.

## Why earlier UI was rejected

The operator showed the real 99,376-byte installed v1.9 UI on 2026-10-20.
The grid markers visually intersected the measured square wave; oversized
all-caps text walls dominated A/B and Reference screens; footer commands
were densely concatenated; Reference repeated WAIT/INVALID and NO VALID
CAPTURE; UP navigation exposed blank A/B detail pages before captures existed.

The square-wave capture itself worked; this was a usability failure.

## New graphical contract: Flipper Zero 128x64

**Scope, page 1:** bold SCOPE heading, PC1, page position; a fine rectangular
wave viewport x2..125/y15..42. Six small vertical border ticks and seven
isolated single-pixel midline dots provide a light oscilloscope graticule.
The measured HIGH/LOW trace is painted last. Guide marks are *not calibrated
time or voltage divisions*. Only real observed PC1 edges may generate
waveform segments: no invented samples before/after captured edges. A single
short primary-font READY/LISTENING/NO SIGNAL/etc message appears if empty,
never repeated in the status row. Status shows actual edge count and capture
state, with ZOOM only for cropped last-edge viewport. Three separated footer
zones: OK RUN / OK STOP, v PAGE / ACTIVE, BACK. Page rotation is disabled
during capture.

**Sequential compare, page 2:** bold COMPARE, PC1, page position. Two quiet
empty capture slots (A -- and B --) replace the former wall of instructions.
Saved A/B rows align real frequency and duty values, followed by two rows
showing F change and D change, specifically B minus A. A and B are *different,
sequential captures of one PC1*, never simultaneous channels. UP moves summary
to A timing to B timing; missing A or B pages are skipped. Timing detail
readouts show actual average HIGH, LOW, PERIOD and duty from complete cycles,
in us/ms without floating-point math. If a stored prefix is truncated it is
marked A* or B*. A/B changes do not touch IRQ, capture history or SD files.

**Reference, page 3:** one table with four aligned rows: TARGET, FREQ, DUTY,
RESULT. Outcomes are PASS, FAIL (out of the preset's tolerance), NO SIGNAL,
BUSY, NOT READY. Full mHz and permille values are re-evaluated before a PASS
can be drawn, preventing stale or rounded false PASS. Footer UP toggles
100Hz/50% vs 1kHz/50%, DOWN pages, BACK exits.

Fonts: use bold Primary for short headlines only, Secondary for aligned
measurements and key labels. 128px width and all 64px height must remain
collision-free for empty, live, completed, malformed, large and partial
capture states. All validation runs before first visible render.

## Validation requirements

1. Host GCC C tests with -std=c11 -Wall -Wextra -Werror -pedantic:
   Scope display geometry and text rectangle nonoverlap, A/B formatting
   and missing data, Reference stale-pass rejection and display bounds,
   focused real-edge plot unchanged.
2. Native Windows E11 SDK: new FAP-only build after preserving the
   previous 99,376-byte installed candidate on PC with pinned SHA256
   0f0b246d042c45eabe2c29dab692dbc7df20817c419c011ca31a313d4b62141a.
   Build stage does not connect to device, flash firmware, or update data.
3. Operator physical UI screenshots must be reviewed before measuring
   PA7->PC1 at 100Hz/50% and 1kHz/50%. STOP/BACK, A/B/Reference and
   existing tools must remain safe; PR #15 stays draft pending approval.

Flipper is 128x64 monochrome. This is a single-channel 3.3V digital
edge viewer, not a calibrated analog oscilloscope. Grid divisions are
visual guides, not assertions of known millisecond/voltage scale.

The older installed 99,376-byte FAP remains untouched by GitHub code edits.
