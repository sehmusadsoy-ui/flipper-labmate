# LabMate v1.6 Stable — Publication readiness (2026-10-10)

**Status: READY FOR FINAL PUBLISH APPROVAL.** This is a written
release plan, not a GitHub Release or tag.

- **Stable candidate branch:** `v1.6-stable-candidate`.
- **Exact verified candidate commit:**
  `4a890002fea0acf8d524b7c772db3bbd3e239848`.
- **Green CI:** [GitHub Actions 38007158577](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38007158577)
  for that exact SHA, both Linux SDK/host tests and Windows installer mock.
- **Artifact name:** `labmate`; files inside: `labmate.fap`,
  `SHA256SUMS.txt`, checksum verified by CI and candidate installer.
- **Device smoke:** operator confirmed all requested points as PASS:
  visible `v1.6` text, Frequency Meter/Pulse Analyzer opening,
  saved S1 Profiles, saved CSV History, Generator defaults STOP.
  Earlier comprehensive DEV tests PASS for behavior inherited
  unchanged by this candidate. Do not claim each detailed measurement
  was repeated on the exact candidate.
- **Stable release proposal:** create tag `v1.6` **at the exact
  SHA above**, title `LabMate v1.6 Stable`,
  `prerelease=false`, attach verified `labmate.fap` and
  `SHA256SUMS.txt` from run 38007158577.
- **Preserve existing v1.5:** never delete, overwrite or retag
  the existing v1.5 Stable release or assets. The newly published
  v1.6 would naturally be the latest stable release, leaving
  v1.5 available as a fallback.
- **No `main` merge without separate approval:** publication of
  a tag/release at the candidate commit is a separate operation
  from moving the default branch.

## Mandatory publication safety checks

1. Confirm there is no existing `v1.6` tag or release, and the
   candidate SHA is unchanged. Abort if the tag already exists
   at a different SHA.
2. Reconfirm the exact successful run (CI jobs, SHA, artifact)
   and SHA256 checksum for the binary about to be uploaded.
3. Only after explicit publish permission, publish the new
   `v1.6` non-prerelease release and attach both files.
4. Verify release tag SHA, asset hashes and preserved v1.5.
   Continue using `main` unchanged unless separately requested.

## Honest limitations in public notes

- Frequency points were tested against the Flipper's own generator
  rather than an independent calibrated frequency standard;
  the resulting figures should not be marketed as a calibration
  accuracy specification.
- HIGH PB3 functional checks cover discrete low and kHz frequencies.
  Pulse Analyzer numerical checks cover PC1 at 100 Hz and 1 kHz
  at 50% duty, not every supported GPIO pin or duty cycle.
- No deliberate device fault-injection on corrupt/full/absent SD,
  sudden power loss or failed writes. Redundant CRC-protected
  Profiles improve resilience but do not guarantee arbitrary
  filesystem recovery.
- Connect only known, safe **3.3 V-compatible GPIO signals**.

The final tested stable-candidate branch remains frozen; documentation
is tracked separately on `v1.6-dev`.
