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

**Host tests, NOT real operator SD evidence:**
[Windows synthetic no-device workflow #38978402213](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38978402213)
**SUCCESS** with 10 mock survey tests, alongside existing 19 listing
and 9 snapshot mocks; [integrated host
#38978387190](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38978387190)
**SUCCESS** on the same new survey model. No private SD card was read
by CI. New script/test pin is
`f63938bf0af57495289e037dea942c12f9ff39fd`.

## Operator procedure — not yet executed

Close qFlipper and other COM7 programs. Retain the existing
10-file current snapshot and 14-file historical LabMate backup.
With Flipper USB on COM7, use this exact single PowerShell block.
All downloaded scripts go to a newly named PC TEMP folder; no old
local files are overwritten.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $source = 'f63938bf0af57495289e037dea942c12f9ff39fd'
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
