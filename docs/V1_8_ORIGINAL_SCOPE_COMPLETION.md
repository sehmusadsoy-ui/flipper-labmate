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
| v1.8 I²C Explorer | **HARDWARE-READY CONDITIONAL CODE, NOT YET OPERATIONAL ON STOCK FIRMWARE:** live HAL ACK adapter, threaded worker, local resource owner, COMM screen and result paging compile into the single development FAP. Stock firmware reports FW API rather than touching PC0/PC1. | Patched Momentum firmware/SDK **actual build** and then user physical safe scan/STOP/BACK validation |
| v1.8 optional 1-Wire | **REAL DRIVER CODE INTEGRATED, HARDWARE TEST PENDING:** PA4 1-Wire host reset/convert/wait/read, scratchpad CRC/temp decoding, no auto OTG, COMM UI and BACK/STOP resource cleanup compile in actual LabMate | Known 3.3 V externally powered single DS18B20 test, pin collision and measured temperature |

## Menu policy (fixed)

**MEASURE → OUTPUT → RECORDS → COMM → INFO (About)**.
INFO/ABOUT is always the **last root group and bottommost menu item**;
COMM is directly above it and contains UART, I²C Explorer and 1-Wire Temp.
Preserve historical tool IDs, profile storage format and 128×64 scrolling.
Portable navigation tests assert the COMM/INFO positions, child mapping
and About's final position. Do not move About into COMM.

## Code gates

### B — Button Analyzer

- [x] Bring prior Button STOP → RESUME implementation, host tests
  and lifecycle guard into *current v1.8* development app.
- [x] Existing physical v1.8.1d candidate Button B1–B6
  operator-reported **6/6 PASS**, source in previous draft PR #12.
  This is carry-forward behavior evidence, **not a physical PASS on
  the newly combined v1.8DEV build**.
- [x] Integrated `v1.8DEV` SDK/host CI [38558631375](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38558631375) PASS, exact source `8956f76d29d8e20d775533e1b066adfb05536872`, same candidate FAP SHA256 `524006f7229a8e706d270a108f21193021f7597ff1bfd6d70e03b66c21981ba9`; native Button, navigation and app-local COMM collision guards plus Windows installer mock PASS.
- [ ] Final *full-scope* device acceptance after I²C/optional 1-Wire integration.

### M — v1.6 resource and module completion

- [x] The app already has split capture/input/view/storage and
  deterministic internal capture owner, PWM TIM1 and USART lifecycle.
- [ ] Audit every production GPIO/IRQ/TIM/UART path, all STOP/BACK/
  failed-acquire/exit transitions and potential concurrent claims.
- [x] Implement **isolated application-local** COMM mutual-exclusion
  model for I²C PC0/PC1 and candidate 1-Wire PA4 (not PB14), explicitly
  refusing capture, GPIO Monitor, PWM, UART, Logger activity; non-owner
  STOP does not release the active owner. Portable tests PASS in
  [CI 38558631375](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38558631375).
  The local claim now guards both real 1-Wire PA4 and conditional I²C3 drivers; it is **not** a global firmware lock.
- [x] Connect local COMM owner gate to actual PA4 1-Wire driver
  START and all STOP/BACK/exit cleanup paths. Direct HAL-backed
  one-shot DS18B20 implemented and compiled; firmware-wide arbitration
  cannot be inferred from app-local exclusivity.
- [x] Connect the I²C runtime worker, COMM screen and PC0/PC1 app-local
  claim to a **conditional real HAL ACK transport**. On stock Momentum
  the feature fails closed with `FW API` and never acquires bus locks.
  SDK/native source tests PASS; genuine firmware runtime still pending.
- [ ] Compile verified modified Momentum firmware/SDK with the new
  exported bounded bus-acquire symbol; then build matching FAP and
  test peripheral ownership/Profiles/CSV regressions on real device.
- [ ] A firmware-wide lock claim requires a real exported HAL
  owner/lock contract or verified firmware change. App-local flags
  alone never guarantee global ownership.

### I — real I²C Explorer (blocked until viable owner path)

- [x] Preserve old pure scanner/pagination/lifecycle research in
  branch `dev/v1.8-i2c-explorer`, never call simulated hits real.
- [x] Design a compatible bounded mutex acquisition using Momentum's
  **same external I²C3 mutex and existing release path**, with finite
  50 ms wait instead of the stock infinite wait. Reproducible
  source patch has **source-application PASS** in
  [CI 38567640945](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38567640945),
  exact firmware source `d3f89dfe2ef6b01839201598e9be1590cba80322`.
  **Not a firmware compile, flash, or real cancellation PASS.**
- [x] Integrate original pure address scanner, result pages, per-probe
  lifecycle and **transport-injected worker** for true 0x08..0x77
  addresses, ACK/NACK/FAULT, bounded probe contract, STOP and exactly
  one matching owner release. All native tests + SDK FAP CI PASS in
  [38561645642](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38561645642).
- [x] Wire **real `furi_hal_i2c_is_device_ready` ACK probes** to the
  HAL adapter, bounded-acquisition contract, dedicated worker,
  I²C Explorer COMM UI, STOP/BACK thread join and owner cleanup.
  The patched SDK's `FURI_HAL_I2C_HAS_EXTERNAL_ACQUIRE_TIMEOUT` marker
  activates the transport automatically. On stock SDK the adapter
  deliberately returns unavailable; no unsafe blocking fallback.
- [x] SDK/host tests: [run 38568097149](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38568097149) PASS.
  Exact source `81f910d18104172387917808d471d21127e7171b`,
  integrated development FAP SHA256
  `4ae887fa2bc8d0ca54758487b37ec7421240d6c5e157782e328fb268b5ca8421`.
  Host fake HAL tested missing-API refusal, encoded ACK on 0x3C,
  STOP before acquire, BUSY and release. Runtime guards cover
  dedicated worker, release and status. **Not physical scanning.**
- [ ] **Compile full patched Momentum firmware and matching FAP**
  (source patch applicability alone is insufficient); validate
  firmware-wide mutex ownership, no deadlock, bus transfer timeouts,
  genuine STOP/BACK and resource release. On-device verification is
  a separate operator-approved gate.
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
- [x] Select **external PA4**, not PB14, and enforce LabMate-local
  capture/PWM/UART/Logger ownership exclusions (no firmware-wide GPIO
  arbiter exported); physical shared-owner cases still require review.
- [x] Implement actual 1-Wire host reset, 0xCC/0x44 conversion,
  nonblocking 800 ms conservative wait, 0xCC/0xBE scratchpad read,
  CRC8, signed temperature, unknown-power-on 85 C refusal,
  no OTG auto-power and immediate STOP cleanup.
- [x] Connect single integrated `COMM → 1-Wire Temp` screen with
  READY/RUN/DONE/NONE/BUSY/ERROR/PWR/STOP, explicit OK and BACK.
  INFO → About remains immediately above COMM.
- [x] Verified exact-source [CI 38563555290](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38563555290)
  on source `a40333dd2e8d2abccaa176ebd63f9037e7f5ee9b`:
  true Momentum SDK/FAP compilation, native CRC/temp tests, UI/menu
  guards, ownership and Windows installer mock PASS. FAP SHA256
  `afa88deb4d64752d9305708909663216778a17f7d8473611bb3c20513b2a1794`.
  **This proves SDK compilation, not physical sensor reading.**
- [ ] Physical known-safe 3.3 V, externally VDD-powered *single*
  DS18B20 test on PA4 with suitable pull-up; BUSY, STOP/BACK and
  existing-instrument regression pending. This is not yet Stable.

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
