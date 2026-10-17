# LabMate E11 final FAP activation (OPERATOR EXPLICITLY APPROVED 2026-10-17).
# Device scope ONLY two same-dir protected renames; NOT firmware or Stable.
# DO NOT automatically retry. On any fail leave old PC backup untouched.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port='COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'qFlipper is open. Close it first. NO DEVICE ACTION.'
}

$newFile=Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
$oldBackup=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
$oldCandidate=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
$oldSource=Join-Path $oldCandidate 'labmate.fap'
$oldBundle=Join-Path $oldCandidate 'firmware-full-update.tgz'
$oldFile=Join-Path $oldBackup 'installed_E11_v18DEV_before_final_label.fap'
$report=Join-Path $oldBackup 'PREWRITE_READONLY_REPORT.json'
$marker=Join-Path $oldBackup 'READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt'
foreach($p in @($newFile,$oldSource,$oldBundle,$oldFile,$report,$marker)) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        throw "Expected immutable original file missing. NO DEVICE ACTION: $p"
    }
}
$expectedOld='2B31EC3FA9050580DC3C3FF80138578ED185D70811AA8124EBD2D00B8D981AF0'
$expectedNew='393FE3E52AA710162A42D7299AA053F538B2EE1AD6542755CF402B83C1931B61'
$expectedBundle='11ED3CDF4E99C9C7218973695D349CD946BE97D21DFC59231113BDE15E94C553'
if ((Get-FileHash -LiteralPath $oldFile -Algorithm SHA256).Hash -ne $expectedOld -or
    (Get-Item -LiteralPath $oldFile).Length -ne 81532 -or
    (Get-FileHash -LiteralPath $oldSource -Algorithm SHA256).Hash -ne $expectedOld -or
    (Get-FileHash -LiteralPath $newFile -Algorithm SHA256).Hash -ne $expectedNew -or
    (Get-Item -LiteralPath $newFile).Length -ne 81528 -or
    (Get-FileHash -LiteralPath $oldBundle -Algorithm SHA256).Hash -ne $expectedBundle) {
    throw 'Original E11/FAP candidate hash/size changed. NO DEVICE ACTION.'
}
$r=Get-Content -LiteralPath $report -Raw -ErrorAction Stop | ConvertFrom-Json
if ($r.installed_old_fap_sha256 -ne $expectedOld -or
    $r.target_candidate_fap_sha256 -ne $expectedNew -or
    $r.installed_old_fap_bytes -ne 81532 -or
    $r.live_identity_fap_md5_verified_twice -ne $true -or
    $r.live_native_js_and_manifest_md5_verified_twice -ne $true -or
    $r.device_write -ne $false -or
    $r.firmware_flash -ne $false -or
    $r.installation_performed -ne $false -or
    $r.stable_release_approved -ne $false) {
    throw 'Original device FAP PC backup report invalid. NO DEVICE ACTION.'
}

$h0=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Previously vetted H0 V3 transport missing. NO DEVICE ACTION.' }

# All Python safety routines were independently host-mocked at this immutable ref.
$pin='086275b82205ad16750fca893e6aa66300f985b4'
$dir=Join-Path $env:TEMP ('LabMate-E11-final-two-renames-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dir -ErrorAction Stop | Out-Null
$names=@(
    'audit_v18_e11_live_labmate_sd.py',
    'check_v18_full_update_bundle.py',
    'preflight_v18_e11_local.py',
    'verify_v18_full_review_pair.py',
    'stage_v18_e11_review_only.py',
    'check_v18_e11_postupdate_readonly.py',
    'check_v18_e11_h_js_runtime_ro.py',
    'check_v18_e11_final_fap_prewrite_ro.py',
    'stage_v18_final_fap_on_device_one_file.py',
    'prepare_v18_e11_phase2b_safe_promote.py'
)
foreach($name in $names) {
    $out=Join-Path $dir $name
    $url="https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$pin/scripts/$name"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $out -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $out -PathType Leaf) -or
        (Get-Item -LiteralPath $out).Length -eq 0) {
        throw "Required pinned phase2B source missing: $name"
    }
}
Write-Host ''
Write-Host 'E11 FINAL PHASE 2B - TWO PINNED SAME-DIR SAFE RENAMES ONLY' -ForegroundColor Cyan
Write-Host 'LabMate fully exited; PWM STOP; all GPIO wires removed; qFlipper closed.'
Write-Host 'FIRST /ext/apps/Tools/labmate.fap -> /ext/apps/Tools/labmate.e11-pre-final.bak'
Write-Host 'SECOND /ext/apps/Tools/labmate.e11-new-stage -> /ext/apps/Tools/labmate.fap'
Write-Host 'IMPORTANT: LabMate may temporarily be absent between the two renames.'
Write-Host 'Never reboot, rerun, auto-restore, delete or flash on unexpected results.' -ForegroundColor Yellow
Write-Host 'This does not update native JS, Manifest, firmware, CSV, Profiles or other apps.'
Write-Host ''
$arguments=@(
  '-3',(Join-Path $dir 'prepare_v18_e11_phase2b_safe_promote.py'),
  '--port',$Port,
  '--momentum-scripts',$h0.FullName,
  '--old-candidate',$oldCandidate,
  '--saved-old-fap-backup',$oldBackup,
  '--new-fap',$newFile
)
& py @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'E11 2B NO-GO. STOP; do not rerun or attempt manual recovery.'
}
Write-Host 'E11 PHASE 2B FILE PROMOTION VERIFIED - DEVICE GUI NOT YET TESTED' -ForegroundColor Green
Write-Host 'STOP HERE. Share output BEFORE launching final LabMate.' -ForegroundColor Yellow
