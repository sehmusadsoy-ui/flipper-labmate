# E11 2B READ-ONLY status after 0/1/2 safe renames, never rollback.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port='COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (Get-Process qFlipper -ErrorAction SilentlyContinue) { throw 'Close qFlipper first.' }
$backup=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
$new=Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
$old=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
if (-not (Test-Path -LiteralPath $new -PathType Leaf) -or
    -not (Test-Path -LiteralPath $old -PathType Container) -or
    -not (Test-Path -LiteralPath $backup -PathType Container)) {
    throw 'Previously verified E11 local inputs unavailable; NO COM ACTION.'
}
if ((Get-FileHash -LiteralPath $new -Algorithm SHA256).Hash -ne
      '393FE3E52AA710162A42D7299AA053F538B2EE1AD6542755CF402B83C1931B61') {
    throw 'New candidate PC hash changed. NO COM ACTION.'
}
$h0=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Trusted H0 CLI source missing.' }
# Previous implementation attempted anonymous raw.githubusercontent.com downloads
# from a private/authenticated repository, producing HTTP 404.  Instead use
# scripts beside THIS checked-out wrapper, but accept each helper only when its
# Git blob is exactly identical to the immutable historical E11 review pin.
# This is PC-only source verification/copying; all actual device calls below
# remain read-only.
$pin='086275b82205ad16750fca893e6aa66300f985b4'
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
}
$dir=Join-Path $env:TEMP ('LabMate-E11-2B-READONLY-' + [guid]::NewGuid().ToString('N'))
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
  'check_v18_e11_phase2b_state_readonly.py'
)
if ($names.Count -ne $expectedBlobs.Count) { throw 'Pinned helper count mismatch; NO COM action.' }
$git=Get-Command git -ErrorAction Stop
foreach($name in $names) {
    $source=Join-Path $PSScriptRoot $name
    $destination=Join-Path $dir $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Pinned local read-only helper missing: $name. NO COM action."
    }
    $before=(& $git.Source hash-object -- $source)
    if ($LASTEXITCODE -ne 0 -or
        $before.Trim().ToLowerInvariant() -ne $expectedBlobs[$name]) {
        throw "Pinned local helper Git blob mismatch: $name. NO COM action."
    }
    Copy-Item -LiteralPath $source -Destination $destination -ErrorAction Stop
    $after=(& $git.Source hash-object -- $destination)
    if ($LASTEXITCODE -ne 0 -or
        $after.Trim().ToLowerInvariant() -ne $expectedBlobs[$name]) {
        throw "Copied local helper blob mismatch: $name. NO COM action."
    }
}
Write-Host "E11 2B LOCAL HELPERS: 10/10 PINNED GIT BLOBS PASS" -ForegroundColor Green
Write-Host 'E11 2B THREE FAP PATHS STATE - READ ONLY' -ForegroundColor Cyan
Write-Host 'Only device_info / storage stat / storage md5. No write, rename, delete, firmware.'
$pyArgs=@(
  '-3',(Join-Path $dir 'check_v18_e11_phase2b_state_readonly.py'),
  '--port',$Port,
  '--momentum-scripts',$h0.FullName,
  '--old-candidate',$old,
  '--saved-old-fap-backup',$backup,
  '--new-fap',$new
)
& py @pyArgs
if ($LASTEXITCODE -ne 0) { throw 'E11 READ-ONLY 2B STATUS NO-GO. NO RETRY/RESTORE.' }
Write-Host 'E11 2B READ ONLY STATE CAPTURED. STOP, AWAIT REVIEW.' -ForegroundColor Cyan
