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
  CI artifact `labmate`, subsequently installed and functionally device-tested
  on a Flipper with the provenance below.
- [x] Verify exact candidate FAP SHA256
  `94883B517D526EAA0F64E2AEAC89F89D181F85FD4F3ABB9056F3EEC2B68123E0`
  and install via COM7 to `/ext/apps/Tools/labmate.fap`. User confirmed
  install and startup on 2026-10-12. Test 7A: **3/3 PASS**
  (launch/no hang, `v1.7rc1` and initial PWM STOP, preserved Profile S1).
- [x] Test 7B: **6/6 PASS** on the exact candidate FAP using PA7→PC1
  Flipper 3.3 V internal loopback. Screenshot-reviewed Pulse readings:
  100 Hz/5% HIGH 500 us, LOW 9.50 ms, PERIOD 10 ms, DUTY 5.0%;
  100 Hz/50% HIGH 5.00 ms, LOW 4.99 ms, PERIOD 9.99 ms, DUTY 50.0%;
  100 Hz/95% HIGH 9.50 ms, LOW 500 us, PERIOD 10 ms, DUTY 95.0%.
  User also reported STATS/MIN/MAX, HOLD/LIVE and STOP/relaunch PASS;
  no defects reported. Functional loopback only; **not calibration**.
- [x] Test 7C: **6/6 PASS (user-reported)** on the installed Stable
  Candidate FAP, 2026-10-12. Frequency LOW PC1 ~10 Hz correct, MIN/MAX
  and HOLD/LIVE work; Frequency HIGH PB3 ~1 kHz correct; 10 Hz stimulus
  increments the PB3 Event Counter, START/STOP/RESET work, and the
  Counter -> Frequency HIGH ownership transition has no BUSY/ERR.
  No independent frequency calibration claimed.
- [x] Test 7D: **7/7 PASS (user-reported)** on the installed candidate
  FAP, 2026-10-12. User confirmed that FREQ/PC1 LOW, PULSE/PC1,
  FREQ/PB3 HIGH CSV recordings work; recent and previous History CSV
  reading works; DELETE confirmation can be cancelled without deleting,
  and confirmed DELETE removes only a disposable selected CSV.
  No independently inspected CSV file was provided in this phase.
- [x] Test 7E: **8/8 PASS (user-reported)** on the installed
  Stable Candidate FAP, 2026-10-12. Clean PA7->PC1 digital signal
  exercises Button Analyzer press/release count, contact state and
  details/debounce settings (NOT mechanical bounce verification);
  Pulse Duty visual Threshold ARM/ALRT/ACK/OFF responds at the 50%
  limit; existing Profile S1 LOAD does not activate PWM; a disposable
  empty-slot profile saves, survives restart, DELETE cancellation
  preserves it and confirmed DELETE removes only that temporary slot;
  PWM RUN blocks LOAD/SAVE/DELETE with S1 preserved. User reported
  all eight checks working, without screenshots for this phase.
  Cumulative Test 7A+7B+7C+7D+7E: **30/30 PASS**
  (user-reported; 7B measurements screenshot-reviewed).
- [x] Test 7F: **6/6 PASS (user-reported)** on the same installed
  Stable Candidate FAP, 2026-10-12. Four groups (5/2/3/1), all 11 tools,
  all 13 About pages and the major tool layouts rendered without clipping;
  ~5-minute menu navigation had no freeze/crash; repeated capture
  handoffs and STOP/START showed no stuck BUSY/ERR; after exit/relaunch
  PWM remains STOP and Profile S1/CSV history persisted. No defects reported.
  Cumulative **Test 7A–7F = 36/36 PASS**. This excludes deferred
  external oscilloscope, real mechanical button and SD fault-injection tests.
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
