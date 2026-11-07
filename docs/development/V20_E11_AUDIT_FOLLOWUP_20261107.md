# E11 audit follow-up — 2026-11-07

This source-only review preserves the approved renderer and installed device.
It does not establish release readiness or resolve startup/OOM issue #31.

## Acceptance and historical commands

Run `sh scripts/test-v20-e11-final-ui-predevice-host.sh` for current E11
acceptance. It includes the production-linked History and OneWire audit-fix
regressions as well as the existing GCC/Clang integration gates. Run against
LF source with full branch history. Native compilation uses the exact E11
patched Momentum SDK, not stock/Normal Momentum.

Historical runner results from the 2026-11-06 audit remain visible:

| Historical entry point | Remaining reconciliation |
|---|---|
| frequency-ui-state, pulse-ui-state, level-witness, scope-diagnostics | Missing historical pure-module source files; no blanket PASS inferred from current renderer tests |
| ultimate-menu-renderer | Missing historical `labmate_menu_grid.h` |
| offline-full, ultimate-ui-contract | Old shared menu-header contract contradicts approved current E11 layout |
| audit-v20-ultimate-sources | Old navigation/module contract |

The legacy coverage inventory exits zero even with failed inner checks;
its original 29 PASS / 1 FAIL count is diagnostic, not acceptance. No failing
historical command was suppressed or changed to return success here.

## Release gates still open

- Startup/OOM #31 and repeated/idle launch/exit heap recovery.
- Device-runtime validation of any newly built FAP; the installed candidate
  remains the original 177804-byte CI artifact, SHA-256 `160e1c2c7e5f63418bf641fc7b5ab9a72f5bb45219126d914b94185654d10e7e`.
- Disposable-data save/restart and storage-fault recovery; readable existing
  profiles/CSV are not new-write durability proof.
- Historical test coverage reconciliation and CI at the publication SHA.
- Firmware patch provenance and real GPIO/UART/I2C/1-Wire electrical tests;
  B01 stays paused.

No firmware flashing, installed FAP replacement, SD mutation, merge or Stable
release is performed by these checks. A future preview must retain
`RC / hardware-validation-pending` and disclose any remaining software gates.
