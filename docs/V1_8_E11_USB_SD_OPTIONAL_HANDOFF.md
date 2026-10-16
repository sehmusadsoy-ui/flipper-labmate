# LabMate v1.8 E11 — optional USB /ext file-content protection (NO SD reader)

**State 2026-10-17:** USB backup helper prepared and simulated on Windows/host.
**Not yet run on the user's actual Flipper.** No device writes are supported.
The historical 14-file LabMate PC backup and newer 10-file / 1,791-byte
live-PC copy are already preserved. The read-only COM7 survey found
57 other app-data directories; merely existing does not mean loss.

## Scope and optionality

The owner indicated that the remaining SD data is **not materially
important to them**. The full-SD backup is therefore an **optional
data-loss precaution, not a requirement to continue safe, offline
v1.8 software development**. The physical firmware trial still
requires its own approved install procedure, device rollback and
safety conditions and separate explicit owner approval. Saying
other app data is unimportant is NOT firmware flash permission.

The helper `scripts/backup_v18_e11_usb_sd_to_pc.py` connects to the
Flipper USB serial CLI and recursively inventories the visible
`/ext` filesystem. It accepts ordinary UTF-8 filenames (including
spaces and non-ASCII names), refuses unsafe/unrepresentable Windows
names, control characters, undecodable bytes, repeated/case-colliding
paths, excessive size/count/depth and broken CLI responses. It
never silently skips a file and then calls an incomplete backup
complete. Only these READ operations are issued to the Flipper:
`device_info` for CLI start, `storage list`, `storage md5`,
`storage read_chunks` with `y` read handshake. **No writes to
Flipper**. No device file names printed to the console.

- Default mode: **inventory only**. Enumerates names and remote
  MD5 screens, prints aggregate counts/size. **No new PC folder**.
- `--copy` mode: after a complete bounded inventory, creates a
  **new PC-only folder** and an INCOMPLETE marker, transfers bytes,
  compares device MD5 before and after copy, checks PC file SHA256
  after disk write, performs a second entire live directory/file
  inventory including every device MD5. Only if everything matches
  is `READ_ONLY_USB_FILE_CONTENTS_VERIFIED.txt` written and the
  incomplete marker removed. Metadata with private original
  filenames and hashes remains local in
  `PC_USB_SD_BACKUP_SHA256_MANIFEST.json` — do not post it.
- If filenames or transfer limits prevent complete coverage, it
  **refuses** and retains incomplete PC output if output was
  created. Do not restore, delete, overwrite or repeat in the
  same output directory.
- This is a **filesystem file-content backup**, not a bit-for-bit
  microSD raw image, original FAT metadata backup, boot validation
  or restore rehearsal. SHA256 is a PC-file digest verified from disk
  against the copied bytes; the Flipper side provides MD5 screening,
  not independently computed SHA256.

## Pinned operator procedure: inventory first, optional PC copy second

Close qFlipper and any other COM7 application. Flipper stays powered
and connected by USB, without removing its microSD card. This
procedure requires working Python 3 and `pyserial`.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $source = '62d73df5765169b4482f25228ed9e78723b0130e'
    $momentum = 'd3f89dfe2ef6b01839201598e9be1590cba80322'

    $work = Join-Path $env:TEMP (
        'LabMate-E11-USB-ReadOnly-' + [guid]::NewGuid().ToString('N')
    )
    $transport = Join-Path $work 'flipper'
    New-Item -ItemType Directory -Path $work | Out-Null
    New-Item -ItemType Directory -Path $transport | Out-Null
    Set-Content -LiteralPath (Join-Path $transport '__init__.py') -Value '' -Encoding ASCII

    foreach ($name in @(
        'audit_v18_e11_live_labmate_sd.py',
        'survey_v18_e11_external_sd_ro.py',
        'backup_v18_e11_usb_sd_to_pc.py'
    )) {
        $url = "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$source/scripts/$name"
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $work $name)
    }

    $url = "https://raw.githubusercontent.com/Next-Flip/Momentum-Firmware/$momentum/scripts/flipper/storage.py"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $transport 'storage.py')

    $output = Join-Path "$HOME\Downloads" (
        'LabMate-USB-FULL-SD-OPTIONAL-' + [guid]::NewGuid().ToString('N')
    )
    $args = @(
        '--port', 'COM7',
        '--momentum-scripts', $work,
        '--pc-output', $output,
        '--protected-backup', "$HOME\Downloads\LabMate-Backup-20261014-201529"
    )

    # Phase 1: only count/read /ext. DO NOT create a backup.
    py -3 (Join-Path $work 'backup_v18_e11_usb_sd_to_pc.py') @args
    if ($LASTEXITCODE -ne 0) {
        throw 'USB full SD inventory rejected safely - NO FLASH'
    }

    # Phase 2 is OPTIONAL. Run only if you actually want a complete PC copy:
    # py -3 (Join-Path $work 'backup_v18_e11_usb_sd_to_pc.py') @args --copy
    # if ($LASTEXITCODE -ne 0) { throw 'USB SD PC backup incomplete - NO FLASH' }
}
```

**Usage:** The first run is entirely read-only and shows counts/bytes.
The commented second command does not execute unless independently
enabled by the operator. The output path was generated in the
PowerShell session; if using another new PowerShell window, generate
a brand-new output path and verify inputs again. Copying a full SD
over USB may be lengthy, especially for large bundled resources;
this task is optional given the owner's stated data priorities.

## No-device verification and remaining gates

- [Real Windows no-device CI #38980845491](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38980845491):
  **SUCCESS**; 11 new synthetic USB scenarios and earlier LabMate
  backup/scope/snapshot safety checks.
- [Integrated host #38980820652](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38980820652):
  **SUCCESS** with 11 new USB scenarios and older native
  software regressions.

**Not completed:** live actual /ext USB full inventory or snapshot,
raw SD backup, reliable restore rehearsal, independent E11 firmware
safety checks, real new E11 GPIO/TIM/EXTI coexistence device tests.
Original and FAP-excluded update artifacts remain DO NOT FLASH.
Draft PR #13 remains unmerged; Stable unchanged.
