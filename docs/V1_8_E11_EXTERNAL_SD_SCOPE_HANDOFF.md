# LabMate v1.8 E11 — OTHER microSD scope survey (strict READ ONLY)

**Status 2026-10-17:** labmate-only preservation PASSED on the operator's
real device: 10 live files / 1,791 B copied to PC and checked, while
the 14 historical LabMate backup files were kept intact. This DOES NOT
cover all other microSD folders, other applications or their settings.

**Question this probe answers:** Does the Flipper currently have non-LabMate
`/ext/apps_data` top-level folders and other application resources
that are outside the existing LabMate-only snapshot? It does NOT
prove any file is corrupted/changed/deleted, backed up or recoverable.

The FULL E11 firmware update resources comparison vs official MNTM-012
has 2,150 old vs 2,116 new files, with 20 additions, 54 removals,
382 modifications and 126 changes in non-JS-plugin
`apps_data/` resource paths. These describe BUNDLED UPDATER
resource files, not a full inventory of the user's actual microSD.
The separately staged FAP-removed updater remains **DO NOT FLASH**.

## Strict read-only top-level-only survey

[`scripts/survey_v18_e11_external_sd_ro.py`](../scripts/survey_v18_e11_external_sd_ro.py)
reads **only three fixed CLI directory lists**:

- `/ext` (root, to confirm presence of applications/data roots)
- `/ext/apps` (one-level entries only)
- `/ext/apps_data` (one-level entries only)

It NEVER recurses into private directories, computes device MD5,
reads file bodies, copies or erases any SD file, installs or flashes
anything. This is just a count exposure assessment. The output omits
all user filenames and app/plugin folder names, including potentially
private paths; it prints counts and `NO` for full snapshot, restore
and firmware authorization. The script fail-closes unrecognized
listings, missing standard roots, path tricks and collisions,
unbounded responses and timeouts.

**Read-only parser safety correction (after first actual device attempt):**
The user executed the original COM7 scope survey and received
`E11 EXTERNAL SD SURVEY REFUSED - NO DEVICE WRITE:
unsafe/ambiguous SD member name`. No scope counts were produced,
and no SD data was changed. The earlier survey incorrectly reused
the strict LabMate *backup filename* parser on all other apps,
which may have names containing spaces, multiple dots or
non-ASCII raw bytes. The exact offending private name is
**not known** and should not be printed or guessed.

The corrected **top-level-count-only** parser uses opaque raw bytes
for names (no Unicode decoding, path building or subsequent commands
based on names), recognizes only the exact Momentum
`[D] name` and `[F] name <decimal>b` CLI grammar, and
compares only the public fixed literal roots `apps`,
`apps_data`, `labmate` in memory. It continues to refuse malformed
CLI output, unsupported byte counts, separators/control bytes, names
over 255 bytes, or ASCII-case collisions, with sanitized errors
naming **only** the hardcoded directory that failed. This approach
preserves strict LabMate backup path validation separately.
No app data, private names or file contents are printed.

