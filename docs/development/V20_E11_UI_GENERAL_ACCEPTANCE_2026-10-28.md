# LabMate v2.0 E11 Pixel UI — General Acceptance

Development branch: dev/v2.0-e11-ui-completion-20261028.
Review: Draft PR #24. No Stable/firmware/device writes.

## Verified evidence

- Counter Step 3 native E11 API 87.1: 171576-byte FAP, SHA-256 6ab9cd5278035b3bccdc8ebe1940ea9869ed9c29b66f92e007cfc3033dec21e9.
- UI completion native E11 API 87.1, SDKCHK, APPCHK and verifier PASS: Actions run 40739617831. 172060-byte FAP, SHA-256 922ef9594808db6ded65cec7a6a9fc506f54e842546dde9f87a8c41ba1942007.
- UI source preservation + GCC/Clang geometry and safety PASS: Actions run 40739625855.
- Legacy UI diagnostic: 30 suites, 15 PASS / 15 FAIL: Actions run 40740819534.
- Doctor Phase 3A + 3B corrected source expectations, GCC/Clang PASS: Actions run 40741361842. The editor intentionally allows Frequency and Pulse only; Scope requires its separate evidence path. No production Doctor code changed.
- Compatible current-suite aggregate: scripts/audit-v20-e11-predevice.sh, result tracked in Actions.

## Explicit unresolved legacy tests

**Current migration progress (post-inventory):** two Doctor suites, UI-01 Scope geometry/navigation, and the historical root-grid suite have been updated and now pass in GitHub Actions.

- UI-01: direct production `labmate_scope_ui_header/footer` geometry, current carousel/list layout, and stable navigation IDs; GCC+Clang PASS.
- Root-grid: replaced obsolete `labmate_menu_grid.h` dependency with production `draw_menu` source-contract checks and the current 5-group / 17-tool carousel and list viewport test; GCC+Clang PASS. This validates navigation/geometry contracts, **not** complete pixel raster output.
- Evidence: [Actions run 40743327323](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40743327323), [earlier UI-01 run 40742892634](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40742892634).

**Eleven old UI suites still require migration**: UI-02, UI-03, UI-04, UI-05, UI-05B, UI-05C Counter, UI-05D, UI-05E GPIO, UI-06, UI-06C and the old Ultimate Menu Renderer. Their earlier FAIL results are **not waived**. Some use outdated geometry, deleted menu header or obsolete Canvas function mocks. Replace with equivalent source-linked current `ui_kit` renderer/128×64 tests. The previous diagnostic's 15 failures remain an accurate result for its older commit, not today's latest suite status.

The old full-host runner is not the current release gate. No physical acceptance claim follows from these host-only tests.

## Physical consolidated acceptance — NOT YET PERFORMED

Prepare exactly one uniquely named E11 UI trial from exact CI-reviewed source when ready. Do not overwrite existing LabMate FAPs. Before cleaning up duplicate app names, inventory actual SD paths and hashes.

- Menu, Settings, Info: 128x64 layout, glyph widths, navigation and preference persistence.
- GPIO: all eight pins and their exact order; 104-bit waveform, no writes in input, hold/resume, busy/error.
- Counter: PB3/TIM2 Rising, Ready/Live/Stopped/Resume/Reset, real 3.3 V common-ground pulses and loss-free STOP.
- Frequency: PC1 low and PB3 high, source switching, lease conflict, accurate min/max, retry and STOP.
- Pulse: valid width/duty, actual IRQ, live/held/denied states and statistics.
- Button/PWM: debounce, press/release, PA7 duty/output and safe ownership return.
- UART/I2C/1-Wire: all states including busy/error, safe external 3.3 V wiring.
- Logger/History/Profiles: SD I/O, busy/CRC/errors, confirmation and persistence with sacrificial data only.
- Scope/Compare/Reference: only real completed capture, 128x64 geometry, busy/invalid/hold.
- Dashboard/Doctor/Alerts: only sealed evidence, no invalid successes or false diagnostic certainty.

Physical resource-contention, SD failure/recovery, regular-firmware compatibility and all modified screen visual acceptance are pending. Stable promotion is blocked pending sign-off.
