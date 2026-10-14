# Read-only preflight for a paired DEVELOPMENT artifact extracted from GitHub Actions.
# Does not install apps, contact COM ports, flash firmware, or alter Stable assets.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$PairDirectory,
    [ValidatePattern('^[A-Fa-f0-9]{40}$')]
    [string]$ExpectedSourceSha,
    [switch]$RequireUpdater
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

try {
    $dir = (Resolve-Path -LiteralPath $PairDirectory).ProviderPath
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) {
        throw 'Expected an extracted development artifact directory.'
    }

    # These five files must originate from ONE Actions run, not from
    # independently downloaded firmware and FAP builds.
    $required = @(
        'labmate.fap', 'firmware.dfu', 'SHA256SUMS.txt',
        'PROVENANCE.txt', 'READ_ME_FIRST.txt'
    )
    $updaterPresent = Test-Path -LiteralPath (Join-Path $dir 'firmware-update.tgz') -PathType Leaf
    if ($RequireUpdater -and -not $updaterPresent) { throw 'Missing minimal updater archive.' }
    if ($updaterPresent) { $required += 'firmware-update.tgz' }
    $present = @(Get-ChildItem -LiteralPath $dir -File | ForEach-Object { $_.Name })
    if ($present.Count -ne $required.Count) {
        throw 'Unexpected file count: refuse partial or mixed development pair.'
    }
    foreach ($name in $required) {
        if ($present -cnotcontains $name) { throw "Missing file: $name" }
    }

    $hashes = @{}
    $lines = @(Get-Content -LiteralPath (Join-Path $dir 'SHA256SUMS.txt'))
    $expectedChecksumCount = if ($updaterPresent) { 3 } else { 2 }
    if ($lines.Count -ne $expectedChecksumCount) {
        throw 'Unexpected number of binary SHA256 entries.'
    }
    foreach ($line in $lines) {
        if ($line -cnotmatch '^([A-Fa-f0-9]{64})\s+\*?(labmate\.fap|firmware\.dfu|firmware-update\.tgz)$') {
            throw 'Unexpected checksum manifest entry.'
        }
        $hash = $Matches[1]
        $name = $Matches[2]
        if ($hashes.ContainsKey($name)) { throw "Duplicate checksum: $name" }
        $hashes[$name] = $hash
    }
    $binaryNames = @('labmate.fap','firmware.dfu')
    if ($updaterPresent) { $binaryNames += 'firmware-update.tgz' }
    foreach ($name in $binaryNames) {
        if (-not $hashes.ContainsKey($name)) { throw "Missing checksum: $name" }
        $file = Join-Path $dir $name
        if ((Get-Item -LiteralPath $file).Length -le 0) {
            throw "Empty binary: $name"
        }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        if (-not [string]::Equals(
            $actual, $hashes[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "SHA256 MISMATCH: $name. No installation was attempted."
        }
        Write-Host "MATCHED PAIR SHA256 VERIFIED: $name $($actual.ToLowerInvariant())"
    }

    $meta = @{}
    foreach ($line in (Get-Content -LiteralPath (Join-Path $dir 'PROVENANCE.txt'))) {
        if ($line -cnotmatch '^([^:]+): (.+)$') { throw 'Malformed provenance entry.' }
        if ($meta.ContainsKey($Matches[1])) { throw 'Duplicate provenance key.' }
        $meta[$Matches[1]] = $Matches[2]
    }
    if ($meta.Count -ne 4) { throw 'Expected exactly four provenance entries.' }
    if (-not $meta.ContainsKey('LabMate commit') -or
        $meta['LabMate commit'] -cnotmatch '^[a-f0-9]{40}$') {
        throw 'Missing exact LabMate source commit.'
    }
    if ($meta['Momentum base commit'] -cne 'd3f89dfe2ef6b01839201598e9be1590cba80322') {
        throw 'Mismatched Momentum base commit.'
    }
    if ($meta['Patched HAL source diff SHA256'] -cnotmatch '^[a-f0-9]{64}$') {
        throw 'Missing patched HAL source fingerprint.'
    }
    if ($meta['GitHub Actions run'] -cnotmatch '^[0-9]+$') {
        throw 'Missing originating GitHub Actions run.'
    }
    if ($ExpectedSourceSha -and
        $meta['LabMate commit'] -cne $ExpectedSourceSha.ToLowerInvariant()) {
        throw 'Development pair was built from a different LabMate commit.'
    }
    $warning = Get-Content -Raw -LiteralPath (Join-Path $dir 'READ_ME_FIRST.txt')
    if ($warning -notmatch 'DO NOT' -or $warning -notmatch 'NOT AN APPROVED') {
        throw 'Missing required unapproved-development warning.'
    }

    Write-Host "PAIR PROVENANCE: LabMate $($meta['LabMate commit'])"
    Write-Host "PAIR PROVENANCE: Actions run $($meta['GitHub Actions run'])"
    Write-Host 'READ-ONLY PREFLIGHT PASS. DEVELOPMENT PAIR NOT APPROVED FOR FLASHING.'
    if ($updaterPresent) { Write-Host 'TGZ SHA256 verified; embedded firmware/manifest audited separately.' }
    Write-Host 'Self-consistent checksums do NOT authenticate an untrusted download.'
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate development pair REFUSED: $($_.Exception.Message)")
    exit 1
}
) {
            throw 'Unexpected checksum manifest entry.'
        }
        $hash = $Matches[1]
        $name = $Matches[2]
        if ($hashes.ContainsKey($name)) { throw "Duplicate checksum: $name" }
        $hashes[$name] = $hash
    }
    foreach ($name in @('labmate.fap','firmware.dfu')) {
        if (-not $hashes.ContainsKey($name)) { throw "Missing checksum: $name" }
        $file = Join-Path $dir $name
        if ((Get-Item -LiteralPath $file).Length -le 0) {
            throw "Empty binary: $name"
        }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        if (-not [string]::Equals(
            $actual, $hashes[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "SHA256 MISMATCH: $name. No installation was attempted."
        }
        Write-Host "MATCHED PAIR SHA256 VERIFIED: $name $($actual.ToLowerInvariant())"
    }

    $meta = @{}
    foreach ($line in (Get-Content -LiteralPath (Join-Path $dir 'PROVENANCE.txt'))) {
        if ($line -cnotmatch '^([^:]+): (.+)$') { throw 'Malformed provenance entry.' }
        if ($meta.ContainsKey($Matches[1])) { throw 'Duplicate provenance key.' }
        $meta[$Matches[1]] = $Matches[2]
    }
    if ($meta.Count -ne 4) { throw 'Expected exactly four provenance entries.' }
    if (-not $meta.ContainsKey('LabMate commit') -or
        $meta['LabMate commit'] -cnotmatch '^[a-f0-9]{40}$') {
        throw 'Missing exact LabMate source commit.'
    }
    if ($meta['Momentum base commit'] -cne 'd3f89dfe2ef6b01839201598e9be1590cba80322') {
        throw 'Mismatched Momentum base commit.'
    }
    if ($meta['Patched HAL source diff SHA256'] -cnotmatch '^[a-f0-9]{64}$') {
        throw 'Missing patched HAL source fingerprint.'
    }
    if ($meta['GitHub Actions run'] -cnotmatch '^[0-9]+$') {
        throw 'Missing originating GitHub Actions run.'
    }
    if ($ExpectedSourceSha -and
        $meta['LabMate commit'] -cne $ExpectedSourceSha.ToLowerInvariant()) {
        throw 'Development pair was built from a different LabMate commit.'
    }
    $warning = Get-Content -Raw -LiteralPath (Join-Path $dir 'READ_ME_FIRST.txt')
    if ($warning -notmatch 'DO NOT' -or $warning -notmatch 'NOT AN APPROVED') {
        throw 'Missing required unapproved-development warning.'
    }

    Write-Host "PAIR PROVENANCE: LabMate $($meta['LabMate commit'])"
    Write-Host "PAIR PROVENANCE: Actions run $($meta['GitHub Actions run'])"
    Write-Host 'READ-ONLY PREFLIGHT PASS. DEVELOPMENT PAIR NOT APPROVED FOR FLASHING.'
    Write-Host 'Self-consistent checksums do NOT authenticate an untrusted download.'
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate development pair REFUSED: $($_.Exception.Message)")
    exit 1
}
