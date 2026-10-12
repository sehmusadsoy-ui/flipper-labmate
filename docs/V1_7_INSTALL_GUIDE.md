# LabMate v1.7 Stable — GitHub-to-USB installer

**Published Stable:** [v1.7](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7)
with two assets, `labmate.fap` and `SHA256SUMS.txt`.
The v1.7 release keeps its **original tag/version**, but its FAP and
SHA256SUMS assets received an in-place, 4/4 device-tested PWM Studio
menu/About naming correction on 2026-10-12. Older v1.6.1/RC1 assets
and tags remain unchanged.

The released installer `scripts/install-v17-from-github.ps1` checks
the official release's tag, commit, Stable/prerelease status and SHA256,
then replaces only `/ext/apps/Tools/labmate.fap` over USB. It does
not flash firmware or intentionally delete CSV/Profile data.

- **Required:** Windows PowerShell, signed-in GitHub CLI (`gh auth login`),
  compatible local Momentum Firmware checkout (usually
  `$HOME\Momentum-Firmware`) with `scripts\toolchain\fbtenv.cmd`
  and `scripts\runfap.py`, and a USB-connected Flipper for installation.
- **Original published source tag:** `v1.7` at
  `d0e1bc6a95b257841533f0aa8745e3a79bbc8dcd` (unchanged).
- **Source of current FAP:** `0aeb0ca7ceba092c8adb6e44add0a2212cae1a74` from CI 38290044094
  (2/2 PASS, 4/4 user-reported on-device label/regression checks).
  The latest asset is a disclosed post-tag update, not a new release.
- **Current official FAP SHA256:**
  `A0B305E5FD8D71C85C51480EE06A8B7E5EBD5BEE0E82935B0ED3B7E74E7EBCEA` (supersedes `5A7CB0EAE601EEAC8856790211C4D2831A9198C31853631E1DAF0308CE724335`).
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

Change COM7 if the device uses a different port.

**Verified on actual Windows/COM7, 2026-10-12:** the operator provided
successful `-Channel Stable -VerifyOnly` output and actual
`-Channel Stable -Port COM7` execution, matching the published `v1.7`
source tag, exact official SHA256 and fixed FAP destination. USB tool
reported `Launching app` and `SUCCESS: v1.7 installed`. **Stable release
installer/USB path: PASS.** A separate post-install visual check of
`v1.7`, PWM STOP, S1 and preserved CSV files was then completed with
**4/4 PASS, user-reported, 2026-10-12**.
The verification did not modify the published release.

## 3. Device regression after install

**Post-install visual and data inspection completed:** user confirmed
**4/4 PASS (2026-10-12)**: menu/About displayed `v1.7`, initial PWM
was STOP, Profile S1 was preserved, and older History CSV files opened.
This verification was performed separately from the successful USB
installer exit. No screenshots or exported CSV were supplied for this
specific post-install check. A
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