**Corrected verified CI after the parser update:**
[Windows #38978962924](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38978962924)
**SUCCESS** — 14 new survey tests including Unicode/space/dots and
negative privacy/path tests, plus 19 existing read-only listing
tests (one NTFS fixture skip) and 9 PC snapshot tests.
[Integrated Linux host #38978962925](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38978962925)
**SUCCESS** at pinned source
`1da7dab93cfd72d94b243c3f5732ded9f8e26e5d`.

**Host tests, NOT real operator SD evidence:**
[Windows synthetic no-device workflow #38978402213](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38978402213)
**SUCCESS** with 10 mock survey tests, alongside existing 19 listing
and 9 snapshot mocks; [integrated host
#38978387190](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38978387190)
**SUCCESS** on the same new survey model. No private SD card was read
by CI. New script/test pin is
`1da7dab93cfd72d94b243c3f5732ded9f8e26e5d`.

## Operator procedure — not yet executed

Close qFlipper and other COM7 programs. Retain the existing
10-file current snapshot and 14-file historical LabMate backup.
With Flipper USB on COM7, use this exact single PowerShell block.
All downloaded scripts go to a newly named PC TEMP folder; no old
local files are overwritten.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $source = '1da7dab93cfd72d94b243c3f5732ded9f8e26e5d'
    $momentum = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
    $work = Join-Path $env:TEMP ('LabMate-E11-SDScope-' + [guid]::NewGuid().ToString('N'))
    $transport = Join-Path $work 'flipper'
    New-Item -ItemType Directory -Path $work | Out-Null
    New-Item -ItemType Directory -Path $transport | Out-Null
    Set-Content -LiteralPath (Join-Path $transport '__init__.py') -Value '' -Encoding ASCII

    foreach ($name in @(
        'audit_v18_e11_live_labmate_sd.py',
        'survey_v18_e11_external_sd_ro.py'
    )) {
        $url = "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$source/scripts/$name"
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $work $name)
    }
    $url = "https://raw.githubusercontent.com/Next-Flip/Momentum-Firmware/$momentum/scripts/flipper/storage.py"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $transport 'storage.py')

    py -3 (Join-Path $work 'survey_v18_e11_external_sd_ro.py') `
        --port COM7 `
        --momentum-scripts $work

    if ($LASTEXITCODE -ne 0) {
        throw 'NON-LABMATE SD READ-ONLY SURVEY REFUSED - NO FLASH'
    }
    Write-Host 'E11 SD SCOPE SURVEY COMPLETED - NO FLASH' -ForegroundColor Green
}
```

## Interpret and preserve data

`apps_data_OTHER_directories > 0` or
`apps_data_top_level_files > 0` means existing app data lies
OUTSIDE the two independently preserved LabMate PC copies.
Even a zero count at this top level does not constitute a full card
inventory or copy; app files and other SD root folders remain.

After this read-only coverage diagnosis, arrange a **separate,
verified, fresh FULL microSD filesystem copy** using a dedicated
SD-card reader or an independently vetted read-only transfer method
before considering a firmware maintenance trial. A future backup
must go into a NEW PC directory on a different disk, preserve existing
copies, include hidden and ordinary file tree entries, verify file
count and source/destination SHA256, and avoid auto-restoring anything.
If equipment is unavailable, hold firmware test rather than asserting
FULL microSD PASS. Do not use the qFlipper *settings-only* TGZ as if
it were a full microSD clone.

**Still blocked after this survey:** full SD integrity/backup,
other-app/plugin compatibility, recovery/restore rehearsal,
full updater authorization and actual E11 GPIO/TIM/EXTI physical tests.
Stable/main untouched; PR #13 draft.


## 2026-10-17 — Actual operator COM7 top-level SD scope survey PASS

**Real, not simulated:** the operator executed the corrected source
`1da7dab93cfd72d94b243c3f5732ded9f8e26e5d` via COM7 and pasted:

```
survey_scope: ONLY /ext, /ext/apps, /ext/apps_data TOP LEVEL
ext_directories: 27
ext_top_level_files: 1
apps_directories: 14
apps_top_level_files: 0
apps_data_labmate_folder_present: YES
apps_data_OTHER_directories: 57
apps_data_top_level_files: 0
non_labmate_content_potentially_outside_existing_snapshot: YES
whole_sd_inventory_completed: NO
whole_sd_snapshot_verified: NO
non_labmate_sd_files_backed_up: NO
restore_rehearsed: NO
E11_firmware_write_authorized: NO
E11 NON-LABMATE SD TOP-LEVEL SURVEY ONLY - NO FLASH
E11 SD SCOPE SURVEY COMPLETED - NO FLASH
```

**Classification: top-level directory exposure SURVEY PASS, whole-SD
backup still FAIL/OPEN.** The `/ext` root contains 27
directories and one file. `/ext/apps` has 14 directories, no
top-level files. `/ext/apps_data` contains LabMate plus **57 other
application data directories**, no files at its top level. This is
NOT a recursive count; file contents, sizes, custom application
preservation and restore have NOT been checked.

The existing PC-verified 14 historical + 10 current LabMate files
do not protect the other 57 `apps_data` directories or remaining
microSD content. Do not infer corruption/changes from the mere
existence of other directories. Real Flipper device files were
**NOT modified** by the read-only survey, and original and
FAP-excluded firmware bundles remain **DO NOT FLASH**.

**Next safeguarding step:** optional, separate computer-side
full-root filesystem snapshot using a properly ejected microSD
and dedicated reader, to a brand-new PC folder. Include hidden
and nested content and verify source/destination bytes/hashes and
the manifest. If no reader is available, mark full-SD backup
DEFERRED rather than pretending this scope survey is enough.
