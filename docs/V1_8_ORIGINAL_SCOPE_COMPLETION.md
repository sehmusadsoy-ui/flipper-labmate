# LabMate v1.8 — Original Roadmap Completion (active work)

**Decision:** Operator requested returning to the original 2026-10-08
v1.8 Communication Tools milestone instead of treating its I²C and
feasible 1-Wire tasks as complete, and including the already physically
tested Button Analyzer STOP/RESUME fix in **v1.8**, not a separate
v1.8.1 release. Restore and finish original requirements first;
do not start v1.9 work. Date: 2026-10-14.

**Published history is immutable evidence:** The public original
v1.8 Stable binary/tag remains valid for its explicitly reduced
scope. Do not rewrite its past build or test results. The requested
future *in-place v1.8 update* can replace the downloaded FAP/assets
only after a new exact-source build, checksum check, and device
regression, with old/new artifact SHA and source provenance recorded.
Do not silently retarget the original tag. No binary update yet.

**One single production application:** `appid=labmate`,
`/ext/apps/Tools/labmate.fap`. The current active work branch
`dev/v1.8-completion` uses the visibly non-Stable label
`v1.8DEV` until original release gates are satisfied.
No standalone preview FAP is an acceptable feature substitute.

## Scope versus verification

| Original milestone | Source implementation | Optional later instrument-grade verification |
| --- | --- | --- |
| v1.5 CSV/History | Implemented and tested; actual Excel import outstanding | Actual Microsoft Excel, destructive SD failures |
| v1.6 code/UI/peripheral architecture | App/driver/GUI/SD/input modules and app-local capture owner implemented | Firmware-wide exclusive resource safety across unrelated system services is not yet proven |
| v1.7 PWM/Counter/Button/Alerts | Implemented, physical functional smoke; Button STOP/RESUME improvement integrated in this working branch | Calibrated PWM, mechanical contact bounce, exhaustive 3.3V extremes |
| v1.8 UART | Implemented and external-peer tested | Physical RX DROP and calibrated baud |
| v1.8 I²C Explorer | **UNFINISHED**: closed unmerged research PR #8 has address scan/results/lifecycle models and disabled production UI | Known 3.3V peripheral and actual device detection, timeouts/STOP/exit |
| v1.8 optional 1-Wire | **UNFINISHED**: closed unmerged research PR #9 has CRC/temp decoder and a mock ownership session | Known supported DS18B20 sensor and actual temperature if feasible |

## Menu policy (fixed)

**MEASURE → OUTPUT → RECORDS → INFO (About) → COMM**.
About stays in the second-last root group; COMM is physically below
it as the last root group. Future I²C and possible 1-Wire children
belong under COMM. Preserve the stable tool IDs, profile storage
format and 128×64 scrolling. Portable navigation test asserts the
INFO/COMM positions and titles. Do not move About into COMM.

## Code gates

### B — Button Analyzer

- [x] Bring prior Button STOP → RESUME implementation, host tests
  and lifecycle guard into *current v1.8* development app.
- [x] Existing physical v1.8.1d candidate Button B1–B6
  operator-reported **6/6 PASS**, source in previous draft PR #12.
  This is carry-forward behavior evidence, **not a physical PASS on
  the newly combined v1.8DEV build**.
- [ ] Integrated `v1.8DEV` CI and final full-scope device acceptance.

### M — v1.6 resource and module completion

- [x] The app already has split capture/input/view/storage and
  deterministic internal capture owner, PWM TIM1 and USART lifecycle.
- [ ] Audit every production GPIO/IRQ/TIM/UART path, all STOP/BACK/
  failed-acquire/exit transitions and potential concurrent claims.
- [ ] Extend app-wide resource exclusion policy to I²C PC0/PC1
  and the selected 1-Wire GPIO, with PWM/Counter/Logger/Profiles
  and busy/rollback tests.
- [ ] A firmware-wide lock claim requires a real exported HAL
  owner/lock contract or verified firmware change. App-local flags
  alone never guarantee global ownership.

### I — real I²C Explorer (blocked until viable owner path)

- [x] Preserve old pure scanner/pagination/lifecycle research in
  branch `dev/v1.8-i2c-explorer`, never call simulated hits real.
- [ ] Establish a technically supported, *bounded/cancellable*
  external I²C bus acquisition or formally justified safe ownership
  protocol for the exact installed Momentum firmware/API.
- [ ] Add real read-only hardware address scan using
  `furi_hal_i2c_is_device_ready` with a per-transaction timeout,
  true 7-bit address encoding, actual hit list and coherent status.
- [ ] STOP/BACK and bus release must survive contention/error
  without GUI deadlock or orphaned worker. Host+SDK tests first.
- [ ] Physical known-safe **3.3V** hardware scan (device/no-device)
  and transition regressions later. No fake FAP, fake hit or
  future-unverified global mutex shortcut.

### W — feasible 1-Wire DS18B20 (real driver, not just decoder)

- [x] Preserve previous pure CRC/temperature codec and STOP model in
  `dev/v1.8-onewire-feasibility`.
- [x] New source review: Flipper's official `example_thermo`
  supports alternative external GPIO pins (PC0, PC1, PC3, PB2, PB3,
  PA4, PA6, PA7), not just shared PB14/`gpio_ibutton`.
  Changing to a non-PB14 pin needs an appropriate 3.3V pull-up.
- [ ] Select a non-iButton pin safely excluded from other
  LabMate instruments, and audit background firmware owner paths.
- [ ] Implement real one-wire host reset, read, conversion,
  scratchpad CRC and timeout, no surprise OTG/power enable.
- [ ] Stable sensor UI, BUSY/ERROR/STOP/BACK with actual measurements.
- [ ] Physical safe sensor test is separately pending.
  Optional means a genuine feasibility verdict is allowed,
  *not* declaring decoder-only code a completed sensor reader.

### R — in-place v1.8 final release gate (NOT YET OPEN)

- [ ] Original v1.8 functional code gates above are satisfied or
  each genuinely infeasible limitation is explained and explicitly
  authorized; this branch is **not** yet complete.
- [ ] All existing v1.5–v1.8 instruments/CSV/Profiles regressions.
- [ ] Final production badge `v1.8` restored, exact FAP SDK/host CI
  and hash recorded, Flipper installed binary acceptance obtained.
- [ ] Replace only the published `v1.8` FAP/checksum after those
  gates; document **both old and new SHA/source** and independently
  verify remote asset digest; preserve immutable original tag
  and earlier v1.7 assets.
- [ ] v1.9 work only afterwards.

**Do not label research UI, decoder, CI or arbitrary hash as a
physically functional device.** Do not promise a solution to firmware
API restrictions before verifying the actual supported interface.
