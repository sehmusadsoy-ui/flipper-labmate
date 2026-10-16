# LabMate v1.8 E11 — full microSD file-content preservation gate

**Status 2026-10-17: OFFLINE TOOL CI PASS; REAL FULL-SD PC COPY NOT YET DONE.**
This is a preservation plan, **NOT a firmware update instruction**.
Working installed EXITFIX must remain untouched. Do not merge draft PR #13.

## Why this gate exists (real operator evidence)

A read-only COM7 survey of the actual card on 2026-10-17 reported:

| Root | Subdirectories | Top-level files |
| --- | ---: | ---: |
| /ext | 27 | 1 |
| /ext/apps | 14 | 0 |
| /ext/apps_data | 58 (LabMate + 57 others) | 0 |

The earlier 14-file historical LabMate data backup and successful
10-file/1,791-byte current LabMate PC snapshot cover
**ONLY /ext/apps_data/labmate**. These two copies are separately
preserved and must NOT be overwritten, deleted, restored or merged.
The **other 57 apps_data directories** and remaining SD root
entries are not included in LabMate-only protection. Static E11
update resource comparison also found 126 changed other
bundled apps_data resource paths; this is **not evidence that real
user data was changed**, but it makes preserving the actual card
before a full Momentum updater especially important.

## Preferred scope: full content from physically removed card

This procedure requires a separate microSD card reader connected to
the Windows PC. **Do not remove a card from a running device.**
End LabMate activity and any logging; stop the Flipper normally,
disconnect USB and ensure device is powered off before removing
the card. Do not format the card if Windows suggests repair/format;
cancel the prompt and keep the card unchanged. The owner must
independently verify the removable SD drive letter in File Explorer
and confirm it contains the expected Flipper folders
\`apps\` and \`apps_data/labmate\`.

**Crucial:** the card must be mounted by Windows to read its
filesystem. The Python tool opens source files READ-ONLY, but
ordinary Windows mounting may update filesystem metadata. Thus
this procedure cannot claim forensic *zero writes at the block
device level* or a bit-for-bit FAT image. For strict physical
write protection a real hardware write-blocker and separately
verified disk imaging process are necessary. This guide only
protects FILE CONTENTS by source/destination SHA256 checks.

### New bounded PC-only tool

[\`scripts/backup_v18_e11_sd_reader_to_pc.py\`](../scripts/backup_v18_e11_sd_reader_to_pc.py)
only reads from the explicit source drive root (\`E:\` is an
**EXAMPLE**, not an asserted real drive letter), and writes to
an unoccupied/new **different-drive** PC folder. It will never
send Flipper CLI commands and has no firmware, USB, serial or
restore functionality. It refuses:

- An unspecified, system or non-drive-root source path;
  a destination on the same drive; existing output directories;
  overlapping source/output trees; symlinks, junctions, NTFS
  reparse points and special filesystem entries.
- Non-Flipper roots that lack \`apps\` or \`apps_data/labmate\`,
  missing directory/file entries, ambiguous case-fold collisions,
  unsafe oversize/total-file counts, insufficient PC disk space,
  or source size/content changes during copying.

It enumerates recursively, including hidden file names and empty
directories, reads every source file in streaming chunks, writes
each PC file **exclusively** without overwrite, checks source and
PC SHA256 against copied bytes, then scans the source again and
re-hashes **both source and destination** to detect drift.
The PC-only output includes a local manifest with file paths,
file sizes and SHA256 hashes. **Do not post this manifest in
GitHub or chat**, since it can contain personal filenames.

Interrupted copies deliberately keep
\`INCOMPLETE-DO-NOT-RESTORE.txt\`; never report PASS or erase the
partial folder. Only a verified copy prints
\`E11 FULL SD FILE-CONTENT PC BACKUP VERIFIED - NO FLASH / NO RESTORE\`
and gets \`READ_ONLY_PC_FILE_SNAPSHOT_VERIFIED.txt\`.

### Operator PowerShell template — run ONLY after identifying card drive

Use File Explorer to inspect the real inserted card and replace
\`E:\` below with its independently established drive letter. It
must NOT be the Windows system drive or the drive used for the
new backup folder. Nothing is written to the Flipper by the
Python script. The source physical card must remain connected
until the final verification. A brand-new PC output folder is
generated automatically.

\`\`\`powershell
& {
    $ErrorActionPreference = 'Stop'
    $sourceCode = 'TO_BE_PINNED_AFTER_FINAL_CI'
    $sdDrive = 'E:\'  # EXAMPLE ONLY: confirm actual SD card reader drive!
    $work = Join-Path $env:TEMP ('LabMate-E11-FullSD-' + [guid]::NewGuid().ToString('N'))
    $output = Join-Path "$HOME\Downloads" (
        'LabMate-FULL-SD-PC-20261017-' + [guid]::NewGuid().ToString('N')
    )
    New-Item -ItemType Directory -Path $work | Out-Null

    $url = "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$sourceCode/scripts/backup_v18_e11_sd_reader_to_pc.py"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (
        Join-Path $work 'backup_v18_e11_sd_reader_to_pc.py'
    )

    py -3 (Join-Path $work 'backup_v18_e11_sd_reader_to_pc.py') 
        --source-drive $sdDrive 
        --pc-output $output

    if ($LASTEXITCODE -ne 0) {
        throw 'FULL SD PC FILE BACKUP NOT VERIFIED - NO FLASH'
    }
    Write-Host 'FULL SD PC FILE-CONTENT COPY VERIFIED - NO FLASH' -ForegroundColor Green
}
\`\`\`

**This is a documentation template, not a ready-to-run command.**
Pin \`sourceCode\` to the final tested commit before invoking and
correct PowerShell continuation characters as appropriate.
Do not guess the drive letter or run it against the Flipper
virtual/COM device (requires a *physical* card reader). If a
reader is unavailable, record full-card backup as **DEFERRED**.
The tool should not be used on a card with suspected filesystem
damage without first selecting an independent recovery procedure.

## What passing WOULD and WOULD NOT mean

Potential PASS: all **files and directories visible to the Windows
mounted filesystem** copied to a separate new PC folder, file counts
and independent SHA256 comparisons match, original LabMate copies
still preserved. This is more complete than qFlipper's settings
archive, the 10-file LabMate copy or this turn's root-only survey.

Still OPEN even after file-content PASS: raw unallocated blocks,
FAT allocation/creation metadata and SD hidden system structures;
Flipper firmware startup and radio/option-byte risk; an actual
verified restore (which would be a separate authorized test);
third-party plugin/firmware API compatibility and the new E11
GPIO/TIM1/TIM2/EXTI physical interaction tests. Original FULL
and FAP-excluded update artifacts remain marked **DO NOT FLASH**.

**No automatic restore, erase, format, app install, firmware flash
or Stable promotion has been authorized or performed.**
