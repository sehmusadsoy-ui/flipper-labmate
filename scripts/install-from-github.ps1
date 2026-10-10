# Install the published LabMate v1.6 Stable FAP from its immutable GitHub Release.
# Requires GitHub CLI, 'gh auth login', and a compatible local Momentum SDK.
[CmdletBinding()]
param(
    [string]$FirmwareRoot = (Join-Path $HOME 'Momentum-Firmware'),
    [ValidatePattern('^(auto|COM[0-9]{1,3})$')]
    [string]$Port = 'COM7'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$tag = 'v1.6'
$expectedCommit = '4a890002fea0acf8d524b7c772db3bbd3e239848'
$target = '/ext/apps/Tools/labmate.fap'
$tempDir = $null

try {
    if($env:OS -ne 'Windows_NT') { throw 'Requires Windows PowerShell.' }
    if(-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'Missing gh. Install once: winget install --id GitHub.cli --exact'
    }
    & gh auth status --hostname github.com 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0) { throw 'Run gh auth login once, then retry.' }

    # Stable means the published release/tag, never the mutable
    # development, RC1, or Stable candidate workflow head.
    $tagSha = & gh api "repos/$repo/git/ref/tags/$tag" --jq .object.sha
    if($LASTEXITCODE -ne 0 -or -not $tagSha) {
        throw 'Unable to verify v1.6 Stable Git tag.'
    }
    if([string]$tagSha -ne $expectedCommit) {
        throw 'v1.6 Stable tag differs from the verified release commit.'
    }

    $releaseJson = & gh api "repos/$repo/releases/tags/$tag"
    if($LASTEXITCODE -ne 0 -or -not $releaseJson) {
        throw 'Could not read the published Stable release metadata.'
    }
    $release = ($releaseJson -join "`n") | ConvertFrom-Json
    if($release.tag_name -ne $tag -or $release.draft -or $release.prerelease) {
        throw 'Expected published non-prerelease v1.6 Stable.'
    }
    $fapAsset = @($release.assets | Where-Object { $_.name -ceq 'labmate.fap' })
    $sumAsset = @($release.assets | Where-Object { $_.name -ceq 'SHA256SUMS.txt' })
    if($fapAsset.Count -ne 1 -or $sumAsset.Count -ne 1) {
        throw 'Missing or duplicated official Stable release assets.'
    }

    Write-Host "Official LabMate $tag Stable (commit $expectedCommit)" -ForegroundColor Cyan
    $tempDir = Join-Path $env:TEMP ('LabMate-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    & gh release download $tag -R $repo -p labmate.fap -p SHA256SUMS.txt -D $tempDir
    if($LASTEXITCODE -ne 0) { throw 'Unable to download official Stable assets.' }

    $fap = Join-Path $tempDir 'labmate.fap'
    $sum = Join-Path $tempDir 'SHA256SUMS.txt'
    if(-not [IO.File]::Exists($fap) -or -not [IO.File]::Exists($sum)) {
        throw 'Missing labmate.fap or SHA256SUMS.txt.'
    }
    if((Get-Item -LiteralPath $fap).Length -eq 0) { throw 'Empty FAP.' }
    $hashes = @()
    foreach($line in (Get-Content -LiteralPath $sum)) {
        if($line -match '^(?<hash>[A-Fa-f0-9]{64})\s+\*?(?<file>.+?)\s*$') {
            if($Matches['file'] -ceq 'labmate.fap' -or $Matches['file'] -ceq './labmate.fap') {
                $hashes += $Matches['hash']
            }
        }
    }
    if($hashes.Count -ne 1) { throw 'Expected one labmate.fap SHA256.' }
    $actual = (Get-FileHash -LiteralPath $fap -Algorithm SHA256).Hash
    if(-not [string]::Equals($actual, $hashes[0], [StringComparison]::OrdinalIgnoreCase)) {
        throw 'SHA256 mismatch. Installation cancelled.'
    }
    Write-Host 'SHA256 OK' -ForegroundColor Green

    $fw = (Resolve-Path -LiteralPath $FirmwareRoot).ProviderPath
    $fbtenv = Join-Path $fw 'scripts\toolchain\fbtenv.cmd'
    $runfap = Join-Path $fw 'scripts\runfap.py'
    if(-not [IO.File]::Exists($fbtenv) -or -not [IO.File]::Exists($runfap)) {
        throw "Momentum scripts missing from $fw"
    }
    foreach($path in @($fbtenv,$runfap,$fap)) {
        if($path -match '["&|<>^%!\r\n]') { throw "Unsafe CMD path: $path" }
    }

    $line = 'set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && python "{1}" -p {2} -s "{3}" -t "{4}"' -f $fbtenv, $runfap, $Port, $fap, $target
    Write-Host "Installing labmate.fap via $Port" -ForegroundColor Yellow
    & cmd.exe /d /s /c $line
    if($LASTEXITCODE -ne 0) { throw "Flipper returned exit code $LASTEXITCODE" }
    Write-Host 'SUCCESS: LabMate installed and app launch requested.' -ForegroundColor Green
    exit 0
}
catch {
    [Console]::Error.WriteLine("LabMate error: $($_.Exception.Message)")
    exit 1
}
finally {
    if($tempDir -and (Test-Path -LiteralPath $tempDir)) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
