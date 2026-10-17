# LabMate E11 final v1.8: ONE-SHOT append ONLY into existing, exact EMPTY non-app sidecar.
# Old LabMate FAP, SD user data and firmware are never an upload destination.
# No delete/rename/restart/recovery or automatic retry on any failure.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port='COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'Close qFlipper. STOP; no device write.'
}
$newFile=Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
$oldBackup=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
$oldCandidate=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'

$oldFile=Join-Path $oldBackup 'installed_E11_v18DEV_before_final_label.fap'
$oldBundle=Join-Path $oldCandidate 'firmware-full-update.tgz'
$oldSource=Join-Path $oldCandidate 'labmate.fap'
foreach($p in @($newFile,$oldFile,$oldBundle,$oldSource,
                (Join-Path $oldBackup 'PREWRITE_READONLY_REPORT.json'),
                (Join-Path $oldBackup 'READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt'))) {
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) {
        throw "Missing exact local candidate/backup: $p"
    }
}
$goodOld='2B31EC3FA9050580DC3C3FF80138578ED185D70811AA8124EBD2D00B8D981AF0'
$goodNew='393FE3E52AA710162A42D7299AA053F538B2EE1AD6542755CF402B83C1931B61'
if ((Get-FileHash -LiteralPath $oldFile -Algorithm SHA256).Hash -ne $goodOld -or
    (Get-FileHash -LiteralPath $oldSource -Algorithm SHA256).Hash -ne $goodOld -or
    (Get-Item -LiteralPath $oldFile).Length -ne 81532 -or
    (Get-FileHash -LiteralPath $newFile -Algorithm SHA256).Hash -ne $goodNew -or
    (Get-Item -LiteralPath $newFile).Length -ne 81528 -or
    (Get-FileHash -LiteralPath $oldBundle -Algorithm SHA256).Hash -ne
      '11ED3CDF4E99C9C7218973695D349CD946BE97D21DFC59231113BDE15E94C553') {
    throw 'Local old E11/new final FAP/bundle fingerprint mismatch. NO DEVICE ACTION.'
}
$h0=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Original tested H0 V3 native transport not found. NO DEVICE ACTION.' }

# Corrected Ready-first code, exact zero-sidecar, chunk-by-chunk checks, 10 host tests.
$pin='3aff361687d57e11dae8b0a7c2cc989bb1ad8d02'
$path=Join-Path $env:TEMP ('LabMate-v18-verified-EMPTY-only-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $path -ErrorAction Stop | Out-Null
$sources=@(
  'audit_v18_e11_live_labmate_sd.py',
  'check_v18_full_update_bundle.py',
  'preflight_v18_e11_local.py',
  'verify_v18_full_review_pair.py',
  'stage_v18_e11_review_only.py',
  'check_v18_e11_postupdate_readonly.py',
  'check_v18_e11_h_js_runtime_ro.py',
  'check_v18_e11_final_fap_prewrite_ro.py',
  'stage_v18_final_fap_on_device_one_file.py',
  'resume_v18_final_fap_from_empty_stage_once.py'
)
foreach($name in $sources) {
    $dest=Join-Path $path $name
    $uri="https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$pin/scripts/$name"
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $dest -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $dest -PathType Leaf) -or
        (Get-Item -LiteralPath $dest).Length -eq 0) {
        throw "Immutable one-shot source missing: $name"
    }
}
Write-Host 'E11 FINAL STAGE FROM VERIFIED EMPTY SIDE-CAR ONLY' -ForegroundColor Cyan
Write-Host 'LabMate must be exited, PWM stopped, all GPIO wires disconnected, qFlipper closed.'
Write-Host 'Allowed SD write: existing /ext/apps/Tools/labmate.e11-new-stage only.'
Write-Host 'Must be STILL 0 bytes and MD5 of empty file. Stage is non-.fap extension.'
Write-Host 'Old active LabMate, other apps, logs, profiles, native resources NEVER touched.'
Write-Host 'Any failure: STOP. DO NOT RETRY, REMOVE, RENAME, RESET OR FLASH.' -ForegroundColor Yellow
$pyArgs=@(
  '-3',(Join-Path $path 'resume_v18_final_fap_from_empty_stage_once.py'),
  '--port',$Port,
  '--momentum-scripts',$h0.FullName,
  '--old-candidate',$oldCandidate,
  '--saved-old-fap-backup',$oldBackup,
  '--new-fap',$newFile
)
& py @pyArgs
if ($LASTEXITCODE -ne 0) {
    throw 'E11 ZERO-SIDECAR STAGE NOT VERIFIED. STOP. Do not retry.'
}
Write-Host 'E11 VERIFIED NON-APP FAP SIDE-CAR COMPLETE; ORIGINAL APP UNCHANGED.' -ForegroundColor Green
Write-Host 'STOP HERE. FINAL APP RENAME/PROMOTION NOT EXECUTED.' -ForegroundColor Yellow
