# LabMate v1.7 Stable — GitHub-to-USB installer

**Published Stable:** [v1.7](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7)
with two assets, `labmate.fap` and `SHA256SUMS.txt`.
This is an **in-place maintenance/documentation update**, not a new
version or a modification of published binary/tag assets.

The released installer `scripts/install-v17-from-github.ps1` checks
the official release's tag, commit, Stable/prerelease status and SHA256,
then replaces only `/ext/apps/Tools/labmate.fap` over USB. It does
not flash firmware or intentionally delete CSV/Profile data.

- **Required:** Windows PowerShell, signed-in GitHub CLI (`gh auth login`),
  compatible local Momentum Firmware checkout (usually
  `$HOME\Momentum-Firmware`) with `scripts\toolchain\fbtenv.cmd`
  and `scripts\runfap.py`, and a USB-connected Flipper for installation.
- **Published source tag:** `v1.7` at
  `d0e1bc6a95b257841533f0aa8745e3a79bbc8dcd`.
- **Official FAP SHA256:**
  `5A7CB0EAE601EEAC8856790211C4D2831A9198C31853631E1DAF0308CE724335`.
  The installer verifies the checksum file; it does not perform independent
  calibration of a GPIO signal.

## 1. Verify the Stable release without installing

Review the
[immutable v1.7 installer source](https://github.com/sehmusadsoy-ui/flipper-labmate/blob/v1.7/scripts/install-v17-from-github.ps1),
then run in Windows PowerShell:

```powershell
$ErrorActionPreference = 'Stop'
$script = Join-Path $env:TEMP 'install-labmate-v17-stable.ps1'
Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/v1.7/scripts/install-v17-from-github.ps1' -OutFile $script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Channel Stable -VerifyOnly
if ($LASTEXITCODE -ne 0) { throw 'LabMate v1.7 Stable VerifyOnly FAILED' }
Write-Host 'LabMate v1.7 Stable release checksum PASS' -ForegroundColor Green
```

Expected output includes `RELEASE VERIFIED: v1.7`,
`SHA256 VERIFIED:` followed by the official hash above, and
`VerifyOnly complete: no USB installation.`

## 2. Install/overwrite the single FAP

After the verify-only check succeeds, with the Flipper connected
and not actively recording data, use the same `$script`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Channel Stable -Port COM7
if ($LASTEXITCODE -ne 0) { throw 'LabMate v1.7 Stable USB installation FAILED' }
Write-Host 'LabMate v1.7 Stable USB install PASS' -ForegroundColor Green
```

Change COM7 if the device uses a different port. An explicit USB
installation test with `-Channel Stable` was **not yet operator-confirmed**
when this document was written; CI Windows transport mocks and a
real-Windows `-Channel RC1 -VerifyOnly` did pass. Do not record
an unperformed live Stable-channel USB test as PASS.

## 3. Device regression after install

Check the menu/About version text `v1.7`, initial PWM STOP,
Profile S1 retention and previously saved History CSV files. A
freshly installed FAP should overwrite the same single Tools app
entry; no duplicate LabMate app is expected. Stop PWM before
changing any jumper wiring; use known 3.3 V-compatible signals only.

## Fallback and unresolved compatibility test

- Published [v1.6.1 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6.1)
  and [v1.7 RC1](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7-rc1)
  remain unchanged.
- Older `scripts/install-from-github.ps1` is intentionally pinned
  to **v1.6**. Use the v1.7-specific installer above for current Stable.
- **Microsoft Excel CSV import: NOT TESTED.** LibreOffice Calc import
  succeeded. Since Microsoft Excel is not available for the present
  test environment, this QA item remains deferred without buying a
  license. See [deferred checks](DEFERRED_HARDWARE_TESTS.md).
- Back up valuable CSV and Profiles before maintenance, and do not
  remove the microSD card during active file access.
