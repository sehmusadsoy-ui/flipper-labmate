# LabMate v1.6 RC1 — Candidate release notes

**Status:** Development release candidate on a dedicated branch,
not a stable production release or an existing v1.5 replacement.

- **Branch:** `v1.6-rc1`, forked from the fully user-tested
  `v1.6-dev` documentation head; instrument logic and data formats
  were not changed for RC1.
- **RC1 identity:** LCD version `v1.6rc1`, external app manifest
  version `1.6` (kept SDK-compatible). The installed LCD and distinct
  RC1 build still clearly identify the release candidate.
- **Build:** GitHub Actions workflow `build-v1.6.yml` on this
  RC1 branch. Checks: source/hardware boundaries, resource policy,
  navigation, profile CRC codec/delete, TIM2 gate math, Momentum SDK
  FAP compilation, verified `labmate.fap` SHA256 archive, and
  mocked Windows installer transport.
- **Binary naming:** `labmate.fap` packaged as artifact `labmate`
  with `SHA256SUMS.txt`. No manual ZIP handling needed for user installs.
- **Installer:** `scripts/install-from-github.ps1` on the RC1
  branch queries only `v1.6-rc1` successful runs, checks the latest
  branch-head SHA and downloaded file checksum, then requests the
  COM7 Flipper app installation using the Momentum tools. It does
  NOT flash the firmware or deliberately remove saved CSV/profile files.
- **Stable isolation:** `main`, v1.5 Stable release/tag and
  `v1.6-dev` remain untouched.

## Major features and user-verified functionality inherited from dev

Grouped app navigation and passive view extraction; exclusive GPIO
capture arbitration; adaptive HIGH PB3 frequency counter (including
the original 1 Hz -> 10 Hz bug fix); 3-slot Profiles SAVE/LOAD/DELETE
with redundant, validated microSD copies; safe refusal to LOAD while
PA7 generator is RUN; Data Logger / CSV history compatibility.

User-reported physical PASS evidence before RC1 packaging: LOW PC1,
HIGH PB3 discrete 1/2/10 Hz and 1/5/10/20/50 kHz points,
Pulse Analyzer PC1 at 100 Hz and 1 kHz + STATS/HOLD,
Generator resource release/exit, P1-P5/P7/F2 profiles,
and R1-R4 latest Data Logger regressions. Consult
`docs/V1_6_FIRST_DEVICE_TEST.md` for detailed operator reports.

## Residual limits and gate to stable

The dev device passes do not yet verify the **newly packaged RC1
binary**. Before declaring the RC1 physically PASS, install the
successful RC1 build and confirm device startup and version text,
menus, low/high frequency, Pulse Analyzer, PA7 STOP/BUSY safety,
profile persistence, logging and history.

Independent absolute frequency calibration was not performed.
Flipper Generator and Meter share internal timing references.
Controlled corrupt/full/unavailable SD, sudden power loss, and
all alternate Pulse input measurements remain untested. Avoid
deliberately damaging storage or testing unsafe voltages merely
to claim coverage. Use only previously verified 3.3 V-compatible
equipment; no uncontrolled new connections.

**Do not publish or promote v1.6 Stable without explicit operator
approval after reviewing RC1 physical smoke results.**

## RC1 CI correction

The first RC1 attempt encountered a Momentum SDK app-discovery/build
failure after setting `fap_version` to the suffix-bearing
`1.6-rc1` string, so the app manifest version was restored to
`1.6`, matching the successfully compiled device-tested developer
build. The on-device `v1.6rc1` label remains. The Windows mock
installer check also needed the correct PowerShell literal/regex
matching for the RC1 branch name. Both fixes are packaging/test
changes only; no GPIO, frequency estimator, PWM, profiles, logger
or menu logic changes.
