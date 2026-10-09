# LabMate v1.6 RC1 — Candidate branch checklist

**State:** RC1 branch prepared from the device-tested v1.6-dev code.
CI and a **fresh on-device RC1 smoke test** must complete before
considering stable promotion. This is not a stable release.

**Tested application code:** `4eaf8054d354fb7725617b72df25c0a974daf214`  
**Confirmed successful build:** [GitHub Actions 38001774685](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38001774685)  
**Distribution artifact:** `labmate` containing `labmate.fap` and `SHA256SUMS.txt`.  
**RC1-specific UI text:** `v1.6rc1`; compatible SDK FAP manifest version: `1.6`.
The RC1 identity is the separate branch, LCD label and checksum-verified build; the SDK's FAP metadata stays within its supported version format.

**RC1 branch:** [`v1.6-rc1`](https://github.com/sehmusadsoy-ui/flipper-labmate/tree/v1.6-rc1).
The RC1 Actions workflow selects only this branch. Its PowerShell installer
checks the latest successful RC1 build against the branch head before install.  
**Evidence log:** [V1_6_FIRST_DEVICE_TEST.md](V1_6_FIRST_DEVICE_TEST.md)

## Functional gates — all user-reported PASS

| Area | Verified examples |
| --- | --- |
| Navigation | A1-A8, grouped menu, tool entry/exit |
| Resources | B1-B6, F1 PA7 BUSY/STOP/release/exit safety |
| Frequency Meter | Corrected HIGH PB3 1/2/10 Hz; 1, 5, 10, 20, 50 kHz points, LOW PC1 |
| Pulse Analyzer | PC1 100 Hz and 1 kHz 50% PWM, HIGH/LOW/PER/DUTY, STATS and HOLD |
| Profiles | P1-P5 + P7: three slots, A/B microSD, save/load/delete/cancel/persistence; F2 empty-slot DELETE UI |
| Data Logger/History | C1-C5 + R1-R4; PC1 LOW, PB3 HIGH, PULSE PC1, CSV persistence/history |

The user manually observed these outcomes on Flipper Zero; GitHub
CI cannot substitute for device tests or independent calibration.

## Residual limitations to disclose or separately qualify

- HIGH PB3 frequency checked at five *discrete* kHz presets; no
  blanket promise about the continuous range or accuracy of an
  external signal. The built-in generator and counter share Flipper
  hardware references; independent lab-grade calibration has not occurred.
- The Pulse Analyzer was accuracy-checked on PC1 at 100 Hz and
  1 kHz, not exhaustively at every input or signal duty cycle.
- Controlled A/B-corruption recovery, full/absent SD, failed SD
  write and sudden power loss have not been physically verified.
  Do not intentionally harm or corrupt the user's device/data.
- F2 confirms the EMPTY state in UI, not the absence of every
  underlying microSD command; code-level no-op has a separate guard.
- The new RC1 label is a cosmetic/UI and manifest change from the
  earlier device-tested dev FAP. The newly packaged binary still needs
  a basic physical startup, navigation and capture regression check.

## Controlled release decision (requires operator direction)

1. Freeze working instrument algorithms and preserve the proven
   `labmate.fap` naming and GitHub CLI + PowerShell installation path.
2. RC1 branch is isolated and requires its own green GitHub Actions
   run (four portable/guard tests + Momentum SDK build + mock Windows
   transport tests). The operator must then smoke-test the exact RC1 FAP
   by opening the tools, verifying STOP/BUSY and CSV/Profile persistence.
3. Promote to stable only with an explicit request from the operator
   after reviewing the residual limitations. Never silently replace
   v1.5 stable or claim those tests were run.

No Stable release or tag is created here. GitHub Actions will produce
an RC1 artifact named `labmate` containing `labmate.fap` and
`SHA256SUMS.txt`. Existing profile data and CSV paths are unchanged.
