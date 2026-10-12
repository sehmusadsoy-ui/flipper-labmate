# LabMate v1.7 RC1 — Preparation and release gates

**State: PREPARATION / NOT PUBLISHED.**
Stable v1.6.1 release, tag and branch must remain unchanged.
The v1.7 development source has passed build tests and specific
on-device checks, and a separately built RC1 candidate now passes CI but has not yet been device-tested.

## RC1 candidate build checkpoint (not published)

- [x] Candidate branch: v1.7-rc1 (no GitHub Release or tag).
- [x] LCD label: v1.7rc1; FAP manifest version: 1.7.
- [x] Exact RC1 FAP source commit:
  55edee5890c2d62ea229f9271c97c6260b067b5a.
- [x] RC1-specific CI run 38186623651: 2/2 jobs PASS
  (Momentum SDK FAP, layout/static tests, Windows mock installer).
- [x] CI generated artifact labmate (id 11719294967) containing
  labmate.fap and SHA256SUMS.txt; NOT a published release.
- [ ] Verify downloaded FAP SHA256 against SHA256SUMS.txt.
- [ ] Fresh physical smoke test of exact RC1 artifact before signoff.
- [ ] User approval required before any GitHub release/tag or stable change.

## 1. Provenance / source freeze

- [x] Record last successful *source* CI baseline:
  `b5bbd31804d3bed068aaf425e0b408fa7962ddbc`.
- [x] CI [38185793925](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38185793925):
  Momentum FAP build/guards/host checks and Windows mock installer
  **2/2 PASS**; artifact `labmate` contains `labmate.fap` and
  `SHA256SUMS.txt` (artifact ID `11719268606`).
- [x] Compare this source to the later development head
  `52fe588ddf19a38bc01bda7f8de6d4a6cc7d725b`:
  two subsequent commits changed **only**
  `docs/V1_7_DEV_NOTES.md`, not app source or FAP packaging.
- [x] Development manifest: `application.fam fap_version="1.7"`;
  device display text: `LABMATE_VERSION_TEXT "v1.7d"`.
- [x] Write draft RC1 notes with limitations:
  `docs/V1_7_RC1_RELEASE_NOTES_DRAFT.md`.
- [x] Freeze the exact final candidate source snapshot. Future source
  changes invalidate the previously verified FAP and require new CI.
- [x] Prepare an isolated `v1.7-rc1` candidate branch and give its
  *LCD UI* a distinct `v1.7rc1` label. Keep manifest metadata
  SDK-compatible as `1.7`; suffix-bearing manifest versions caused
  trouble during v1.6 packaging.
- [x] Ensure RC1-specific CI runs from the candidate branch/commit
  and uploads an artifact; do not repurpose the older dev artifact as RC1.
- [ ] Verify both source commit provenance and
  **`labmate.fap` SHA256 against `SHA256SUMS.txt`** when downloaded.
  An Actions artifact ZIP digest is **not** the FAP SHA256.

## 2. Development physical evidence (user-reported)

- [x] PWM Studio, 100 Hz duty 5/25/50/95%, 1 kHz/50% and CUSTOM
  1235 Hz/50% tested with internal 3.3 V PA7 loopback.
- [x] Pulse Analyzer PC1, STATS/HOLD and short-pulse averaging at
  5% / 95%; LOW PC1 frequency; HIGH PB3 frequency.
- [x] PB3 Event Counter with RUN/STOP/RESET and capture-owner
  transitions through Frequency/Logger; app exit/reentry STOP behavior.
- [x] Button Analyzer and all four Threshold Alerts sources with clean
  Flipper-generated digital input, not a mechanical switch.
- [x] CSV Logger's three modes, older/newer Log History and S1
  Profiles persistence/LOAD.
- [x] New menu icons, 13-page About guide and principal instrument UI
  testing; screenshot-reviewed revised Records (Logger, History,
  Profiles).
