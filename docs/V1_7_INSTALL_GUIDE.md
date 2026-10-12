# LabMate v1.7 — checksum-verified GitHub-to-USB installer

The self-contained Windows script `scripts/install-v17-from-github.ps1`
selects a **published** release, checks tag/release provenance, downloads
`labmate.fap` and `SHA256SUMS.txt`, verifies SHA256, and updates
only `/ext/apps/Tools/labmate.fap` on the connected Flipper using local
Momentum firmware tools. It never downloads new firmware, replaces MCU
firmware or intentionally modifies stored profiles/CSV records.

**Requirements:** Windows PowerShell, GitHub CLI (`gh`) signed in with
`gh auth login`, compatible local Momentum firmware checkout with
`scripts/toolchain/fbtenv.cmd` and `scripts/runfap.py`, connected Flipper.

## Currently available: v1.7 RC1 pre-release

Use one PowerShell line (change COM7 if your port differs):

```powershell
$p="$env:TEMP\labmate-v17-install.ps1"; Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/v1.7-stable-candidate/scripts/install-v17-from-github.ps1" -OutFile $p; powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p -Channel RC1 -Port COM7
```

Verify without installing: append `-VerifyOnly`.

## Future channel: v1.7 Stable (NOT YET PUBLISHED)

When the official `v1.7` non-prerelease release exists, run the same
script with `-Channel Stable`. Until then it must refuse to install from
a missing Stable release. No development-branch FAP is silently substituted.

Before executing a downloaded script, review its source. For production,
use the immutable final Stable tag rather than a moving candidate-branch
URL. A final, tag-pinned command will be provided at Stable publication.

Installer updates a single FAP path; it will not create an additional
Tools app entry. Independently back up important records before maintenance.
