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

## Pending physical regression

**Not tested on a real Flipper yet.** When an exact successful
development build is installed via the development PowerShell
script, verify v1.6.1d label, PC1 LOW/PB3 HIGH/PULSE PC1 CSV
creation, previous History files, saved Profiles S1 and
Generator default STOP. Do not assert device PASS without
operator test reports. Use only known 3.3 V-compatible signals.

Further measurement/storage extraction and cleanup can proceed
in small changes with hardware validation after each stage.
