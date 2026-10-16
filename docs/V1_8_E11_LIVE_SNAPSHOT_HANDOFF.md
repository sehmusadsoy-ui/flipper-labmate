# LabMate v1.8 E11 — Preserve CURRENT LabMate data on PC (NO FLASH)

**Status 2026-10-17:** Actual read-only on-device COM7 file-inventory
audit completed. **BACKUP COVERAGE GAP**, NOT PASS.
A new PC-only readback snapshot tool is developed/tested, but has
**NOT yet been executed on the operator's actual device**.

## Why a separate new snapshot is mandatory

The existing 2026-10-14 LabMate backup has **14 files**, while the
current device has **10 files** under the production
`/ext/apps_data/labmate` path. Current screening finds
**3 same-path+size+MD5 matches, 9 historical file paths absent
from the live device, 5 new live paths not in old backup and 2
changed overlapping paths**. The exact names were not emitted by
the existing comparison. It is not evidence of the cause of loss,
nor authorization to restore or delete anything.

Preserve BOTH independent states:
- Historical 14-file local folder backup (never overwrite, delete
  or automatically restore any old CSV/profiles).
- Actual 10 live LabMate SD files, each backed up to its own new
  **PC-only** output folder with byte readback checks.

qFlipper settings-only TGZ (14 files/1 directory) and a historical
MNTM-012 updater are NOT substitutes for either user data copy.

## Readback method (ONLY Flipper reads, PC file writes)

[`scripts/snapshot_v18_e11_live_labmate_sd.py`](../scripts/snapshot_v18_e11_live_labmate_sd.py)
works with the exact pinned official Momentum storage library.
It checks the historical directory and uses CLI `device_info`,
`storage list` and `storage md5` plus **`storage read_chunks`
read-only transfers**; `y` is the reply to an existing read-only
chunk handshake, not an SD write. It caps file and total transfer
size, compares every received file length+MD5 to the initial live
listing and independently calculates SHA256 on each written PC
file. It re-lists and re-hashes the live data after the copy, so
a concurrent on-device change is detected.

This writes files under a **brand-new**, operator-selected
PC destination ONLY; pre-existing output paths and paths overlapping
the historical backup are rejected. An interrupted or failed PC
snapshot folder retains `INCOMPLETE-DO-NOT-RESTORE.txt` and is
not accepted. After all checks it writes
`PC_SNAPSHOT_MANIFEST.json` (local names and hashes, **do not
post its private contents**) and
`READ_ONLY_SNAPSHOT_VERIFIED.txt`, removes the incomplete marker
and prints ONLY counts/byte totals.

This does NOT create an image of the entire microSD and does not
prove post-upgrade restore. The known previous 9 absent device
files remain preserved in the historical copy, without
automatically merging into the active LabMate history.

## Source-pinned Windows command (not yet operator-run)

Close qFlipper and all other COM7 sessions. Python 3 and pyserial
are required. PowerShell, single block:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $source = 'ad7ac88e9817b8a64f0b8d1aaa3235056bb2c82c'
    $momentum = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
    $work = Join-Path $env:TEMP (
        'LabMate-E11-LiveSnapshot-' + [guid]::NewGuid().ToString('N')
    )
    $transport = Join-Path $work 'flipper'
    $output = Join-Path "$HOME\Downloads" (
        'LabMate-LiveSnapshot-20261017-' + [guid]::NewGuid().ToString('N')
    )
    New-Item -ItemType Directory -Path $work | Out-Null
    New-Item -ItemType Directory -Path $transport | Out-Null
    Set-Content -LiteralPath (Join-Path $transport '__init__.py') -Value '' -Encoding ASCII

    foreach ($name in @(
        'audit_v18_e11_live_labmate_sd.py',
        'snapshot_v18_e11_live_labmate_sd.py'
    )) {
        $url = "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$source/scripts/$name"
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $work $name)
    }

    $url = "https://raw.githubusercontent.com/Next-Flip/Momentum-Firmware/$momentum/scripts/flipper/storage.py"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $transport 'storage.py')

    py -3 (Join-Path $work 'snapshot_v18_e11_live_labmate_sd.py') `
        --port COM7 `
        --momentum-scripts $work `
        --historical-backup "$HOME\Downloads\LabMate-Backup-20261014-201529" `
        --output $output

    if ($LASTEXITCODE -ne 0) {
        throw 'CURRENT LABMATE PC SNAPSHOT FAILED - NO FLASH'
    }

    Write-Host "CURRENT LABMATE SNAPSHOT VERIFIED - PC ONLY: $output" -ForegroundColor Green
}
```

**Never run `send`, `format_ext`, `remove`, `restore` or a
firmware installer** as part of this step. If a snapshot fails,
retain the original historical backup and any incomplete new
folder as-is; identify the specific failure and plan a separate,
new destination for a retry. The first real device result must
be captured before calling this data preservation step PASS.

## Software evidence

- [Integrated host #38977160159](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38977160159):
  **SUCCESS**, includes the new PC snapshot safety test module.
- [Windows mock CLI + snapshot #38977176906](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38977176906):
  **SUCCESS**, 19 prior parse/audit tests (18 PASS, one
  NTFS-only test skipped) and 9 PC snapshot adversarial/positive
  tests PASS. No device, flash or real user data touched.

**Release gate:** Snapshot scope is LabMate's own active data subtree
only; third-party `apps_data`, global SD card, recovery/restore
rehearsal and new E11 firmware resource physical compatibility
remain OPEN. The existing E11 review artifacts remain
**DO NOT FLASH**; PR #13 DRAFT; main/Stable unchanged.


## 2026-10-17 — Operator completed real 10-file PC-only readback

**REAL DEVICE RESULTS — operator PowerShell terminal**:

```
snapshot_files_verified: 10
snapshot_file_bytes: 1791
new_device_files_preserved: 5
changed_device_files_preserved: 2
historical_files_not_on_device: 9
old_backup_preserved: YES
flipper_files_modified: NO
snapshot_full_microSD: NO
restore_rehearsed: NO
firmware_flash_authorized: NO
LIVE LABMATE PC READBACK SNAPSHOT VERIFIED - NO FLASH / NO RESTORE
CURRENT LABMATE SNAPSHOT VERIFIED - PC ONLY
```

**This supersedes the above operator-pending status**: current
LabMate-only 10-file snapshot **PASS** with 1,791 bytes copied to
a new Windows local folder and locally re-read SHA256 verification.
The previous historical 14-file folder is preserved separately,
including historical files not currently found on the Flipper;
there was **no restore, merge, delete, overwrite, firmware flash or
FAP install**. Both copies should be kept intact. The exact
randomized new Windows folder name was not emitted in the posted
short transcript; the operator can locate it among
`Downloads/LabMate-LiveSnapshot-*`, including
`PC_SNAPSHOT_MANIFEST.json` and
`READ_ONLY_SNAPSHOT_VERIFIED.txt`.

**Still NOT PROVEN**: independent SHA256 directly computed by
the Flipper firmware, complete non-LabMate microSD content
preservation, independent restore rehearsal, installed
firmware identity, new E11 live ownership/refusal tests. The
formal firmware installation decision remains **NO-GO**.
