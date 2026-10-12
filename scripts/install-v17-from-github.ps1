# LabMate v1.7 RC1 / future Stable: checksum-verified, single-FAP USB installer.
# RC1 can be installed now; Stable will work only after the official non-prerelease
# v1.7 tag and release exist. Never installs FAP from a moving branch.
[CmdletBinding()]
param(
    [ValidateSet('RC1', 'Stable')]
    [string]$Channel = 'Stable',
    [string]$FirmwareRoot = (Join-Path $HOME 'Momentum-Firmware'),
    [ValidatePattern('^(auto|COM[0-9]{1,3})$')]
    [string]$Port = 'auto',
    [switch]$VerifyOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$tag = if($Channel -eq 'Stable') { 'v1.7' } else { 'v1.7-rc1' }
$shouldBePrerelease = $Channel -eq 'RC1'
$rc1Source = 'd55eec032e5f341f39aa7c98915ec2062995e66b'
$rc1FapHash = 'ED2E91A02AB0F720D6B48EAC13D505D37570FB3A4A1F8E8A76D59E1B79FE14AA'
$tempDir = $null

try {
    if($env:OS -ne 'Windows_NT') { throw 'Windows required.' }
    if(-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'GitHub CLI missing: install gh and authenticate with gh auth login.'
    }
    & gh auth status --hostname github.com 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0) { throw 'Run gh auth login and retry.' }

    $refJson = & gh api "repos/$repo/git/ref/tags/$tag"
    if($LASTEXITCODE -ne 0) { throw "Official $tag tag not found." }
    $ref = ($refJson -join "`n") | ConvertFrom-Json
    if($ref.object.type -ne 'commit' -or $ref.object.sha -notmatch '^[0-9a-fA-F]{40}$') {
        throw 'Release tag must point directly to an immutable commit.'
    }
    $tagCommit = [string]$ref.object.sha

    $releaseJson = & gh api "repos/$repo/releases/tags/$tag"
    if($LASTEXITCODE -ne 0) { throw "Official $tag release not found." }
    $release = ($releaseJson -join "`n") | ConvertFrom-Json
    if($release.tag_name -ne $tag -or $release.draft -or
       [bool]$release.prerelease -ne $shouldBePrerelease) {
        throw 'Unexpected release channel or draft status.'
    }
    if($release.target_commitish -ne $tagCommit) {
        throw 'Published release source differs from its tag.'
    }
    if($Channel -eq 'RC1' -and $tagCommit -ne $rc1Source) {
        throw 'RC1 tag moved from its device-tested commit.'
    }
    $fapAssets = @($release.assets | Where-Object { $_.name -ceq 'labmate.fap' })
    $sumAssets = @($release.assets | Where-Object { $_.name -ceq 'SHA256SUMS.txt' })
    if($fapAssets.Count -ne 1 -or $sumAssets.Count -ne 1) {
        throw 'Release must contain exactly one FAP and checksum asset.'
    }

    $tempDir = Join-Path $env:TEMP ("LabMate-v17-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    & gh release download $tag -R $repo -p labmate.fap -p SHA256SUMS.txt -D $tempDir
    if($LASTEXITCODE -ne 0) { throw 'Release download failed.' }
    $fap = Join-Path $tempDir 'labmate.fap'
    $sum = Join-Path $tempDir 'SHA256SUMS.txt'
    if(-not (Test-Path -LiteralPath $fap) -or -not (Test-Path -LiteralPath $sum) -or
       (Get-Item -LiteralPath $fap).Length -le 0) {
        throw 'Incomplete release download.'
    }
    $entries = @()
    foreach($line in (Get-Content -LiteralPath $sum)) {
        if($line -match '^(?<hash>[A-Fa-f0-9]{64})\s+\*?(?<file>.+?)\s*$') {
            if($Matches['file'] -ceq 'labmate.fap' -or
               $Matches['file'] -ceq './labmate.fap') {
                $entries += $Matches['hash']
            }
        }
    }
    if($entries.Count -ne 1) { throw 'Expected exactly one valid FAP checksum.' }
    $actual = (Get-FileHash -LiteralPath $fap -Algorithm SHA256).Hash
    if(-not [string]::Equals($actual, $entries[0], [StringComparison]::OrdinalIgnoreCase)) {
        throw 'FAP checksum mismatch; nothing installed.'
    }
    if($Channel -eq 'RC1' -and $actual -ine $rc1FapHash) {
        throw 'Unexpected RC1 FAP checksum; nothing installed.'
    }
    Write-Host "RELEASE VERIFIED: $tag ($tagCommit)" -ForegroundColor Cyan
    Write-Host "SHA256 VERIFIED: $actual" -ForegroundColor Green
    if($VerifyOnly) {
        Write-Host 'VerifyOnly complete: no USB installation.'
        exit 0
    }

    $fw = (Resolve-Path -LiteralPath $FirmwareRoot).ProviderPath
    $envCmd = Join-Path $fw 'scripts\toolchain\fbtenv.cmd'
    $runFap = Join-Path $fw 'scripts\runfap.py'
    if(-not (Test-Path -LiteralPath $envCmd) -or -not (Test-Path -LiteralPath $runFap)) {
        throw "Momentum SDK installation scripts are missing from $fw"
    }
    foreach($path in @($envCmd, $runFap, $fap)) {
        if($path -match '["&|<>^%!\r\n]') {
            throw "Unsafe cmd.exe path: $path"
        }
    }
    # Existing FAP is replaced in place. microSD profile/CSV files are not touched.
    $target = '/ext/apps/Tools/labmate.fap'
    $line = 'set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && python "{1}" -p {2} -s "{3}" -t "{4}"' -f $envCmd,$runFap,$Port,$fap,$target
    & cmd.exe /d /s /c $line
    if($LASTEXITCODE -ne 0) { throw "USB installer returned $LASTEXITCODE" }
    Write-Host "SUCCESS: $tag installed to $target" -ForegroundColor Green
    exit 0
}
catch {
    [Console]::Error.WriteLine("LabMate installation FAILED: $($_.Exception.Message)")
    exit 1
}
finally {
    if($tempDir -and (Test-Path -LiteralPath $tempDir)) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
