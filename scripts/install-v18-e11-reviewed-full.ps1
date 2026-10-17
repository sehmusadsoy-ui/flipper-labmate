# LabMate E11 pinned FULL candidate — STAGE ONLY unless explicitly triple-authorized.
# Default operation is offline on PC; -Apply MAY FLASH/REPLACE the device.
# Never use a FAP-split bundle; current old /ext/Manifest targets EXITFIX FAP.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$CandidateDirectory,
    [switch]$Apply,
    [switch]$AcceptExitfixReplacement,
    [switch]$AcceptNonExactFirmwareRollback,
    [string]$RollbackTgz,
    [string]$InstalledExitfixCopy,
    [string]$HistoricalLabmateBackupDirectory,
    [string]$CurrentLabmateSnapshotDirectory,
    [string]$SettingsBackupTgz,
    [string]$FirmwareRoot,
    [ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port = 'COM7'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$source = 'ba379f20fb29369501e1057f570a911f71ac83f8'
$buildRun = 38966248325
$base = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
$expected = @{
    'labmate.fap' = '2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0'
    'js_gpio.module' = 'fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a'
    'firmware.dfu' = '88d12fee4edb4fa0ec042a1b526ddb41b8db36aeb9554c6a9a8aef1c37e4e1b0'
    'firmware-full-update.tgz' = '11ed3cdf4e99c9c7218973695d349cd946be97d21dfc59231113bde15e94c553'
}
function Assert-ExactSha([string]$File, [string]$Hash) {
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { throw 'Required local input missing' }
    if ((Get-Item -LiteralPath $File).Length -le 0) { throw 'Required local input empty' }
    if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash -ine $Hash) {
        throw 'Pinned local input SHA256 mismatch'
    }
}
function Assert-SafeArg([string]$Value) {
    if ($Value -match '[\"&|<>^%!\r\n]') {
        throw 'Unsafe shell command path character'
    }
}
# Consent/risk switches MUST be present before any live-device step;
# do not automatically infer them from "devam" or from historical approvals.
if ($Apply -and (-not $AcceptExitfixReplacement -or -not $AcceptNonExactFirmwareRollback)) {
    throw 'E11 -Apply REFUSED: BOTH independent risk acknowledgements are mandatory. NO FLASH.'
}
# Repo-local audit source must be checked out at the same development branch.
$repoRoot = Split-Path -Parent $PSScriptRoot
$verifier = Join-Path $repoRoot 'scripts\verify_v18_full_review_pair.py'
$transition = Join-Path $repoRoot 'scripts\audit_v18_e11_full_transition.py'
$backupGate = Join-Path $repoRoot 'scripts\verify_v18_e11_pc_backup_gate.py'
if (-not (Test-Path -LiteralPath $verifier -PathType Leaf) -or
    -not (Test-Path -LiteralPath $transition -PathType Leaf) -or
    -not (Test-Path -LiteralPath $backupGate -PathType Leaf)) {
    throw 'Exact v1.8 E11 source audit scripts missing'
}
$bundle = (Resolve-Path -LiteralPath $CandidateDirectory).ProviderPath
foreach ($name in $expected.Keys) {
    Assert-ExactSha (Join-Path $bundle $name) $expected[$name]
}
& py -3 $verifier $bundle --expected-source $source --expected-run $buildRun
if ($LASTEXITCODE -ne 0) { throw 'Exact E11 full candidate provenance verification FAILED' }
& py -3 $transition --candidate $bundle
if ($LASTEXITCODE -ne 0) { throw 'Full E11 resource transition verification FAILED' }

