# LabMate v1.6.1 — Dev Refactor, Step 1

**Branch:** `v1.6.1-dev`, forked from `main`
`08133dba06bf5c18780081e00a87b6778c3a29ba`.
**Status:** isolated development build, NOT v1.6.1 Stable.
Existing v1.6 tag/release and v1.5 Stable are unchanged.

## Extraction

- Add `labmate_logger_codec.c/.h`: pure C functions to decode
  `log_0001.csv` ... `log_9999.csv` filenames and to format
  existing FREQ/PC1, FREQ/PB3 and PULSE/PC1 CSV records.
- Keep file opening/closing, timestamps, sampling cadence, UI mutex,
  error handling and GPIO capture in the existing app loop for now.
- Keep identical CSV layout, invalid sample encoding and decimal
  precision; current microSD storage paths remain unchanged.
- Host native C tests verify filename edge cases, CSV rows, small
  output buffer handling and invalid input.
- Device label: `v1.6.1d`; `application.fam` retains SDK-compatible
  external-app manifest version `1.6` while the dev FAP is tested.
- Workflow builds modular Momentum FAP, existing host tests, new
  logger format tests, SHA256 artifact and Windows mock installer.
- Dev-only `scripts/install-v161-dev.ps1` requires successful
  CI for the exact branch head and validates `labmate.fap` SHA256;
  the published Stable installer remains release-pinned to v1.6.

## Step 1 — real Flipper regression: PASS (operator report)

The operator installed exact CI FAP from run
[38045960606](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38045960606)
(commit `c593a3322f1ca6505d2b02d0305e597998b595b1`)
via the checksum-checked PowerShell installer and confirmed all seven
smoke/compatibility tests PASS:

- `v1.6.1d` displayed correctly.
- PC1 LOW, PB3 HIGH and PULSE PC1 CSV recording each PASS.
- Log History reads both older and newly created CSV files.
- Previously saved Profile S1 persisted.
- Signal Generator default remained STOP.

This is functional device validation, not external metrology calibration
or intentional corrupt/full-microSD fault injection.

## Step 2 — read-only History module extraction

- Move all four existing Log History storage methods from `labmate.c`
  into `labmate_history.c/.h`: scan, open, incremental read and close.
- Keep the same I/O order, SD error handling, mutex boundaries,
  record formatting and 256-byte read size. This move does not modify
  the content of any existing CSV.
- Share one `LABMATE_LOGGER_DIR` macro between Logger and History.
  Continue to use `/ext/apps_data/labmate` without any on-disk migration.
- Retain canvas drawing in `labmate_ui_screens.c`, the pure CSV
  codec in `labmate_logger_codec.c`, and GPIO/IRQ/PWM routines in core.
- Extend CI architecture guards to require one implementation for
  each History operation, read-only SD mode and unchanged path.

**Next gate:** Step 2 will need a separate CI PASS and physical
regression check after installation. The prior seven PASS tests
apply to Step 1 only. Use only known 3.3 V-compatible signals.
