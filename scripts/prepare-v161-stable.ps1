# Prepare (DO NOT PUBLISH) the tested LabMate v1.6.1 Stable package.
[CmdletBinding()]
param([string]$OutputDirectory = (Join-Path $HOME 'LabMate-v1.6.1-Stable'))
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$sourceSha = 'bc63271afe572c393c1febd0f0ef7039404bc937'
$runId = '38057529062'
$tag = 'v1.6.1'

if(-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Missing GitHub CLI.' }
$runInfo = & gh run view $runId -R $repo --json headSha,conclusion | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $runInfo.conclusion -ne 'success' -or $runInfo.headSha -ne $sourceSha) {
    throw 'CI status/source mismatch.'
}
if(Test-Path -LiteralPath $OutputDirectory) {
    if(@(Get-ChildItem -LiteralPath $OutputDirectory -Force).Count -gt 0) {
        throw 'Output directory is not empty. Refusing to overwrite files.'
    }
} else {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}
& gh run download $runId -R $repo -n labmate -D $OutputDirectory
if($LASTEXITCODE -ne 0) { throw 'Artifact download failed.' }
$fap = Join-Path $OutputDirectory 'labmate.fap'
$sum = Join-Path $OutputDirectory 'SHA256SUMS.txt'
if(-not (Test-Path $fap) -or -not (Test-Path $sum)) { throw 'Missing FAP/checksum asset.' }
$hashList = @(
    Get-Content $sum | ForEach-Object {
        if($_ -match '^(?<hash>[A-Fa-f0-9]{64})\s+\*?(?<file>.+?)\s*$' -and
            ($Matches['file'] -ceq 'labmate.fap' -or $Matches['file'] -ceq './labmate.fap')) {
            $Matches['hash']
        }
    }
)
if($hashList.Count -ne 1) { throw 'Expected exactly one labmate.fap checksum.' }
if((Get-Item $fap).Length -eq 0) { throw 'Empty FAP.' }
$actual = (Get-FileHash $fap -Algorithm SHA256).Hash
if(-not [string]::Equals($actual, $hashList[0], [StringComparison]::OrdinalIgnoreCase)) {
    throw 'SHA256 mismatch.'
}
$notes = @'
# LabMate v1.6.1 Stable — proposed release notes

For Momentum Firmware / Flipper Zero.

## Improvements
- Frequency Meter LOW PC1 / HIGH PB3 and Pulse Analyzer reliability.
- Modular logger codec/storage, read-only Log History and backward-compatible CSV.
- Centralized capture ownership, EXTI cleanup and protected TIM1/PA7 background PWM.
- Grouped navigation and Profiles save/load persistence.
- INFO screen displays SauronLAB, Sehmus, repository address and 3.3V GPIO warning.

## Verification
- Firmware source: bc63271afe572c393c1febd0f0ef7039404bc937
- GitHub Actions: 38057529062 SUCCESS.
- Earlier full Gate A: 8/8 PASS and Gate B: 6/6 PASS on RC1 source.
- INFO follow-up: 3/3 PASS on this Stable candidate (operator reports).
- Earlier broad tests do not constitute an independent full Gate B on this newer source.
- Normal operation coverage; not certified metrology or fault-injection qualification.

Target: /ext/apps/Tools/labmate.fap
Only 3.3 V compatible GPIO signals. Existing v1.6 and RC1 releases remain unchanged.
'@
Set-Content -LiteralPath (Join-Path $OutputDirectory 'RELEASE_NOTES.md') -Value $notes -Encoding UTF8
Write-Host "STABLE PACKAGE VERIFIED (NOT PUBLISHED)" -ForegroundColor Green
Write-Host "Source: $sourceSha"
Write-Host "Build: $runId"
Write-Host "SHA256: $actual"
Write-Host "Folder: $OutputDirectory"
