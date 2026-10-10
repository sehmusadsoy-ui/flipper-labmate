# LabMate v1.6 — Stable Release Candidate Preparation

**Status (2026-10-10):** Stable **candidate** isolated from the device-verified
v1.6 RC1 commit. The **Stable GitHub Release has not yet been published**.
No update to `main` or the `v1.5` release is authorized by this preparation.

## Provenance

- **Parent:** v1.6 RC1 commit `62e708fc7c556fe89ef2a1bc99a6ced259434cdf`.
- **Parent Actions:** [run 38005381142](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38005381142), successful Momentum SDK compile, four host C regressions, static guard, FAP SHA256, Windows mock transport tests.
- **Flipper RC1 operator smoke (PASS):** on-device `v1.6rc1`, Frequency Meter/Pulse Analyzer entry, persisted S1 Profile, CSV Log History, and Generator STOP. Earlier **development** build's detailed LOW PC1 / HIGH PB3, Pulse time/duty/stats/HOLD, profiles SAVE/LOAD/DELETE, logger/history and resource-ownership tests also PASS.
- **Candidate label:** `v1.6` displayed in the app menu/About. Momentum `application.fam` remains `fap_version="1.6"`.
- **Hardware and storage implementation:** unchanged relative to RC1; only visible label width/text, branch-scoped workflow/installer, CI guard and documentation differ.
- **Branch:** `v1.6-stable-candidate`; the `main` branch, v1.6 RC1 and v1.5 Stable are kept untouched.

## Release changes since v1.5

- Grouped navigation for Measure / Output / Records / Info.
- Improved input selection and GPIO/PA7 resource arbitration.
- LOW PC1 frequency mode and HIGH PB3 TIM2 adaptive gate fix.
- Pulse Analyzer HIGH, LOW, PERIOD, DUTY, STATS MIN/MAX and HOLD.
- Signal Generator PA7: existing 15 frequencies, 50% duty and protected RUN/STOP handoff.
- Three CRC32-checked microSD Profile slots with SAVE/LOAD/DELETE, redundant A/B records and LOAD safety refusal while generator runs.
- CSV Data Logger (PC1 LOW, PB3 HIGH, PULSE PC1) and read-only Log History retained.
- No migration of existing Profile and CSV paths.

## Known validation limits — must be disclosed even in Stable

- Measurement points with the built-in generator do not independently calibrate absolute frequency; both generator and meter share Flipper timing sources.
- HIGH PB3 was device-tested at 1, 2, 10 Hz and 1, 5, 10, 20, 50 kHz discrete points, not every value in a continuous frequency band.
- Pulse PC1 timing/duty was checked at 100 Hz and 1 kHz; other input pins/frequencies are not fully characterized.
- Controlled corrupt/full/missing microSD, failed writes and abrupt power loss were not physically fault-injected. Redundant profile recovery is codec-tested but not guaranteed in all filesystem damage scenarios.
- Only known 3.3 V-compatible signals and previously verified connections may be applied to Flipper GPIO.

## Stable publishing gate

1. This branch's own GitHub Actions must PASS guard tests, host C tests, Momentum SDK FAP compile, checksum packaging and mock PowerShell installer checks.
2. Install the **exact successful Stable candidate** `labmate.fap` via GitHub CLI + PowerShell, and verify the SHA256-protected artifact at install.
3. On the physical Flipper confirm **`v1.6`** label, Frequency/Pulse screens, PA7 initial STOP, preserved Profiles/CSV History; report any regression. The RC1 device PASS is not automatically a PASS on the new binary.
4. Explicitly approve **publishing** `v1.6` Stable; only then create the public `v1.6` tag and release, upload `labmate.fap` + `SHA256SUMS.txt` from the successful candidate run, and consider `main` promotion as a **separate decision**.
5. Keep existing `v1.5` tag, release and downloadable assets intact, even after a new Stable release.

The candidate installer selects only `v1.6-stable-candidate` and refuses to install a stale success run if branch HEAD moves. The production release has not been made.
