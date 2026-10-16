# LabMate v1.8 E11 — Existing device LabMate SD backup parity (READ ONLY)

**State 2026-10-17:** The software audit is built and tested. **The
operator's live Flipper inventory has not yet been captured.** Never
conflate a passed mock CI test with actual device parity.

## Scope

The single existing LabMate persistent-data directory is defined
in `src/labmate_storage_paths.h` as `/ext/apps_data/labmate`.
Earlier operator-provided evidence confirms a historical local copy
with **14 files** and an installed (read back) EXITFIX FAP SHA256
`7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.

The read-only [`audit_v18_e11_live_labmate_sd.py`](../scripts/audit_v18_e11_live_labmate_sd.py)
compares only this live LabMate data subtree against
`Downloads/LabMate-Backup-20261014-201529`. It sends only
Flipper CLI `device_info`, `storage list` and `storage md5`,
all read-only operations. It explicitly checks allowed path names,
finite serial response timeout, bounded CLI buffers, and rejects
missing/unavailable/error responses, oversized listings, symlinks
on local backup and ambiguous file names. Output is **counts only**,
no device UID, Bluetooth address or file contents.

The audit computes local MD5 and size/path in memory, never copies
or overwrites a file, never saves a report unless the user independently
redirects their terminal. MD5 + size is **a screening mechanism, NOT
an authenticated SHA256 readback**. It is not a full microSD snapshot.

## Real device procedure — proposed, not yet run

The operator must choose to run the command with qFlipper and any other
COM7 consumer closed. The pinned trusted raw scripts are downloaded
into a **brand-new PC temporary folder only**, with no overwrite of
old backups and no device modification. Python3 and `pyserial` are
required (they were previously used successfully for the installed
FAP readback). Pin the exact GitHub source SHA for the tested auditor
and independent Momentum base for the library.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $auditSource = '91e038b1aafcdc94eecdb44be926d40454a079ed'
    $momentumSource = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
    $work = Join-Path $env:TEMP ('LabMate-E11-SD-READONLY-' + [guid]::NewGuid().ToString('N'))
    $transport = Join-Path $work 'flipper'
    New-Item -ItemType Directory -Path $transport -Force:$false | Out-Null

    Invoke-WebRequest -UseBasicParsing -Uri (
        "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$auditSource/scripts/audit_v18_e11_live_labmate_sd.py"
    ) -OutFile (Join-Path $work 'audit_v18_e11_live_labmate_sd.py')

    Invoke-WebRequest -UseBasicParsing -Uri (
        "https://raw.githubusercontent.com/Next-Flip/Momentum-Firmware/$momentumSource/scripts/flipper/storage.py"
    ) -OutFile (Join-Path $transport 'storage.py')

    py -3 (Join-Path $work 'audit_v18_e11_live_labmate_sd.py') `
      --port COM7 `
      --momentum-scripts $work `
      --backup-dir "$HOME\Downloads\LabMate-Backup-20261014-201529"

    $result = $LASTEXITCODE
    if ($result -eq 2) {
        Write-Host 'LABMATE HISTORICAL BACKUP COVERAGE GAP - NO FLASH' -ForegroundColor Yellow
    } elseif ($result -ne 0) {
        throw 'READ-ONLY SD COMPARISON FAILED - NO FLASH'
    } else {
        Write-Host 'LABMATE SD MD5+SIZE SCREEN MATCH - NO FLASH' -ForegroundColor Green
    }
}
```

This exact command has not yet been executed by the device operator,
so do not mark it PASS on the Flipper. An expected **gap** is not a
software crash and must not trigger deletion or overwriting:
earlier records suggested `log_0041.csv`–`log_0049.csv` were missing
from the later live view; the auditor can confirm a count mismatch but
**cannot determine why files went missing**.

## Interpret results precisely

- `historical_files_now_absent`: old backup filenames absent on SD.
  **Preserve** the backup; never auto-restore files that could alter IDs.
- `new_device_files_not_in_backup`: SD contains later/newer files
  that an old backup cannot protect. A backup-coverage refresh plan
  would require **separate user authorization**, a new destination,
  readback/hash checks and never overriding the historical archive.
- `changed_files_not_covered_by_backup`: same path, differing
  MD5 or size; a newer Profiles generation can legitimately differ.
  Treat as not protected by historical backup, not as corruption.
- `current_data_backup_parity: MATCH` means only **size + MD5
  screening matches for the one LabMate folder**; *not* SHA256
  verification, a whole SD backup, recovery rehearsal, or firmware
  installation approval.
- If any count differs, CLI returns exit code 2 and prints
  `BACKUP COVERAGE GAP CONFIRMED`. This is a **data preservation
  decision point**, not a prompt to automatically sync files.

## Verified software evidence

- [Integrated host no-flash regression #38975922317](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38975922317)
  completed SUCCESS, and covers the new mock CLI and drift cases.
- [Native Windows mock SD model #38975922250](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38975922250)
  completed SUCCESS: 16 tests (15 passed and 1 case-collision test
  skipped because Windows NTFS cannot express distinct case-only names
  in that default folder).
- The first Windows attempt #38975686516 failed only because its
  case-collision fixture assumed a case-sensitive Windows filesystem;
  fixed with an explicit test-environment skip, **not** by ignoring
  filesystem name collisions in production logic.
- The official Flipper storage code was reviewed at exact
  Momentum source `d3f89dfe2ef6b01839201598e9be1590cba80322`.
  Its `hash_flipper()` sends `storage md5` and the auditor uses
  `storage list` to inspect names without reading full contents.
  The app's persistent folder path is pinned in production source.

**Remaining gates:** full current microSD backup parity outside
LabMate's own folder, actual SHA256 verification of current device
files where required, unattended updater impacts on user/custom
`apps_data` plugins, untried recovery and restore, the new matched
firmware/FAP physical E11 trial and separate owner approval. New split
review artifact still says `DO NOT FLASH`, PR #13 stays DRAFT;
main/Stable untouched.
