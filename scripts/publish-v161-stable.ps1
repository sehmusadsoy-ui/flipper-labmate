# Publish verified LabMate v1.6.1 Stable from the previously prepared folder.
# This script does not change main or overwrite existing releases/tags.
[CmdletBinding()]
param([string]$PackageDir = (Join-Path $HOME 'LabMate-v1.6.1-Stable'))
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$tag = 'v1.6.1'
$source = 'bc63271afe572c393c1febd0f0ef7039404bc937'
$runId = '38057529062'
$expectedSha256 = 'DA2B09D40608A5BF237A9D682E2802EBDA68942DA887CF0E4F3FE5DE9F105F79'

if(-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI (gh) missing.' }
$info = & gh run view $runId -R $repo --json headSha,conclusion | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $info.conclusion -ne 'success' -or $info.headSha -ne $source) {
    throw 'Successful CI source mismatch. Not publishing.'
}
$existing = & gh release list -R $repo --json tagName --limit 100
if($LASTEXITCODE -ne 0) { throw 'Cannot list existing releases.' }
if(@($existing | ConvertFrom-Json | Where-Object { $_.tagName -eq $tag }).Count -gt 0) {
    throw 'Stable release already exists. Refusing overwrite.'
}
# A standalone tag also blocks a release. 404 is an expected nonzero exit.
& cmd.exe /d /s /c "gh api repos/$repo/git/ref/tags/$tag 1>NUL 2>NUL"
if($LASTEXITCODE -eq 0) { throw 'Stable tag already exists. Refusing overwrite.' }
if($LASTEXITCODE -ne 1) { throw "Tag check failed (exit $LASTEXITCODE)." }

$fap = Join-Path $PackageDir 'labmate.fap'
$sum = Join-Path $PackageDir 'SHA256SUMS.txt'
$notes = Join-Path $PackageDir 'RELEASE_NOTES.md'
foreach($file in @($fap, $sum, $notes)) {
    if(-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing: $file" }
}
if((Get-Item -LiteralPath $fap).Length -eq 0) { throw 'Empty FAP.' }
$hashList = @(
    Get-Content -LiteralPath $sum | ForEach-Object {
        if($_ -match '^(?<hash>[A-Fa-f0-9]{64})\s+\*?(?<file>.+?)\s*$' -and
            ($Matches['file'] -ceq 'labmate.fap' -or $Matches['file'] -ceq './labmate.fap')) {
            $Matches['hash']
        }
    }
)
if($hashList.Count -ne 1) { throw 'Manifest must contain exactly one FAP SHA256.' }
$actual = (Get-FileHash -LiteralPath $fap -Algorithm SHA256).Hash
if($actual -ne $expectedSha256 -or $hashList[0].ToUpperInvariant() -ne $actual) {
    throw 'SHA256 mismatch. Not publishing.'
}
Write-Host 'Source, CI and SHA256 verified.' -ForegroundColor Green

& gh release create $tag $fap $sum -R $repo --target $source --title 'LabMate v1.6.1 Stable' --notes-file $notes --latest
if($LASTEXITCODE -ne 0) { throw 'Release creation failed.' }
$release = & gh release view $tag -R $repo --json tagName,isPrerelease,isDraft,url,assets | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $release.tagName -ne $tag -or $release.isPrerelease -or $release.isDraft) {
    throw 'Release status verification failed.'
}
$names = @($release.assets | ForEach-Object { $_.name })
if('labmate.fap' -notin $names -or 'SHA256SUMS.txt' -notin $names) {
    throw 'Required release assets missing.'
}
$resolved = & gh api "repos/$repo/commits/$tag" --jq .sha
if($LASTEXITCODE -ne 0 -or [string]$resolved -ne $source) {
    throw 'Stable tag is not the tested firmware source.'
}
Write-Host "PUBLISHED STABLE: $($release.url)" -ForegroundColor Green
Write-Host "SOURCE: $source"
Write-Host "SHA256: $actual"
