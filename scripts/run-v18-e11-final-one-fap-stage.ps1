# E11 final v1.8 FAP-only trial phase 2A: stage ONE new nonapp sidecar on Flipper.
# Explicitly approved app-only trial, but this step DOES NOT replace original.
# NEVER retry on error, remove/rename old app, touch CSV/Profile or flash firmware.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port = 'COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'qFlipper is open. Close it. No stage write performed.'
}

$newFile = Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
$oldBackup = Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
if (-not (Test-Path -LiteralPath $newFile -PathType Leaf)) {
    throw 'Pinned candidate FAP not found in Downloads; no device connection.'
}
if (-not (Test-Path -LiteralPath $oldBackup -PathType Container)) {
    throw 'Exact successful operator PC backup folder not found; no device connection.'
}
if ((Get-FileHash -LiteralPath $newFile -Algorithm SHA256).Hash -ne
        '393FE3E52AA710162A42D7299AA053F538B2EE1AD6542755CF402B83C1931B61' -or
        (Get-Item -LiteralPath $newFile).Length -ne 81528) {
    throw 'New candidate identity mismatch; no device connection.'
}

# Previously used, PASS-tested pinned Momentum H0 V3 CLI transport.
$stage = Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $stage) {
    throw 'Previously tested E11-H0 Momentum serial transport not found.'
}

# Previously operator-tested exact original E11 FULL review pair.
$oldCandidate = Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
$oldApp = Join-Path $oldCandidate 'labmate.fap'
$oldBundle = Join-Path $oldCandidate 'firmware-full-update.tgz'
if (-not (Test-Path -LiteralPath $oldApp -PathType Leaf) -or
    -not (Test-Path -LiteralPath $oldBundle -PathType Leaf)) {
    throw 'Previously tested original E11 source pair no longer present.'
}
if ((Get-FileHash -LiteralPath $oldApp -Algorithm SHA256).Hash -ne
        '2B31EC3FA9050580DC3C3FF80138578ED185D70811AA8124EBD2D00B8D981AF0' -or
    (Get-FileHash -LiteralPath $oldBundle -Algorithm SHA256).Hash -ne
        '11ED3CDF4E99C9C7218973695D349CD946BE97D21DFC59231113BDE15E94C553') {
    throw 'Original source artifacts no longer match. DO NOT STAGE.'
}

# Immutable reviewed host-mock CI stage source. No USB command until all
# candidate and old-app PC backup provenance checks have passed.
$pin = '39662e195e0aa748e12f0b5acfeb5aaf6c862f48'
$scriptsDir = Join-Path $env:TEMP ('LabMate-E11-one-FAP-stage-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scriptsDir -ErrorAction Stop | Out-Null
$names = @(
  'audit_v18_e11_live_labmate_sd.py',
  'check_v18_full_update_bundle.py',
  'preflight_v18_e11_local.py',
  'verify_v18_full_review_pair.py',
  'stage_v18_e11_review_only.py',
  'check_v18_e11_postupdate_readonly.py',
  'check_v18_e11_h_js_runtime_ro.py',
  'check_v18_e11_final_fap_prewrite_ro.py',
  'stage_v18_final_fap_on_device_one_file.py'
)
foreach ($name in $names) {
    $url = "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$pin/scripts/$name"
    $dest = Join-Path $scriptsDir $name
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $dest
    if (-not (Test-Path -LiteralPath $dest -PathType Leaf) -or
        (Get-Item -LiteralPath $dest).Length -eq 0) {
        throw "Missing pinned one-FAP staging helper $name"
    }
}

Write-Host 'E11 FINAL v1.8 - LIMITED FAP STAGING ONLY' -ForegroundColor Cyan
Write-Host 'Stop/exit LabMate, unplug all GPIO wires, close qFlipper and other serial software.'
Write-Host 'One SD write path allowed: /ext/apps/Tools/labmate.e11-new-stage'
Write-Host 'Original /ext/apps/Tools/labmate.fap will not be removed or renamed.'
Write-Host 'No firmware, JS plugin, Manifest, CSV or Profiles write.'
Write-Host 'On error: STOP. No second attempt, no automatic cleanup.' -ForegroundColor Yellow
$argv = @(
    '-3',(Join-Path $scriptsDir 'stage_v18_final_fap_on_device_one_file.py'),
    '--port',$Port,
    '--momentum-scripts',$stage.FullName,
    '--old-candidate',$oldCandidate,
    '--saved-old-fap-backup',$oldBackup,
    '--new-fap',$newFile
)
& py @argv
if ($LASTEXITCODE -ne 0) {
    throw 'E11 FINAL FAP STAGE FAILED; DO NOT RETRY/RENAME/DELETE ANYTHING.'
}
Write-Host 'E11 FINAL ONE-FAP STAGE VERIFIED - ORIGINAL APP UNCHANGED' -ForegroundColor Green
Write-Host 'STOP HERE. No active application replacement was performed.' -ForegroundColor Yellow
