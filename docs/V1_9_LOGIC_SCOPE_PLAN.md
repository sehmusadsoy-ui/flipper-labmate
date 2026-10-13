# LabMate v1.9 — Logic Scope + Signal Compare (early R&D)

**Status (2026-10-14): L0 strict C11 host tests, scope HAL-isolation guard, Momentum development FAP SDK build and Windows installer mock all CI PASS. L1 display projection is the next gate; real GPIO capture is still NOT IMPLEMENTED.**
This is a preliminary v1.9 **development-only branch**, not a
v1.9 release, not a device-tested oscilloscope, and not authorization
to skip an unfinished v1.8 milestone.

Branch: `dev/v1.9-logic-scope-core` — **branched from `main`**,
which contains accepted development UART. We deliberately **do not
merge** blocked [I²C PR #8](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/8)
or optional [1-Wire PR #9](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/9).
The published v1.7 Stable tag/assets are unchanged. v1.8 has
no published Stable release; its UART work and outstanding hardware
risk decisions must remain intact.

## Why this feature is useful

A compact **digital** single-channel scope can retain actual
HIGH/LOW state transitions and their measured timestamps rather
than guessing a waveform from an average frequency. Signal Compare
can later compare a captured trace or measured pulse statistics with
a user-selected reference range. Both need honest bounds, safety,
explicit missing-data status and readable 128×64 rendering. This
is **not analog acquisition**, calibrated timing, or proof of
multi-channel/high-frequency sampling.

## L0 — HAL-free edge trace, 128 events

Sources:
`src/labmate_scope_trace.h/.c`. Host tests:
`tests/test_scope_trace.c.inc`. Static guard:
`scripts/check_v19_scope_isolation.py`.

The model accepts single-owner, **serially delivered** binary
samples with a 32-bit timestamp of **unknown caller tick rate**.
It holds **128 event entries maximum** and each entry is at
most 8 bytes (at most **1024 bytes for event storage**),
with small additional metadata. No dynamic allocation, GPIO
setup, callback subscription, radio/power interaction,
thread scheduling, Canvas drawing or microSD writes are involved.
Pure code is compiled by the normal `src/*.c` FAP wildcard,
but **no runtime code invokes it**. No user-visible Scope menu exists.

- Explicit trigger modes: **immediate, rising, falling, either edge**.
  Non-triggering edges are discarded while ARMED. On an edge
  trigger the trace begins with the observed **post-edge** level
  at offset zero; it does **not invent pre-trigger data**.
  An immediate capture records the initial observed level at zero.
- Only **actual observed binary level changes** produce new
  timestamped events. No reconstructed/guessed pulses. Consecutive
  unchanged samples do not consume the 128-entry event budget.
  Raw timestamps are **caller ticks**, not microseconds/Hz until
  a separately validated clock source and conversion are attached.
- Timestamp subtraction is modular unsigned 32-bit. Genuine
  one-wrap forward passage can be accepted if every consecutive
  gap and the accumulated arm/record span remain within
  `2^31-1` ticks. Same-tick opposite levels, longer/ambiguous gaps,
  implausible total span and invalid levels cause an **explicit FAULT**
  and freeze the retained trace. No evidence exists of device
  timebase precision or detection of unobserved transitions.
- Events 1–128 are preserved. On the **next observed transition**
  the state becomes **OVERFLOW**, preexisting events are
  never overwritten and `missed_lower_bound=1` means **at
  least one omitted transition**, not an exact dropped count.
  No claim is made for edges arriving after the model freezes.
  STOP during ARMED/RECORDING preserves all events and whether
  a trigger occurred. STOP does not disguise OVERFLOW or FAULT
  as a clean completion.
- Every run has a monotonic generation token to reject old
  input callbacks after restart. Saturated generation rejects
  restart rather than wrapping and risking token reuse.
  This is a **logical model only**: it is not thread-safe,
  and neither a STOP nor a completion proves GPIO/EXTI/timer
  or worker resources have been released on a Flipper.
- **Precaution:** a future real producer must serialize events
  with the model, avoid unbounded ISR work, supply an independently
  characterized timer and ensure full pin/timer/EXTI exclusivity.
  A 128-sample buffer alone does not guarantee throughput or
  finite ISR latency. The actual physical sample rate is unknown.

### Test matrix

| Gate | Evidence required | Present status |
| --- | --- | --- |
| L0a | Native strict C11: initial level, trigger modes, filtered edges, stale token, START/STOP | **CI PASS** run 38473341973; exact source 1febeaf6 |
| L0b | Native strict C11: wrap, clock faults, >half-range span, no overwrite, overflow, token exhaustion | **CI PASS** run 38473341973; exact source 1febeaf6 |
| L0c | Static guard: no HAL, GPIO, UI/menu, or runtime calls; SDK development FAP builds alongside older features | **CI PASS** run 38473341973; SDK build and Windows mock installer passed |
| L1 | Pure 128×64 pixel/column projection with honest unresolved-edge density flags | NOT STARTED |
| L2 | Real capture driver plan: mutually exclusive PC0/PC1/PB3/PA7, bounded ISR/timebase and STOP/BACK | NOT STARTED — safety gate |
| L3 | Real Flipper no-signal and known-safe 3.3-V loopback; clean STOP/BACK and regressions | NOT TESTED |
| L4 | Signal Compare: reference/tolerance pure math and defensible error/missing-signal messaging | NOT STARTED |
| L5 | Performance/risk acceptance, scope/compare app integration, version release planning | NOT STARTED |

### L0 exact CI acceptance evidence

- [GitHub Actions run 38473341973](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38473341973), tested source SHA `1febeaf67f366e1a60310202f942348ad3d5cd1c`.
- Job `115557763010` **SUCCESS**; logs explicitly say
  `v1.9 scope HOST: 128-event cap, triggers, stale tokens, wrap, clock faults, overflow PASS` and
  `v1.9 Scope trace: HAL-free, bounded and NOT connected to physical GPIO/menu PASS`.
  Momentum SDK development FAP linked and checksum check reported `labmate.fap: OK`;
  file SHA256 `f3ce6438280524692908212c0b3c8b4c9a830b7afc467b503aab667d2e7f12d2`.
  Artifact `labmate` ID `11852083054` is a **development-only** FAP; this is not a v1.9 release or on-device run.
- Windows installer mock job `115557763256` **SUCCESS** without touching USB.
  v1.7 release finalization job `115557896247` **SKIPPED** as intended.
- These PASS results cover only the HAL-free model and build. Physical signal capture, hardware timebase, accuracy, peak edge rate and STOP/BACK on Flipper remain untested.

### Current limitations

This model does **not** determine the input pin, measure analog
voltages, change pull-ups, sample from interrupt handlers, calibrate
timestamps, show a live waveform, set a hardware trigger, or read
from an actual external signal. All synthetic test waveforms
are *models*, not a physical Flipper capture. Host CI does not
replace device validation. Do not label v1.9 release-ready
until its separate hardware and regression gates PASS.

### Release/project discipline

Work starts from current development `main` solely for offline
feasibility. **No early v1.9 UI or version label is enabled**.
Existing UART terminal, PWM Studio, Counter, Profile data, CSV History,
Stable v1.7, Draft I²C PR #8 and Draft 1-Wire PR #9 must remain
untouched. Later, before any merge, reconcile this branch against
the actual accepted v1.8 baseline instead of overwriting ongoing
communication-tools development.

Only **known 3.3 V-compatible digital inputs** could be candidates
for future hardware capture; no unknown-level electrical source,
5-V line, powered peripheral or wiring instruction is part of L0.
