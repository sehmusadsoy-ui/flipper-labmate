# Installs successful LabMate v1.6 v1.6.1 dev build directly from GitHub.
# Requires GitHub CLI with one-time "gh auth login" authentication.
[CmdletBinding()]
param(
    [string]$FirmwareRoot = (Join-Path $HOME 'Momentum-Firmware'),
    [ValidatePattern('^(auto|COM[0-9]{1,3})$')]
    [string]$Port = 'COM7'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$target = '/ext/apps/Tools/labmate.fap'
$tempDir = $null

try {
    if($env:OS -ne 'Windows_NT') { throw 'Requires Windows PowerShell.' }
    if(-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'Missing gh. Install once: winget install --id GitHub.cli --exact'
    }
    & gh auth status --hostname github.com 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0) { throw 'Run gh auth login once, then retry.' }

    $data = & gh run list -R $repo -w build-v1.6.yml -b v1.6.1-dev -s success -L 1 --json databaseId,headSha
    if($LASTEXITCODE -ne 0) { throw 'Unable to query GitHub Actions.' }
    $runs = @($data | ConvertFrom-Json)
    if($runs.Count -ne 1 -or -not $runs[0].databaseId) {
        throw 'No successful v1.6.1-dev build found.'
    }
    # An older successful Actions run is not sufficient after a new candidate
    # commit; do not silently install a stale build while CI is pending.
    $headSha = & gh api "repos/$repo/branches/v1.6.1-dev" --jq .commit.sha
    if($LASTEXITCODE -ne 0 -or -not $headSha) {
        throw 'Unable to verify latest v1.6.1 dev branch head.'
    }
    if($runs[0].headSha -ne [string]$headSha) {
        throw 'Latest v1.6.1 dev commit does not yet have a successful build.'
    }
    $runId = [string]$runs[0].databaseId
    Write-Host "LabMate v1.6.1 dev build $runId (commit $($runs[0].headSha))" -ForegroundColor Cyan

    $tempDir = Join-Path $env:TEMP ('LabMate-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    & gh run download $runId -R $repo -n labmate -D $tempDir
    if($LASTEXITCODE -ne 0) { throw 'GitHub artifact download failed.' }

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
