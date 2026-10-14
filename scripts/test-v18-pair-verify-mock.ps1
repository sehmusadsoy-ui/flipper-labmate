# Windows native tests for read-only development-pair verifier.
# Fixture bytes are NOT firmware/FAP and there is NO USB or flashing.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Join-Path ([IO.Path]::GetTempPath()) ("labmate-v18-pair-" + [guid]::NewGuid().ToString('N'))
$source = 'a' * 40
$base = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
try {
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    [IO.File]::WriteAllBytes((Join-Path $root 'labmate.fap'), [byte[]](1,2,3,4))
    [IO.File]::WriteAllBytes((Join-Path $root 'firmware.dfu'), [byte[]](9,8,7,6))
    $fapHash = (Get-FileHash -LiteralPath (Join-Path $root 'labmate.fap') -Algorithm SHA256).Hash.ToLowerInvariant()
    $fwHash = (Get-FileHash -LiteralPath (Join-Path $root 'firmware.dfu') -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText((Join-Path $root 'SHA256SUMS.txt'),
        "$fapHash  labmate.fap" + [Environment]::NewLine +
        "$fwHash  firmware.dfu" + [Environment]::NewLine)
    $provenance = "LabMate commit: $source" + [Environment]::NewLine +
        "Momentum base commit: $base" + [Environment]::NewLine +
        "Patched HAL source diff SHA256: " + ('b' * 64) + [Environment]::NewLine +
        "GitHub Actions run: 12345678" + [Environment]::NewLine
    [IO.File]::WriteAllText((Join-Path $root 'PROVENANCE.txt'), $provenance)
    [IO.File]::WriteAllText((Join-Path $root 'READ_ME_FIRST.txt'),
        'NOT AN APPROVED INSTALL PACKAGE. DO NOT FLASH. TEST PAIR ONLY.')

    & ./scripts/verify-v18-matched-pair.ps1 -PairDirectory $root -ExpectedSourceSha $source
    if ($LASTEXITCODE -ne 0) { throw 'Verifier rejected matching intact pair.' }

    & ./scripts/verify-v18-matched-pair.ps1 -PairDirectory $root -ExpectedSourceSha ('c' * 40)
    if ($LASTEXITCODE -eq 0) { throw 'Wrong expected source SHA was accepted.' }

    [IO.File]::WriteAllBytes((Join-Path $root 'labmate.fap'), [byte[]](1,2,3,5))
    & ./scripts/verify-v18-matched-pair.ps1 -PairDirectory $root -ExpectedSourceSha $source
    if ($LASTEXITCODE -eq 0) { throw 'Tampered FAP was accepted.' }
    [IO.File]::WriteAllBytes((Join-Path $root 'labmate.fap'), [byte[]](1,2,3,4))

    # Verify the firmware digest independently; a matching FAP alone
    # cannot prove the pair is safe or even complete.
    [IO.File]::WriteAllBytes((Join-Path $root 'firmware.dfu'), [byte[]](9,8,7,0))
    & ./scripts/verify-v18-matched-pair.ps1 -PairDirectory $root -ExpectedSourceSha $source
    if ($LASTEXITCODE -eq 0) { throw 'Tampered firmware was accepted.' }
    [IO.File]::WriteAllBytes((Join-Path $root 'firmware.dfu'), [byte[]](9,8,7,6))

    # Reject duplicate checksum names that could conceal mixed runs.
    $manifestPath = Join-Path $root 'SHA256SUMS.txt'
    $validManifest = [IO.File]::ReadAllText($manifestPath)
    [IO.File]::WriteAllText($manifestPath,
        "$fapHash  labmate.fap" + [Environment]::NewLine +
        "$fapHash  labmate.fap" + [Environment]::NewLine)
    & ./scripts/verify-v18-matched-pair.ps1 -PairDirectory $root -ExpectedSourceSha $source
    if ($LASTEXITCODE -eq 0) { throw 'Duplicate FAP hash entries were accepted.' }
    [IO.File]::WriteAllText($manifestPath, $validManifest)

    [IO.File]::WriteAllText((Join-Path $root 'PROVENANCE.txt'),
        $provenance.Replace($base, ('c' * 40)))
    & ./scripts/verify-v18-matched-pair.ps1 -PairDirectory $root -ExpectedSourceSha $source
    if ($LASTEXITCODE -eq 0) { throw 'Wrong Momentum base was accepted.' }
    [IO.File]::WriteAllText((Join-Path $root 'PROVENANCE.txt'), $provenance)

    Remove-Item -LiteralPath (Join-Path $root 'firmware.dfu')
    & ./scripts/verify-v18-matched-pair.ps1 -PairDirectory $root
    if ($LASTEXITCODE -eq 0) { throw 'Missing firmware was accepted.' }

    Write-Host 'Read-only v1.8 matching-pair Windows mock PASS (no COM or flashing).'
    $global:LASTEXITCODE = 0
} finally {
    if (Test-Path -LiteralPath $root) {
        Remove-Item -LiteralPath $root -Recurse -Force
    }
}
