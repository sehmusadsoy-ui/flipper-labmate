# E11 v1.9 independently consent-gated 2-rename activation REVIEW wrapper.
# DEFAULT = PC-ONLY DRY RUN; no COM/USB operations; never flash firmware.
# -ApplyActivation + -AcceptFirmwareABIRisk actually renames 2 SD files.
# Old stage-only consent is NOT activation consent. Do NOT invoke these
# switches unless owner gives NEW explicit, scoped approval after host tests.
# On any rename ambiguity stop; NEVER auto-repeat or auto-restore.
[CmdletBinding()]
param(
    [ValidateSet('COM7')][string]$Port='COM7',
    [switch]$ApplyActivation,
    [switch]$AcceptFirmwareABIRisk
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

$root = Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups'
$old = Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
$saved = Join-Path $root 'E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
$active = Join-Path $root 'V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482'
$data = Join-Path $root 'V19-LabMate-Data-bbacf95032af4bf2bbb470614eaff1a0'
$final = Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
$candidateDir = Join-Path $root 'V19-WINDOWS-PC-CANDIDATE-3d66658-20261019'
$candidate = Join-Path $candidateDir 'labmate-v1.9DEV-E11-WINDOWS-PC-ONLY.fap'
$manifest = Join-Path $candidateDir 'WINDOWS_PC_ONLY_CANDIDATE_MANIFEST.json'
$marker = Join-Path $candidateDir 'WINDOWS_PC_ONLY_CANDIDATE_VERIFIED.txt'
$expectedFapSHA = 'E1F43390C4078FBAAD7E13124331926E0D6667294F2815E8B63762BD16F3FF90'
$expectedV18SHA = '393FE3E52AA710162A42D7299AA053F538B2EE1AD6542755CF402B83C1931B61'

if ($ApplyActivation -and -not $AcceptFirmwareABIRisk) {
    throw 'Installed E11 firmware binary ABI not attested; explicit ABI risk acceptance required.'
}
if ($AcceptFirmwareABIRisk -and -not $ApplyActivation) {
    throw 'ABI-risk flag by itself is invalid. NO DEVICE ACTION.'
}
if ($ApplyActivation -and (Get-Process qFlipper -ErrorAction SilentlyContinue)) {
    throw 'qFlipper open; no device rename initiated.'
}
foreach($folder in @($root,$old,$saved,$active,$data,$candidateDir)) {
    if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
        throw "Required PC directory missing: $folder. STOP before COM."
    }
}
foreach($file in @($final,$candidate,$manifest,$marker)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Required PC identity/evidence file missing: $file. STOP before COM."
    }
}
if (Test-Path -LiteralPath (Join-Path $candidateDir 'INCOMPLETE_DO_NOT_USE_FOR_DEVICE_STAGE.txt')) {
    throw 'PC candidate incomplete; refuse installation/stage.'
}
$inventory = @(Get-ChildItem -LiteralPath $candidateDir -Force)
if ($inventory.Count -ne 3 -or @($inventory | Where-Object { $_.Name -notin @(
    'labmate-v1.9DEV-E11-WINDOWS-PC-ONLY.fap',
    'WINDOWS_PC_ONLY_CANDIDATE_MANIFEST.json',
    'WINDOWS_PC_ONLY_CANDIDATE_VERIFIED.txt'
)}).Count -ne 0) {
    throw 'Windows PC candidate directory has altered inventory. STOP.'
}
$reparse = [IO.FileAttributes]::ReparsePoint
foreach($file in @($candidate,$manifest,$marker)) {
    if (((Get-Item -LiteralPath $file -Force).Attributes -band $reparse) -ne 0) {
        throw 'Reject symlink/reparse input: PC candidate.'
    }
}
$hash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash
if ((Get-Item -LiteralPath $candidate).Length -ne 97540 -or $hash -ne $expectedFapSHA) {
    throw 'Wrong candidate SHA256 or length. NO device write.'
}
$record = Get-Content -LiteralPath $manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($record.status -ne 'PC_WINDOWS_REVIEW_COPY_ONLY' -or
    $record.filename -ne 'labmate-v1.9DEV-E11-WINDOWS-PC-ONLY.fap' -or
    $record.candidate_sha256.ToUpperInvariant() -ne $expectedFapSHA -or
    $record.candidate_bytes -ne 97540 -or
    $record.prior_active_v18_sha256.ToUpperInvariant() -ne $expectedV18SHA -or
    $record.labmate_snapshot_files_verified -ne 12 -or
    $record.labmate_snapshot_bytes -ne 2128 -or
    $record.device_write -ne $false -or
    $record.install_authorized -ne $false) {
    throw 'PC-only candidate provenance/backup proof mismatch. NO COM.'
}

