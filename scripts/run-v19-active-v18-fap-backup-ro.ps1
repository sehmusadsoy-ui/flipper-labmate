# LabMate v1.9 PRETRIAL: BACK UP LIVE final v1.8 app to NEW PC folder ONLY.
# Never write, rename, delete, flash, recover or launch apps on Flipper.
# Files are loaded only from local authenticated Git checkout, then checked
# against exact Git blobs from the E11 reviewed code and current v1.9 helper.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port = 'COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'Close qFlipper before the read-only COM check. NO DEVICE WRITE.'
}

$old=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
$saved=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
$final=Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
$backupRoot=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups'
if (-not (Test-Path -LiteralPath $old -PathType Container) -or
    -not (Test-Path -LiteralPath $saved -PathType Container) -or
    -not (Test-Path -LiteralPath $final -PathType Leaf) -or
    -not (Test-Path -LiteralPath $backupRoot -PathType Container)) {
    throw 'Existing final v1.8 / original E11 files or PC backup directory missing. NO COM ACTION.'
}

$h0=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Previously trusted E11 CLI transport not found. NO COM ACTION.' }

$expectedBlobs=@{
  'audit_v18_e11_live_labmate_sd.py'='44f4892493a173cad8436da1c622ae8c00d6ae66'
  'check_v18_full_update_bundle.py'='fdd44261af8907c943107a1f6d41309703ad8549'
  'preflight_v18_e11_local.py'='f0087487da362476a1b98fa727205d5fe3bc2aa6'
  'verify_v18_full_review_pair.py'='89df4e7fcd9c4dbf6d8c36988a146850703784c6'
  'stage_v18_e11_review_only.py'='ef2e196d37566f1b17faa298b7f64f86dcb3980b'
  'check_v18_e11_postupdate_readonly.py'='975842871b5f5034171a785805942b847ebde1d1'
  'check_v18_e11_h_js_runtime_ro.py'='118acd7af8803d042b6f569bdc2840c08e3036b4'
  'check_v18_e11_final_fap_prewrite_ro.py'='90ee1ed26e9633fbe858de915cc1e9eaefe31eef'
  'stage_v18_final_fap_on_device_one_file.py'='b445d769383a520996bb95d44e6eba61b8ed848c'
  'check_v18_e11_phase2b_state_readonly.py'='800f7aa68abfdd304998ad69fa6568e7a4d0c695'
  'backup_v19_active_v18_fap_ro.py'='a6cde7413e45780476959a8ffda4c131f8186d98'
}
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
  'check_v18_e11_phase2b_state_readonly.py',
  'backup_v19_active_v18_fap_ro.py'
)
if ($names.Count -ne $expectedBlobs.Count) { throw 'Helper list/count mismatch. NO COM ACTION.' }

$git=(Get-Command git -ErrorAction Stop).Source
$dir=Join-Path $env:TEMP ('LabMate-v19-V18-BACKUP-CODE-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dir -ErrorAction Stop | Out-Null
foreach($name in $names) {
    $source=Join-Path $PSScriptRoot $name
    $dest=Join-Path $dir $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing locally pinned helper $name; NO COM ACTION."
    }
    $before=(& $git hash-object -- $source)
    if ($LASTEXITCODE -ne 0 -or
        $before.Trim().ToLowerInvariant() -ne $expectedBlobs[$name]) {
        throw "Unrecognized local helper content $name; NO COM ACTION."
    }
    Copy-Item -LiteralPath $source -Destination $dest -ErrorAction Stop
    $after=(& $git hash-object -- $dest)
    if ($LASTEXITCODE -ne 0 -or
        $after.Trim().ToLowerInvariant() -ne $expectedBlobs[$name]) {
        throw "Copied helper not identical $name; NO COM ACTION."
    }
}

$backup=Join-Path $backupRoot ('V19-pretrial-live-v18-' + [guid]::NewGuid().ToString('N'))
Write-Host 'V19 PRETRIAL ACTIVE V18 - READ-ONLY DEVICE, NEW PC BACKUP' -ForegroundColor Cyan
Write-Host 'LOCAL HELPER SOURCE: 11/11 PINNED GIT BLOBS PASS' -ForegroundColor Green
Write-Host 'Only device_info/storage stat/storage md5/storage read_chunks. NO device writes.'
$pyArgs=@(
  '-3',(Join-Path $dir 'backup_v19_active_v18_fap_ro.py'),
  '--port',$Port,
  '--momentum-scripts',$h0.FullName,
  '--old-candidate',$old,
  '--saved-old-fap-backup',$saved,
  '--final-v18-fap',$final,
  '--pc-backup',$backup
)
& py @pyArgs
if ($LASTEXITCODE -ne 0) { throw 'Live active v1.8 PC backup INCOMPLETE. STOP; do not blindly retry.' }
Write-Host 'VERIFIED LIVE FINAL v1.8 FAP PC BACKUP - PASS. STOP FOR REVIEW.' -ForegroundColor Green