- [x] User subsequently reported the single-CSV DELETE addition
  working on their Flipper as an overall PASS.
- [ ] **Not separately confirmed:** HISTORY DELETE confirmation
  cancellation preserves a disposable file, unrelated CSV remains
  readable, profile remains intact, repeated SD error paths. Test
  with a *throwaway* CSV only; do not delete valuable logs.

## 3. Fresh RC1 FAP smoke test — pending

The following must use the *new RC1-labeled build*, not the earlier
`v1.7d` development FAP. Use only safe built-in Flipper 3.3 V PWM,
STOP before moving any jumper, and no external voltage source.

- [ ] Confirm menu/About show **v1.7rc1**, all groups and 11 icons
  render without clipping, and PWM initially shows STOP.
- [ ] With **PA7 -> PC1**, verify PWM at 100 Hz / 95% and 5% gives
  HIGH/LOW/PERIOD/DUTY plus STATS; check STOP/reentry.
- [ ] On PC1, enter Frequency LOW and Button Analyzer with a suitable
  clean 1 Hz stimulus; confirm no capture ERR or frozen screen.
  Real mechanical bounce is explicitly deferred.
- [ ] After PWM STOP, move jumper to **PA7 -> PB3**; verify 10 Hz
  Event Counter RUN/STOP/RESET, Frequency HIGH and capture handoff.
- [ ] Exercise at least one Threshold Alerts ARM/TRIPPED/ACK/OFF
  state with the applicable safe source; verify UI isn't clipped.
- [ ] Make a brief *disposable* Data Logger CSV, STOP/close the
  recording, open it in History, cancel deletion with BACK, confirm
  file still exists, then explicitly DELETE that disposable file.
  Verify list rescan and that another known CSV remains readable.
  No deletion without identifying the disposable file first.
- [ ] Open Profiles: saved S1 remains readable; LOAD does not START
  PWM. Do not overwrite/delete S1/S2 for an RC smoke test.
- [ ] Fully exit LabMate while PWM RUN, relaunch and confirm STOP;
  stop PWM explicitly when tests are finished.
- [ ] Record any visual defects, unexpected storage errors, FAP source
  SHA and verified checksum. Update the evidence log only after
  user reports exact results.

## 4. Disclosures / non-blocking equipment gaps

- [ ] Mark **NOT TESTED**: real dry-contact mechanical pushbutton
  bounce, settle and hold behavior. User deferred until equipment.
- [ ] Mark **NOT TESTED**: independent oscilloscope verification of
  output HIGH/LOW voltages, duty/frequency, waveforms and electrical
  OFF state. Loopback is functional verification, not calibrated
  metrology. User deferred until equipment.
- [ ] Disclose unexhaustive frequency range, full/corrupt/absent SD,
  abrupt power-loss, and other error-path testing.
- [ ] Disclose Profiles restrictions: no saved CUSTOM frequency, duty
  or Threshold settings; CUSTOM SAVE refused; LOAD duty resets to 50%.
- [ ] Clearly identify single-CSV deletion as irreversible, show its
  explicit confirmation, and advise backing up valuable logs/profiles.

## 5. Go / no-go and publication controls

- [ ] Finish RC1 branch CI, package/checksum and fresh physical smoke.
- [ ] User reviews candidate screenshots and release notes; explicitly
  approves or rejects RC1 publication.
- [ ] Only after approval: create a clearly marked **pre-release** tag
  and attach the exact tested FAP/checksum. No Stable promotion.
- [ ] Leave `main`, v1.6.1 Stable tag and existing release assets
  **unchanged**; never overwrite the stable install script to point
  at an unpublished RC.
- [ ] On future stable promotion, request a separate explicit decision
  and verification; do not infer it from RC1 test success.

**Next action:** download and SHA256-verify the isolated RC1 FAP from run 38186623651, install it on Flipper and complete the on-device smoke test. Release/tag creation still requires user approval.