# The module imported as flipper.storage must match the EXACT *upstream*
# pinned Momentum source (Git blob), not merely a similarly named local file.
# H0 was used for accepted v1.8 real-device readback; the hash is now pinned.
$h0 = Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Pinned E11 serial transport not present. NO COM.' }
$git = (Get-Command git -ErrorAction Stop).Source
$h0storage = Join-Path $h0.FullName 'flipper\storage.py'
$h0blob = (& $git hash-object -- $h0storage)
if ($LASTEXITCODE -ne 0 -or
    $h0blob.Trim().ToLowerInvariant() -ne '0182cf45fa8ff254e31da6a1d059d570badb816e') {
    throw 'Momentum serial transport does not match exact pinned d3f89dfe Git blob. NO COM.'
}
$expected = @{
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
    'check_v19_e11_staged_device_ro.py'='2d75ad615840f4aa38422635a9c2d7469315ac56'
    'check_v19_e11_pc_backups_windows_ro.py'='4ff782b0cbe239fe15e2029edd6b387862dff339'
    'activate_v19_e11_once_review_only.py'='755f8b62ed566903881370f577a1c2eedf63b320'
    'review_v19_e11_activation_recovery_offline.py'='95633df47f02d630da89d9b65b72b3a5d9d1c25a'
    'simulate_v19_e11_storage_cli_offline.py'='5a45d1446b8c87710ac3245b8df475f59b4a1ad5'
    'simulate_v19_e11_fap_swap_offline.py'='5a3b6939a7920ba8eeb2a630573fd0d341ca098e'
}
$names = @(
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
    'check_v19_e11_device_prewrite_ro.py',
    'check_v19_e11_staged_device_ro.py',
    'check_v19_e11_pc_backups_windows_ro.py',
    'activate_v19_e11_once_review_only.py',
    'review_v19_e11_activation_recovery_offline.py',
    'simulate_v19_e11_storage_cli_offline.py',
    'simulate_v19_e11_fap_swap_offline.py'
)
if ($names.Count -ne 19 -or $expected.Count -ne 19) {
    throw 'Expected nineteen audited Python helpers only. STOP.'
}
$working = Join-Path $env:TEMP ('LabMate-V19-E11-ACTIVATION-PC-GATE-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $working -ErrorAction Stop | Out-Null
foreach($name in $names) {
    $source = Join-Path $PSScriptRoot $name
    $target = Join-Path $working $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Missing pinned stage helper $name. NO COM."
    }
    $before = (& $git hash-object -- $source)
    if ($LASTEXITCODE -ne 0 -or
        $before.Trim().ToLowerInvariant() -ne $expected[$name]) {
        throw "Pinned stage helper changed: $name. NO COM."
    }
    Copy-Item -LiteralPath $source -Destination $target -ErrorAction Stop
    $after = (& $git hash-object -- $target)
    if ($LASTEXITCODE -ne 0 -or
        $after.Trim().ToLowerInvariant() -ne $expected[$name]) {
        throw "Copied stage helper changed: $name. NO COM."
    }
}

# Call a pin-verified file directly; Windows PowerShell can remove quotes
# from a Python -c string, yielding SyntaxError despite sound backup files.
# No COM transport is imported or opened by this PC-only verification.
$verifyArgs = @(
    '-3','-B',(Join-Path $working 'check_v19_e11_pc_backups_windows_ro.py'),
    '--active-v18-backup',$active,
    '--historical-e11-backup',$saved,
    '--data-snapshot',$data
)
& py @verifyArgs
if ($LASTEXITCODE -ne 0) {
    throw 'PC backup verification failed; check helper output. NO COM.'
}
Write-Host 'V19 E11 ACTIVATION LOCAL HASH / BACKUP / TRANSPORT REVIEW PASS' -ForegroundColor Green
Write-Host 'FAP: 97540 bytes / pinned SHA256, source 19/19 / transport Git blob PASS'
Write-Host 'Original v1.8, E11 v1.8DEV and 12 LabMate data files preserved on PC.'

if (-not $ApplyActivation) {
    Write-Host 'DRY RUN: NO COM / NO DEVICE WRITES / NO RENAMES / NO FIRMWARE FLASH' -ForegroundColor Cyan
    Write-Host 'Native E11 installed firmware ABI: NOT ATTESTED.' -ForegroundColor Yellow
    Write-Host 'Activation requires separate, explicit owner approval; NEVER imply permission.'
    exit 0
}

# WARNING: THIS OPENS COM7 AND MAY PERFORM TWO NON-ATOMIC SD RENAMES.
# Fail-closed fresh same-session full-readback/old-backup/native E11 checks
# precede each move. If the first rename succeeds and the second fails,
# the installed app pathname MAY BE ABSENT. No retry or recovery here.
Write-Host 'WARNING: ACTIVATION WILL RENAME TWO ON-DEVICE FAP FILES' -ForegroundColor Yellow
Write-Host 'E11 firmware export ABI NOT independently attested; this is an experimental risk.'
Write-Host 'STOP on error. No repeat, rollback, firmware flash or deletion.'
$activateArgs = @(
    '-3','-B',(Join-Path $working 'activate_v19_e11_once_review_only.py'),
    '--port',$Port,
    '--momentum-scripts',$h0.FullName,
    '--old-candidate',$old,
    '--saved-old-fap-backup',$saved,
    '--final-v18-fap',$final,
    '--active-v18-backup',$active,
    '--data-snapshot',$data,
    '--candidate',$candidate,
    '--approve-two-renames','I_EXPLICITLY_APPROVE_V19_TWO_NONATOMIC_RENAMES_ONLY',
    '--accept-unverified-abi-risk','I_ACCEPT_E11_INSTALLED_FIRMWARE_BINARY_ABI_NOT_ATTESTED'
)
& py @activateArgs
if ($LASTEXITCODE -ne 0) {
    throw 'UNKNOWN POSSIBLE PARTIAL ACTIVATION. STOP; classify read-only. NO RE-RUN.'
}
Write-Host 'STAGED v1.9 FILE ACTIVATED BY RENAME: INDEPENDENT READ-ONLY SCREEN STILL REQUIRED.'
Write-Host 'Do not start app before post-activation identity PASS.'
