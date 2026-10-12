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

- [x] Extracted app-thread measurements into `labmate_measurements.c/.h`,
  CSV row snapshots into `labmate_logger_snapshot.c/.h` and Threshold
  validity gating into `labmate_alerts_bridge.c/.h`. Capture IRQ/PA7 pin
  ownership remains in the existing source modules. Source boundary,
  portable logic and Momentum SDK CI checks PASS (physical regression pending).
- [x] One-command `scripts/install-v17-from-github.ps1` includes pinned RC1
  and future Stable release channels, SHA256 checks, single-FAP destination,
  and rejects metadata/hash/USB errors in Windows mock tests.
  **Not yet physically verified** with the future Stable release. Stable
  remains unavailable until the separate `v1.7` release exists.
- [ ] Freeze remaining changes; use an on-device build with Stable
  version label `v1.7` only after code/installer QA.
- [x] Candidate CI [38191036835](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38191036835)
  **2/2 PASS** on source `bdb1de1058961b9d5285944c3d41e16c19183478`:
  SDK FAP compile, architecture and host tests, Windows mock installer.
  CI artifact `labmate`; this is **not** physically tested yet.
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

Current operating policy: keep `docs/DEFERRED_HARDWARE_TESTS.md` open across releases; do not report mechanical/scope/SD fault cases PASS without actual equipment evidence.
