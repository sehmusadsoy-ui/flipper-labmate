# v1.9 E11 prospective first FAP trial: exact READ-ONLY COM7 PREWRITE CHECK.
# NO app upload, no storage writes, no rename, no firmware/update, no reset.
# Do not run previous v1.8 installer / promotion scripts for a v1.9 binary.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port='COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'Close qFlipper before read-only device preflight. NO DEVICE WRITE.'
}
$old=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
$saved=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
$active=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482'
$data=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\V19-LabMate-Data-bbacf95032af4bf2bbb470614eaff1a0'
$final=Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
foreach($folder in @($old,$saved,$active,$data)) {
    if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
        throw "Required immutable E11 / app-data PC folder missing: $folder. NO COM ACTION."
    }
}
if (-not (Test-Path -LiteralPath $final -PathType Leaf)) {
    throw 'Pinned final v1.8 review FAP missing. NO COM ACTION.'
}
$h0=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Trusted E11 COM transport missing. NO COM ACTION.' }

# No network fetch. Every PC helper must be byte-identical to its audited
# Git blob before creating a temporary, isolated runnable copy.
$expected=@{
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
    'prepare_v19_e11_pc_only.py'='8cb273ae9833a6b71ce3733ff17ae1450212396f'
    'check_v19_e11_device_prewrite_ro.py'='2be0999cdab90d91113d1031f22d845b8dbfd326'
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
    'backup_v19_active_v18_fap_ro.py',
    'prepare_v19_e11_pc_only.py',
    'check_v19_e11_device_prewrite_ro.py'
)
if ($names.Count -ne 13 -or $expected.Count -ne 13) {
    throw 'Unexpected pinned helper inventory. NO COM ACTION.'
}
$git=(Get-Command git -ErrorAction Stop).Source
$dir=Join-Path $env:TEMP ('LabMate-V19-E11-PREWRITE-RO-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dir -ErrorAction Stop | Out-Null
foreach($name in $names) {
    $source=Join-Path $PSScriptRoot $name
    $destination=Join-Path $dir $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing pinned helper: $name. NO COM ACTION."
    }
    $before=(& $git hash-object -- $source)
    if ($LASTEXITCODE -ne 0 -or
        $before.Trim().ToLowerInvariant() -ne $expected[$name]) {
        throw "Local audited helper changed: $name. NO COM ACTION."
    }
    Copy-Item -LiteralPath $source -Destination $destination -ErrorAction Stop
    $after=(& $git hash-object -- $destination)
    if ($LASTEXITCODE -ne 0 -or
        $after.Trim().ToLowerInvariant() -ne $expected[$name]) {
        throw "Staged PC helper mismatch: $name. NO COM ACTION."
    }
}

Write-Host 'V19 E11 COM7 PREWRITE - READ-ONLY: NO APP/SD FIRMWARE WRITES' -ForegroundColor Cyan
Write-Host 'PINNED LOCAL HELPERS: 13/13 GIT BLOBS PASS' -ForegroundColor Green
$arguments=@(
    '-3',(Join-Path $dir 'check_v19_e11_device_prewrite_ro.py'),
    '--port',$Port,
    '--momentum-scripts',$h0.FullName,
    '--old-candidate',$old,
    '--saved-old-fap-backup',$saved,
    '--final-v18-fap',$final,
    '--active-v18-backup',$active,
    '--data-snapshot',$data
)
& py @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'E11 v1.9 device prewrite READ-ONLY NO-GO. STOP; DO NOT RETRY.'
}
Write-Host 'E11 v1.9 DEVICE PREWRITE READ-ONLY PASS; V1.9 FAP NOT INSTALLED.' -ForegroundColor Green
Write-Host 'STOP HERE. No new v1.9 app-stage upload/rename permission granted.' -ForegroundColor Yellow
