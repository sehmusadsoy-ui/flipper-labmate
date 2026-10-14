# LabMate v1.8DEV UART buffer trial: one FAP, NO FIRMWARE FLASH.
# Default = prepare/verify only. -Apply requires typed YUKLE.
[CmdletBinding()]
param(
    [string]$Directory = (Join-Path $HOME 'Downloads\LabMate-v18DEV-UARTFIX'),
    [string]$PreviousDevFap = (Join-Path $HOME 'Downloads\LabMate-v18DEV-FULL\labmate.fap'),
    [string]$FirmwareRoot = (Join-Path $HOME 'Momentum-Firmware'),
    [ValidatePattern('^(auto|COM[0-9]{1,3})$')]
    [string]$Port = 'auto',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$runId = '38635690935'
$artifact = 'v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH'
$source = 'f24a08640e7938cfaf7000a8f5b3e470c9b6ad14'
$momentum = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
$oldMomentum = 'e1784e7418d8b074e971983ceb6fef0f37e52ae4'
$oldDevSha = '9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881'
$expected = @{
    'labmate.fap' = 'eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf'
    'firmware.dfu' = 'e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0'
    'firmware-full-update.tgz' = 'be92ae2d63e0776c2bde1135e0f3f1e744cafc3ad4b88ca6855005e5de2a5353'
}
$required = @('labmate.fap', 'firmware.dfu', 'firmware-full-update.tgz',
              'SHA256SUMS.txt', 'PROVENANCE.txt', 'READ_ME_FIRST.txt')

function Assert-Sha256([string]$Path, [string]$ExpectedHash) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing file: $Path"
    }
    if ((Get-Item -LiteralPath $Path).Length -le 0) {
        throw "Empty file: $Path"
    }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    if (-not $actual.Equals($ExpectedHash, [StringComparison]::OrdinalIgnoreCase)) {
        throw "SHA256 MISMATCH: $Path"
    }
    Write-Host "SHA256 PASS: $([IO.Path]::GetFileName($Path))" -ForegroundColor Green
}

