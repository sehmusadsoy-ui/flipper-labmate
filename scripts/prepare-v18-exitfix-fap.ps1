# LabMate v1.8DEV exit-resource cleanup FAP: STAGE AND VERIFY ONLY.
# Explicitly NO USB, no firmware flash, no release, no SD modification.
[CmdletBinding()]
param(
    [string]$Directory = (Join-Path $HOME 'Downloads\LabMate-v18DEV-EXITFIX'),
    [string]$PreviousFapPath = (Join-Path $HOME 'Downloads\LabMate-v18DEV-UARTFIX\labmate.fap'),
    [switch]$OfflineVerify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Pinned CI build; never use mutable branch latest artifacts.
$repo = 'sehmusadsoy-ui/flipper-labmate'
$runId = '38645876409'
$sourceSha = 'a3c52e8ef5ff09c51cd3b5eb40c6c1108cb89e18'
$momentumSha = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
$original012Sha = 'e1784e7418d8b074e971983ceb6fef0f37e52ae4'
$artifactName = 'v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH'
$previousFapSha = 'eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf'
$expected = @{
    'labmate.fap' = '7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be'
    'firmware.dfu' = 'e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0'
    'firmware-full-update.tgz' = 'd7665bf273f69d98aef8bdab06705640833127465d9241c00dff399248b57b18'
}
$required = @(
    'labmate.fap', 'firmware.dfu', 'firmware-full-update.tgz',
    'SHA256SUMS.txt', 'PROVENANCE.txt', 'READ_ME_FIRST.txt'
)

function Assert-FileSha256([string]$Path, [string]$Expected, [string]$Label) {
    if(-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label file: $Path"
    }
    if((Get-Item -LiteralPath $Path).Length -eq 0) {
        throw "Empty $Label file: $Path"
    }
    $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    if(-not $hash.Equals($Expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw "SHA256 MISMATCH for $Label; no USB/device action."
    }
    Write-Host "SHA256 PASS: $Label" -ForegroundColor Green
}

try {
    if($env:OS -ne 'Windows_NT') {
        throw 'Windows PowerShell is required for this operator staging procedure.'
    }
    if(-not $OfflineVerify) {
        if(-not (Get-Command gh -ErrorAction SilentlyContinue)) {
            throw 'GitHub CLI (gh) missing; nothing downloaded.'
        }
        & gh auth status *> $null
        if($LASTEXITCODE -ne 0) {
            throw 'gh auth login required; nothing downloaded.'
        }
        $viewText = & gh run view $runId --repo $repo --json conclusion,headSha
        if($LASTEXITCODE -ne 0) {
            throw 'Unable to verify pinned Actions run; nothing downloaded.'
        }
        $view = ($viewText | ConvertFrom-Json)
        if($view.conclusion -cne 'success' -or $view.headSha -cne $sourceSha) {
            throw 'Pinned CI run not SUCCESS at expected source SHA.'
        }
    }

    # Preserve all old test artifacts, old FAP backup, CSV data and user profiles.
    Assert-FileSha256 $PreviousFapPath $previousFapSha 'previous UARTFIX rollback FAP'
    if(-not (Test-Path -LiteralPath $Directory)) {
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    }
    $dir = (Resolve-Path -LiteralPath $Directory).ProviderPath
    $entries = @(Get-ChildItem -LiteralPath $dir -Force)
    if($entries.Count -eq 0) {
        if($OfflineVerify) {
            throw 'OfflineVerify requires an existing, populated staging folder.'
        }
        & gh run download $runId --repo $repo --name $artifactName --dir $dir
        if($LASTEXITCODE -ne 0) {
            throw 'Pinned artifact download failed. Do not install anything.'
        }
    } else {
        Write-Host 'Existing staging directory: verify only, do not overwrite.'
    }

    $entries = @(Get-ChildItem -LiteralPath $dir -Force)
    if($entries.Count -ne $required.Count) {
        throw 'Unexpected staging file count; no file will be replaced.'
    }
    foreach($entry in $entries) {
        if($entry.PSIsContainer -or $required -cnotcontains $entry.Name) {
            throw "Unexpected staging entry: $($entry.Name)"
        }
    }
    foreach($name in $expected.Keys) {
        Assert-FileSha256 (Join-Path $dir $name) $expected[$name] $name
    }

    $rows = @(Get-Content -LiteralPath (Join-Path $dir 'SHA256SUMS.txt'))
    if($rows.Count -ne 3) {
        throw 'Expected exactly three SHA256SUMS rows.'
    }
    $seen = @{}
    foreach($row in $rows) {
        if($row -cnotmatch '^([a-fA-F0-9]{64})\s+\*?(labmate\.fap|firmware\.dfu|firmware-full-update\.tgz)$') {
            throw "Unexpected SHA256SUMS row: $row"
        }
        $name = $Matches[2]
        if($seen.ContainsKey($name)) {
            throw "Duplicate SHA256 entry: $name"
        }
        if(-not $Matches[1].Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "SHA256SUMS does not match pinned reference: $name"
        }
        $seen[$name] = $true
    }
    if($seen.Count -ne 3) {
        throw 'SHA256SUMS manifest incomplete.'
    }
    Write-Host 'SHA256 MANIFEST PASS' -ForegroundColor Green

    $provenance = Get-Content -Raw -LiteralPath (Join-Path $dir 'PROVENANCE.txt')
    foreach($line in @(
        "LabMate commit: $sourceSha",
        "Momentum base: $momentumSha",
        "Installed Momentum012 source: $original012Sha",
        "Actions run: $runId"
    )) {
        if($provenance -cnotmatch ('(?m)^' + [regex]::Escape($line) + '\r?$')) {
            throw "Provenance mismatch: $line"
        }
    }
    $notice = Get-Content -Raw -LiteralPath (Join-Path $dir 'READ_ME_FIRST.txt')
    if($notice -notmatch 'NOT A RELEASE' -or $notice -notmatch 'DO NOT FLASH') {
        throw 'Artifact safeguard / not-a-release warning missing.'
    }
    Write-Host 'PROVENANCE PASS' -ForegroundColor Green

    Write-Host ''
    Write-Host 'LABMATE V1.8 EXITFIX STAGE PASS. NO DEVICE CHANGE.' -ForegroundColor Green
    Write-Host "NEW_FAP: $(Join-Path $dir 'labmate.fap')"
    Write-Host "NEW_FAP_SHA256: $($expected['labmate.fap'])"
    Write-Host "PINNED_FIRMWARE_SHA256: $($expected['firmware.dfu'])"
    Write-Host 'OLD_UARTFIX_BACKUP: PASS'
    Write-Host 'Do NOT install firmware.dfu or firmware-full-update.tgz.'
    Write-Host 'No USB installer exists in this script. Await a separate operator approval.'
    exit 0
} catch {
    [Console]::Error.WriteLine("LABMATE EXITFIX STAGE STOPPED: $($_.Exception.Message)")
    exit 1
}
