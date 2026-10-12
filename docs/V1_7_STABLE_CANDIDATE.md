# LabMate v1.7 Stable candidate — work and gates

Status: **WORK IN PROGRESS / NOT STABLE / NOT PUBLISHED**.

## Immutable baseline and isolated development

- Source baseline: published `v1.7-rc1` at commit
  `d55eec032e5f341f39aa7c98915ec2062995e66b`.
- Baseline FAP SHA256:
  `ED2E91A02AB0F720D6B48EAC13D505D37570FB3A4A1F8E8A76D59E1B79FE14AA`.
- Branch: `v1.7-stable-candidate`. Do not edit published RC1 tag/assets,
  `main`, published v1.6.1 Stable assets or installer.
- Device-tested RC1 Profiles fix 6A+6B+6C: **16/16 PASS**,
  before any Stable-candidate source modifications.

## Candidate work

- [ ] Complete extraction of app-thread measurements into
  `labmate_measurements.c/.h`, preserve capture IRQ/pin ownership and
  all frequency/pulse statistics, run source-architecture and native tests.
- [ ] Verify one-command `scripts/install-v17-from-github.ps1` release
  selection, SHA256 verification, fixed destination and error handling
  with Windows mock transport. The Stable channel is unavailable until a
  separate `v1.7` Stable release exists; RC1 is already published.
- [ ] Freeze remaining changes; use an on-device build with Stable
  version label `v1.7` only after code/installer QA.
- [ ] Run candidate CI compile + portable tests + mock Windows installer.
- [ ] SHA256-verify exact candidate FAP; install over USB and repeat key
  device smoke/regression: startup, PA7 STOP on exit, 100 Hz 5/95% duty
  with Pulse, LOW/HIGH Frequency, PB3 Counter, clean PC1 Button,
  Threshold Alerts, CSV Logger/History cancel/delete, Profiles
  SAVE/LOAD/DELETE and PWM-RUN blocks.
- [ ] Check resource-hand-off and repeated navigation/STOP/START; check
  storage error behavior when practicable on disposable test data.
- [ ] Review full 11-tool menu, 13-page About and 128x64 clipping.
- [ ] Update README/ROADMAP/CHANGELOG/release notes; list hardware test
  gaps from [DEFERRED_HARDWARE_TESTS.md](DEFERRED_HARDWARE_TESTS.md).
- [ ] Obtain separate explicit approval for **v1.7 Stable**, then pin
  final source commit, create and verify final release + SHA256 assets.
- [ ] Verify stable release non-prerelease, correct tag/FAP/checksum,
  one-command Stable installer and no changes to previous published releases.

**IMPORTANT:** RC1 tests do not automatically validate a modified
stable-candidate FAP. Do not mark unperformed hardware checks PASS. Physical
mechanical button, independent scope/electrical output validation, full SD
fault-injection and all edge cases are currently deferred.
