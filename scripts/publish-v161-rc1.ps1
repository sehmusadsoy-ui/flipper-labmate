# Publish the already-tested LabMate v1.6.1 RC without modifying main or v1.6 Stable.
# Requires an authenticated GitHub CLI with release write permissions.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$sourceSha = '9c087b64504083e5f977544bc27cd9ce37840819'
$runId = '38056474953'
$tag = 'v1.6.1-rc.1'
$temp = Join-Path $env:TEMP ('labmate-release-' + [guid]::NewGuid().ToString('N'))
try {
    if(-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Missing GitHub CLI (gh).' }
    & gh auth status --hostname github.com 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0) { throw 'Please run gh auth login first.' }

    $existing = & gh release list -R $repo --json tagName --limit 100
    if($LASTEXITCODE -ne 0) { throw 'Cannot check existing releases.' }
    if(@($existing | ConvertFrom-Json | Where-Object { $_.tagName -eq $tag }).Count -gt 0) {
        throw "Release $tag already exists; refusing to overwrite."
    }
    # A tag with no release must also be considered reserved.
    # GitHub returns 404 for a tag that does not exist. PowerShell 5.1
    # converts native stderr to an error under Stop; use a clean exit-code
    # probe and preserve any unexpected API/authentication errors.
    $tagProbe = & cmd.exe /d /s /c "gh api repos/$repo/git/ref/tags/$tag 2>NUL"
    if($LASTEXITCODE -eq 0) { throw "Tag $tag already exists; refusing to move it." }
    if($LASTEXITCODE -ne 1) {
        throw "Could not safely verify the absence of tag $tag (exit $LASTEXITCODE)."
    }

    $runInfo = & gh run view $runId -R $repo --json headSha,conclusion | ConvertFrom-Json
    if($LASTEXITCODE -ne 0 -or $runInfo.conclusion -ne 'success' -or $runInfo.headSha -ne $sourceSha) {
        throw 'Candidate workflow commit or SUCCESS status mismatch.'
    }
    New-Item -ItemType Directory -Path $temp -Force | Out-Null
    & gh run download $runId -R $repo -n labmate -D $temp
    if($LASTEXITCODE -ne 0) { throw 'Artifact download failed.' }
    $fap = Join-Path $temp 'labmate.fap'
    $sum = Join-Path $temp 'SHA256SUMS.txt'
    if(-not (Test-Path -LiteralPath $fap) -or -not (Test-Path -LiteralPath $sum)) {
        throw 'Missing labmate.fap or SHA256SUMS.txt in tested artifact.'
    }
    $hashList = @(
        Get-Content -LiteralPath $sum | ForEach-Object {
            if($_ -match '^(?<hash>[A-Fa-f0-9]{64})\s+\*?(?<file>.+?)\s*$' -and
               ($Matches['file'] -ceq 'labmate.fap' -or $Matches['file'] -ceq './labmate.fap')) {
                $Matches['hash']
            }
        }
    )
    if($hashList.Count -ne 1) { throw 'Expected exactly one FAP checksum.' }
    $actual = (Get-FileHash -LiteralPath $fap -Algorithm SHA256).Hash
    if(-not [string]::Equals($actual, $hashList[0], [StringComparison]::OrdinalIgnoreCase)) {
        throw 'SHA256 MISMATCH: release cancelled.'
    }
    if((Get-Item -LiteralPath $fap).Length -eq 0) { throw 'FAP is empty.' }
    Write-Host 'Verified: GitHub Actions SUCCESS, source SHA, and FAP SHA256.' -ForegroundColor Green

    $notes = @'
LabMate v1.6.1 Release Candidate 1 (Momentum Firmware)

This is a pre-release, not v1.6 Stable.

Highlights:
- Frequency Meter LOW PC1 / HIGH PB3 capture and Pulse Analyzer improvements.
- Modular Logger codec/storage, read-only Log History and pulse/frequency math.
- Consolidated capture ownership and EXTI cleanup, with TIM1/PA7 generator isolation.
- Grouped navigation, Profiles S1 persistence and CSV compatibility.

Validation:
- Exact firmware source: 9c087b64504083e5f977544bc27cd9ce37840819
- GitHub Actions: 38056474953 (SUCCESS).
- Physical Gate A: 8/8 PASS (operator report).
- Physical Gate B: 6/6 PASS (operator report).
- This is normal-operation regression testing, not precision certification or fault-injection qualification.

Install target: /ext/apps/Tools/labmate.fap
GPIO: 3.3 V compatible signals only.
Existing v1.6 Stable release and main branch are unchanged.
'@
    $notesFile = Join-Path $temp 'RELEASE_NOTES.md'
    Set-Content -LiteralPath $notesFile -Value $notes -Encoding UTF8

    & gh release create $tag $fap $sum -R $repo --target $sourceSha `
        --title 'LabMate v1.6.1 RC1' --prerelease --notes-file $notesFile
    if($LASTEXITCODE -ne 0) { throw 'GitHub pre-release creation failed.' }

    $release = & gh release view $tag -R $repo --json isPrerelease,tagName,url,assets | ConvertFrom-Json
    if($LASTEXITCODE -ne 0 -or -not $release.isPrerelease -or $release.tagName -ne $tag) {
        throw 'Release verification failed.'
    }
    $names = @($release.assets | ForEach-Object { $_.name })
    if('labmate.fap' -notin $names -or 'SHA256SUMS.txt' -notin $names) {
        throw 'Release missing required assets.'
    }
    # Resolve lightweight or annotated tags via the GitHub commit API.
    $resolved = & gh api "repos/$repo/commits/$tag" --jq .sha
    if($LASTEXITCODE -ne 0 -or [string]$resolved -ne $sourceSha) {
        throw 'Release tag does not resolve to the tested firmware commit.'
    }
    Write-Host "PUBLISHED: $($release.url)" -ForegroundColor Green
    Write-Host "Source: $sourceSha" -ForegroundColor Green
}
finally {
    if(Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
