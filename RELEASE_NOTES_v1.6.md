# LabMate v1.6 Stable — Release Notes

**Published:** 2026-10-10  
**Download:** [LabMate v1.6 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6)  
**Released source/tag:** `v1.6` at commit
`4a890002fea0acf8d524b7c772db3bbd3e239848`  
**Verified build:** [GitHub Actions 38007158577](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38007158577)  
**Assets:** `labmate.fap` and matching `SHA256SUMS.txt`  
**Previous Stable:** [v1.5](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5), preserved for rollback.

## New in v1.6

- **Modular UI and grouped navigation:** MEASURE / OUTPUT / RECORDS /
  INFO, extracted Canvas screens and reusable navigation helpers.
- **Improved resource safety:** GPIO ownership policy isolates
  frequency/pulse captures and Generator PA7 PWM; STOP and app exit
  release the generator output. Generator LOAD from Profiles is
  refused while PWM RUN.
- **Frequency Meter:** HIGH PB3 TIM2 uses adaptive edge-aligned
  gating to fix the spurious ~10× readings at low-frequency PWM.
  LOW PC1 retains its period-based low-rate capture.
- **Pulse Analyzer:** HIGH/LOW/PERIOD/DUTY, MIN/MAX STATS and
  HOLD/LIVE; supported inputs PC0/PC1/PB2/PA4.
- **Profiles:** three SAVEd settings slots, LOAD and DELETE with
  user confirmation/cancel and redundant CRC32-protected A/B
  microSD records. Saves preferred frequency/pulse pins, generator
  preset and logger source. LOAD never starts generator output.
- **Data Logger / History:** compatible PC1 LOW/PB3 HIGH/PULSE PC1
  CSV recording (one row/second) and read-only session history.
  v1.5 CSV and v1.6 profile storage paths remain unchanged.

## Physical device verification

The development FAP underwent extensive operator-reported Flipper tests:

- HIGH PB3 measured 1, 2 and 10 Hz and 1, 5, 10, 20, 50 kHz
  using the Flipper's own Generator, with tight reported
  MIN/MAX ranges at the tested presets.
- Pulse Analyzer PC1 HIGH/LOW/PERIOD/DUTY at 100 Hz and 1 kHz,
  plus STATS and HOLD/LIVE checks.
- Generator PA7 BUSY reservation, STOP/release and application
  exit cleanup.
- Profiles: SAVE/LOAD/DELETE/cancel/persistence and refusal
  to LOAD while Generator RUN; empty-slot DELETE handled.
- Data Logger and Log History source modes, persistence across
  restart, and preservation of existing CSV entries.
- The exact v1.6 Stable candidate FAP was installed and passed
  real-device label, Frequency/Pulse screen access, saved Profile
  S1, Log History and Generator default STOP smoke checks.

Host C regressions, source boundaries, the Momentum SDK compile,
FAP checksum and mocked Windows installer transport passed in the
[successful build](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38007158577).

These are operator-reported functional measurements and tests,
not third-party laboratory calibration. Detailed evidence is in
[docs/V1_6_FIRST_DEVICE_TEST.md](docs/V1_6_FIRST_DEVICE_TEST.md).

## Known limitations

1. The Flipper's Generator and Meter share internal timing sources;
   agreement between them does not independently establish
   absolute frequency accuracy. HIGH PB3 data covers discrete
   test points rather than every possible external frequency.
2. Pulse Analyzer numerical checks were performed on PC1 at
   100 Hz and 1 kHz, not exhaustively across all pins and duty cycles.
3. Deliberate corrupt/full/absent microSD, failed-write and power-loss
   fault injection was not performed on the real device. Profile
   A/B redundancy helps normal recovery but cannot promise arbitrary
   SD filesystem recovery.
4. Only **known 3.3 V-compatible digital GPIO signals** may be
   used. Never connect 5 V or unknown voltages directly.
5. FAP compatibility depends on Momentum Firmware SDK/API versions;
   if the device firmware is incompatible, rebuild against a matching SDK.

## Installation and rollback

Download the release's `labmate.fap` and confirm its hash with
`SHA256SUMS.txt`, then install to `/ext/apps/Tools/labmate.fap`.
The verified PowerShell/GitHub CLI installation helper on `main`
can automate download, hash verification and installation over USB.
No Momentum firmware flashing is involved. Existing
`/ext/apps_data/labmate/` CSV and Profile data is not
intentionally removed by installation; back up important files.

The previous [v1.5 Stable release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5)
and its original assets remain available.

The default `main` source branch tracks this stable release's
instrument code and documentation. The `v1.6` tag itself is
unchanged and points to the tested production artifact.