# Stage into a brand-new PC TEMP folder; archive extraction is NOT a device write.
$stage = Join-Path $env:TEMP ('LabMate-E11-FULL-READONLY-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage -ErrorAction Stop | Out-Null
$archive = Join-Path $bundle 'firmware-full-update.tgz'
& tar.exe -xzf $archive -C $stage
if ($LASTEXITCODE -ne 0) { throw 'Pinned full updater PC extraction FAILED' }
$root = Join-Path $stage 'f7-update-mntm-HEAD-d3f89dfe'
$manifest = Join-Path $root 'update.fuf'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw 'Pinned exact full updater manifest not found'
}
$embeddedFirmware = Join-Path $root 'firmware.dfu'
Assert-ExactSha $embeddedFirmware $expected['firmware.dfu']
$unpackedManifest = Get-Content -Raw -LiteralPath $manifest
foreach ($field in @(
    'Target: 7',
    'Firmware: firmware.dfu',
    'Resources: resources.tar.gz',
    'Radio: radio.bin',
    'Loader: updater.bin'
)) {
    if ($unpackedManifest -notmatch ('(?m)^' + [regex]::Escape($field) + '\r?$')) {
        throw 'Pinned full updater manifest required field mismatch'
    }
}
Write-Host 'E11 exact FULL updater + NEW FAP pair PC PREFLIGHT PASS (NOT A DEVICE TEST)' -ForegroundColor Green
Write-Host 'The resource update targets installed EXITFIX and replaces it with E11 FAP.'
Write-Host 'The official Momentum MNTM-012 rollback does NOT restore custom dirty firmware exactly.'
Write-Host "PC staging only: $stage"
if (-not $Apply) {
    Write-Host 'STAGE ONLY - NO DEVICE OR SD WRITE; PHYSICAL E11 TRIAL NOT PERFORMED.'
    return
}
# The following checks are intentionally required ONLY for -Apply and must
# fail BEFORE any Flipper serial/USB writer is opened.
foreach ($argument in @($RollbackTgz, $InstalledExitfixCopy,
                        $HistoricalLabmateBackupDirectory, $CurrentLabmateSnapshotDirectory,
                        $SettingsBackupTgz, $FirmwareRoot)) {
    if ([string]::IsNullOrWhiteSpace($argument)) {
        throw 'E11 Apply REFUSED: explicit rollback, working EXITFIX, historical AND current LabMate data snapshots, settings and Momentum-root paths REQUIRED'
    }
}
Assert-ExactSha $RollbackTgz '1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7'
Assert-ExactSha $InstalledExitfixCopy '7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be'
Assert-ExactSha $SettingsBackupTgz 'a0487ede35b8cec4cef505faf57363768fc1bc02d5d7c1dd3a8dcfa282c00ef2'
& py -3 $backupGate --historical $HistoricalLabmateBackupDirectory --current $CurrentLabmateSnapshotDirectory
if ($LASTEXITCODE -ne 0) {
    throw 'E11 Apply REFUSED: two-state LabMate PC backup checksum gate FAILED; NO DEVICE WRITE'
}
$fw = (Resolve-Path -LiteralPath $FirmwareRoot).ProviderPath
$head = (& git -C $fw rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $head -cne $base) {
    throw 'E11 Apply REFUSED: Momentum script source not at pinned base'
}
$envCmd = Join-Path $fw 'scripts\toolchain\fbtenv.cmd'
$selfUpdate = Join-Path $fw 'scripts\selfupdate.py'
foreach ($file in @($envCmd, $selfUpdate)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw 'E11 Apply REFUSED: pinned Momentum updater toolchain absent'
    }
}
$changedTransport = @(& git -C $fw status --porcelain -- scripts/selfupdate.py scripts/flipper)
if ($LASTEXITCODE -ne 0 -or $changedTransport.Count -gt 0) {
    throw 'E11 Apply REFUSED: modified update transport script/tree'
}
foreach ($item in @($envCmd,$selfUpdate,$manifest)) { Assert-SafeArg $item }
Write-Host 'EXPERIMENTAL FULL FIRMWARE REPLACEMENT — NOT GUARANTEED BOOT/ROLLBACK' -ForegroundColor Yellow
Write-Host 'Must close qFlipper, disconnect external GPIO devices, use stable power and USB.'
Write-Host 'Do not attempt if current dirty firmware is irreplaceable.'
$choice = Read-Host 'TYPE YUKLE-E11 to replace firmware and EXITFIX with the matched E11 pair'
if ($choice -cne 'YUKLE-E11') { throw 'E11 physical trial declined: no device write started' }
# This is the ONLY device-write action in this script. A zero status only
# means the update request was accepted; boot/rollback need real testing.
$line = 'set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && python "{1}" -p {2} "{3}"' -f $envCmd,$selfUpdate,$Port,$manifest
& cmd.exe /d /s /c $line
if ($LASTEXITCODE -ne 0) {
    throw 'E11 selfupdate request rejected or interrupted; device state UNKNOWN, do not automatically retry'
}
Write-Host 'E11 UPDATE REQUEST ACCEPTED: DO NOT CALL THIS DEVICE PASS.'
Write-Host 'Confirm firmware boot, exact E11 FAP version, resource ownership, and STOP/BACK before any release.'