try {
    if ($env:OS -ne 'Windows_NT') { throw 'Windows PowerShell is required.' }
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'GitHub CLI (gh) missing.'
    }
    & gh auth status *> $null
    if ($LASTEXITCODE -ne 0) { throw 'gh auth login required.' }

    # Refuse a silently substituted GitHub run or branch head.
    $viewJson = & gh run view $runId --repo $repo --json conclusion,headSha
    if ($LASTEXITCODE -ne 0) { throw 'Cannot verify GitHub Actions run.' }
    $view = $viewJson | ConvertFrom-Json
    if ($view.conclusion -cne 'success' -or $view.headSha -cne $source) {
        throw 'GitHub Actions source SHA or successful conclusion does not match.'
    }

    if (-not (Test-Path -LiteralPath $Directory)) {
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    }
    $dir = (Resolve-Path -LiteralPath $Directory).ProviderPath
    $entries = @(Get-ChildItem -LiteralPath $dir -Force)
    if ($entries.Count -eq 0) {
        & gh run download $runId --repo $repo --name $artifact --dir $dir
        if ($LASTEXITCODE -ne 0) {
            throw 'GitHub artifact download failed; no install.'
        }
    } else {
        Write-Host 'Existing staging directory: verify pinned files without replacing anything.'
    }
    $entries = @(Get-ChildItem -LiteralPath $dir -Force)
    if ($entries.Count -ne $required.Count) {
        throw 'Unexpected number of artifact entries. Nothing installed.'
    }
    foreach ($entry in $entries) {
        if ($entry.PSIsContainer -or $required -cnotcontains $entry.Name) {
            throw "Unexpected artifact entry: $($entry.Name)"
        }
    }
    foreach ($name in $expected.Keys) {
        Assert-Sha256 (Join-Path $dir $name) $expected[$name]
    }

    $rows = @(Get-Content -LiteralPath (Join-Path $dir 'SHA256SUMS.txt'))
    if ($rows.Count -ne 3) { throw 'Expected exactly three checksum rows.' }
    $seen = @{}
    foreach ($row in $rows) {
        if ($row -cnotmatch '^([a-fA-F0-9]{64})\s+\*?(labmate\.fap|firmware\.dfu|firmware-full-update\.tgz)$') {
            throw 'Checksum manifest contains unexpected row.'
        }
        $name = $Matches[2]
        if ($seen.ContainsKey($name)) { throw "Repeated checksum: $name" }
        if (-not $Matches[1].Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "Checksum manifest mismatch: $name"
        }
        $seen[$name] = $true
    }
    if ($seen.Count -ne 3) { throw 'Checksum manifest incomplete.' }
    $provenance = Get-Content -Raw -LiteralPath (Join-Path $dir 'PROVENANCE.txt')
    foreach ($line in @(
        "LabMate commit: $source",
        "Momentum base: $momentum",
        "Installed Momentum012 source: $oldMomentum",
        "Actions run: $runId"
    )) {
        if ($provenance -notmatch ('(?m)^' + [regex]::Escape($line) + '\r?$')) {
            throw "Provenance mismatch: $line"
        }
    }
    $warning = Get-Content -Raw -LiteralPath (Join-Path $dir 'READ_ME_FIRST.txt')
    if ($warning -notmatch 'DO NOT FLASH' -or $warning -notmatch 'NOT A RELEASE') {
        throw 'Test-only release warning is missing.'
    }
    Write-Host 'LABMATE UARTFIX FAP PREPARE PASS. NO DEVICE CHANGE.' -ForegroundColor Green
    Write-Host "New FAP: $(Join-Path $dir 'labmate.fap')"
    Write-Host 'Existing patched firmware hash MATCHES. Never install the TGZ/DFU for this FAP-only test.'

    if (-not $Apply) {
        Write-Host 'Stage-only. Re-run with -Apply when ready.'
        exit 0
    }

    Assert-Sha256 $PreviousDevFap $oldDevSha
    $envCmd = Join-Path $FirmwareRoot 'scripts\toolchain\fbtenv.cmd'
    $runfap = Join-Path $FirmwareRoot 'scripts\runfap.py'
    if (-not (Test-Path -LiteralPath $envCmd -PathType Leaf) -or
        -not (Test-Path -LiteralPath $runfap -PathType Leaf)) {
        throw 'Momentum SDK/runfap scripts missing. No install.'
    }
    Write-Host 'PREVIOUS DEV FAP SAFE AT:' $PreviousDevFap
    Write-Host 'This replaces ONLY /ext/apps/Tools/labmate.fap with tested UART fix.'
    Write-Host 'Exit LabMate, close qFlipper, keep USB connected. NO firmware reflash.'
    $approval = Read-Host 'Type YUKLE to install the new UART test FAP'
    if ($approval -cne 'YUKLE') {
        Write-Host 'Operator did not approve; no USB installation.'
        exit 0
    }

    # Frozen historical one-FAP installer. Exact v1.8DEV previous workflow.
    $installer = Join-Path $env:TEMP 'install-labmate-v18-uartfix.ps1'
    $uri = 'https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/24c603bef6568003ede441871432c6e2dbb4384d/scripts/install-labmate.ps1'
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $installer
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
        throw 'Pinned single-FAP installer unavailable.'
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer `
        -FapPath (Join-Path $dir 'labmate.fap') `
        -ExpectedSha256 $expected['labmate.fap'] `
        -FirmwareRoot $FirmwareRoot -Port $Port
    if ($LASTEXITCODE -ne 0) { throw 'FAP USB installer failed or unconfirmed.' }
    Write-Host 'LABMATE UARTFIX FAP INSTALL COMMAND PASS. Confirm actual app launch on screen.' -ForegroundColor Green
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate UARTFIX STOPPED: $($_.Exception.Message)")
    exit 1
}
