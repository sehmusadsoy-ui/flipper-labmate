# LabMate v1.7 Stable — RELEASE NOTES DRAFT (NOT PUBLISHED)

> **PREPARATION ONLY.** A `v1.7` non-prerelease GitHub Release and
> tag do **not** exist yet. The currently published Stable is v1.6.1.
> The final `v1.7` display-label artifact, checksum and exact source
> commit remain to be filled from the final, successful CI and physically
> smoke-tested on a real Flipper **before** release authorization.

## Scope and compatible platform

LabMate is a Flipper Zero external app for compatible **Momentum Firmware**,
with 3.3 V digital GPIO measurement, signal generation, recordkeeping
and instrument diagnostics. Installing the FAP does not update device
firmware. The final release asset will replace only
`/ext/apps/Tools/labmate.fap`; existing CSV and profile paths remain.

## Features and improvements since v1.6.1 Stable

- **PWM Studio (PA7 / TIM1):** original 15 frequency presets, adjustable
  5%–95% duty in 5% steps, and STOP-only CUSTOM 1–50,000 Hz editor with
  1/10/100/1000 Hz change increments. A generator intentionally keeps
  RUN state while navigating inside LabMate but always stops on full exit.
- **Event Counter (PB3 / TIM2):** real counted rising edges with
  RUN/STOP/RESET, elapsed time and saturating 64-bit total.
- **Button Analyzer (PC1 / EXTI):** open/closed digital contact state,
  press/release, selectable 5/10/20/50 ms debounce and bounce/settle/hold
  metrics. Clean digital loopback tested; actual mechanical contact not tested.
- **Threshold Alerts:** visual-only armed/latching alerts for frequency,
  pulse duty, event count and button settling; acknowledge and disarm.
- **Interface:** grouped MEASURE/OUTPUT/RECORDS/INFO navigation, unique
  icons for 11 tools, 13 About pages and refreshed 128×64 layouts.
- **Data Logger and History:** one-second samples of FREQ LOW PC1,
  FREQ HIGH PB3 and PULSE PC1; past and present CSV browse; explicit
  cancelable, single-selected-file irreversible DELETE.
- **Profiles:** 3 stored presets, CRC/redundant compatible format,
  named SAVE/OVERWRITE/DELETE confirmation, BACK cancellation and
  strict resource blocking. LOAD never starts PWM and preserves other
  profile slots.
- **Modularity and resource correctness:** measurement snapshot/statistics,
  CSV row formatting and Threshold sample adapter extracted into
  dedicated modules; drivers, GPIO/Timer/EXTI ownership and stored
  formats remain backward compatible by design.
- **Installer:** PowerShell script selects the published release
  channel, confirms release/tag identity, verifies FAP SHA256 and
  overwrites exactly one Flipper FAP path through USB.

## Verification, provenance and release status

- **RC1 published and tested:** [v1.7 RC1](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7-rc1)
  from `d55eec032e5f341f39aa7c98915ec2062995e66b`. Profiles UX
  fix on-device tests **16/16 PASS**, and tagged RC1 FAP matched that
  tested artifact byte-for-byte.
- **Refactored Stable Candidate source:** `bdb1de1058961b9d5285944c3d41e16c19183478`;
  FAP SHA256 `94883B517D526EAA0F64E2AEAC89F89D181F85FD4F3ABB9056F3EEC2B68123E0`.
  Momentum FAP + Windows mock installer CI
  [38191036835](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38191036835) **2/2 PASS**.
- **On-device regression on the exact refactored candidate FAP, user-reported,
  2026-10-12: 36/36 PASS.**
  7A launch/version/STOP/S1 persistence 3/3;
  7B PWM-Pulse 100 Hz 5/50/95%, stats/hold/STOP 6/6;
  7C LOW/HIGH Frequency, Event Counter and capture handoff 6/6;
  7D CSV three logger modes, History, delete cancel/confirm 7/7;
  7E clean-digital Button, visual Threshold, Profiles/guards 8/8;
  7F 11 tools, 13 About pages, 5-minute navigation, resource
  cleanup and persistence 6/6. Only 7B timings were screenshot-reviewed;
  the other checks are user reports.
- **Final stable-label source commit:** PENDING FINAL CI
- **Final Stable FAP SHA256:** PENDING FINAL CI
- **Final Stable-labeled device smoke:** PENDING REAL DEVICE
- **v1.7 Stable publication:** PENDING SEPARATE EXPLICIT APPROVAL.
  Do not publish or copy candidate RC1 checksum as final Stable.

## Known limits and deferred equipment tests

- The Flipper 3.3 V internal PWM loopback demonstrates functional
  timing, NOT an independent, calibrated frequency/duty/voltage or
  electrical OFF-level measurement. A calibrated oscilloscope or
  reference measurement instrument was not available.
- Real mechanical dry-contact bounce/settling has NOT been tested
  on hardware: Button metrics were functionally checked with clean
  digital signals. Configurable debounce does not guarantee performance
  for every physical switch.
- Not exhaustive: external 3.3 V reference sources, full preset/duty
  combinations, all pins, long continuous operation, abrupt power loss,
  full/missing/corrupt microSD and other failure injection.
  [Deferred hardware test register](DEFERRED_HARDWARE_TESTS.md) will
  be kept open and updated when equipment becomes available.
- Profiles use the legacy small record: no saved CUSTOM PWM frequency,
  PWM duty or Threshold Alert settings. CUSTOM SAVE is refused,
  preset LOAD resets duty to 50%, LOAD never activates PWM.
- CSV DELETE is irreversible. Preserve important profiles and logs
  with a backup before destructive operations.

## Installation and user safety

1. Use only a Momentum Firmware API-compatible LabMate FAP.
2. Once published, download `labmate.fap` and `SHA256SUMS.txt`
   together from the **official v1.7 Stable GitHub Release**,
   verify SHA256, then overwrite `/ext/apps/Tools/labmate.fap`.
3. Or use the version-aware, release-verified one-command
   PowerShell/USB installer from the final immutable v1.7 source;
   it requires `gh`, local Momentum toolchain and a connected Flipper.
4. **Only 3.3 V-compatible GPIO digital signals.** Never attach 5 V,
   mains, automotive or unknown voltages directly to Flipper GPIO.
   Always STOP PWM before changing external jumper connections.
   Back up valuable CSV/profile data; avoid unplugging microSD
   during active file access.

**Isolation:** v1.6.1 Stable and v1.7 RC1 tags and their release assets
remain unchanged and available after any future v1.7 Stable promotion.
