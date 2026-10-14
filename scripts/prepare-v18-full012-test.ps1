# One-command PowerShell downloader for the exact FULL MNTM-012->LabMate DEV
# candidate. Read-only: NO COM port, NO selfupdate.py, NO FAP install.
# Do not call without a confirmed PASS and known full-package SHA256.
[CmdletBinding()]
param(
    [string]$Directory = (Join-Path $HOME 'Downloads\LabMate-v18DEV-FULL'),
    [ValidatePattern('^[a-fA-F0-9]{64}
    [switch]$VerifyOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = 'sehmusadsoy-ui/flipper-labmate'
$runId = '38611756627'
$artifactName = 'v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH'
$commit = '370bc048dc21d7d58ee69c8e762f5c29705a1c1c'
$base = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
$oldSource = 'e1784e7418d8b074e971983ceb6fef0f37e52ae4'
$expected = @{
    'labmate.fap' = '9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881'
    'firmware.dfu' = 'e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0'
    'firmware-full-update.tgz' = $FullUpdateSha256.ToLowerInvariant()
}
$required = @('labmate.fap','firmware.dfu','firmware-full-update.tgz',
              'SHA256SUMS.txt','PROVENANCE.txt','READ_ME_FIRST.txt')

try {
    if (-not $VerifyOnly) {
        if (Test-Path -LiteralPath $Directory) {
            if (@(Get-ChildItem -LiteralPath $Directory -Force).Count -gt 0) {
                throw 'Hedef klasor bos degil, mevcut dosyalara dokunulmadi.'
            }
        }
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        if (-not $gh) { throw 'GitHub CLI (gh) bulunamadi.' }
        & gh auth status *> $null
        if ($LASTEXITCODE -ne 0) { throw 'gh auth login gerekli.' }
        $detail = (& gh run view $runId --repo $repo --json conclusion,headSha) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or $detail.conclusion -ne 'success' -or
            $detail.headSha -cne $commit) {
            throw 'Tam firmware CI PASS ve kaynak commit dogrulanamadi.'
        }
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
        & gh run download $runId --repo $repo --name $artifactName --dir $Directory
        if ($LASTEXITCODE -ne 0) { throw 'Tam firmware test arsivi indirilemedi.' }
    }
    $dir = (Resolve-Path -LiteralPath $Directory).ProviderPath
    $files = @(Get-ChildItem -LiteralPath $dir -File | ForEach-Object { $_.Name })
    if (@(Get-ChildItem -LiteralPath $dir -Directory).Count -ne 0 -or
        $files.Count -ne $required.Count) {
        throw 'Beklenmeyen dosya sayisi veya alt klasor.'
    }
    foreach ($name in $required) {
        if ($files -cnotcontains $name) { throw "Eksik dosya: $name" }
    }
    foreach ($name in $expected.Keys) {
        $file = Join-Path $dir $name
        if ((Get-Item -LiteralPath $file).Length -eq 0) {
            throw "Bos dosya: $name"
        }
        $sha = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        if (-not $sha.Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "SHA256 UYUSMUYOR: $name"
        }
        Write-Host "SHA256 PASS: $name" -ForegroundColor Green
    }
    $entries = @{}
    $lines = @(Get-Content -LiteralPath (Join-Path $dir 'SHA256SUMS.txt'))
    if ($lines.Count -ne 3) { throw 'Checksum listesi tam olarak 3 satir olmali.' }
    foreach ($line in $lines) {
        if ($line -cnotmatch '^([a-fA-F0-9]{64})\s+\*?(labmate\.fap|firmware\.dfu|firmware-full-update\.tgz)$') {
            throw 'Checksum format hatasi.'
        }
        $filename = $Matches[2]
        if ($entries.ContainsKey($filename)) { throw "Checksum tekrari: $filename" }
        $entries[$filename] = $Matches[1]
    }
    foreach ($name in $expected.Keys) {
        if (-not $entries.ContainsKey($name) -or
            -not $entries[$name].Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "Manifest SHA256 uyusmazligi: $name"
        }
    }
    $sourceText = Get-Content -Raw -LiteralPath (Join-Path $dir 'PROVENANCE.txt')
    if ($sourceText -notmatch "(?m)^LabMate commit: $commit\r?$" -or
        $sourceText -notmatch "(?m)^Momentum base: $base\r?$" -or
        $sourceText -notmatch "(?m)^Installed Momentum012 source: $oldSource\r?$" -or
        $sourceText -notmatch "(?m)^Actions run: $runId\r?$") {
        throw 'Provenans bilgileri eslesmiyor.'
    }
    $warning = Get-Content -Raw -LiteralPath (Join-Path $dir 'READ_ME_FIRST.txt')
    if ($warning -notmatch 'DO NOT FLASH' -or $warning -notmatch 'NOT A RELEASE') {
        throw 'Deneysel test paketi uyarisi eksik.'
    }
    Write-Host ''
    Write-Host 'LABMATE FULL MNTM012 PREPARE PASS' -ForegroundColor Green
    Write-Host "Konum: $dir"
    Write-Host 'SADECE INDIRME/DOGRULAMA. FLASH YOK. TEST PAKETI.'
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate tam test paketi REDDEDILDI: $($_.Exception.Message)")
    exit 1
}
)]
    [string]$FullUpdateSha256 = '5e3267d780a56178e8ff40cb81ca2f6562e81d4d07daf703ab1c7db34e967d0d',
    [switch]$VerifyOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = 'sehmusadsoy-ui/flipper-labmate'
$runId = '38611756627'
$artifactName = 'v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH'
$commit = '370bc048dc21d7d58ee69c8e762f5c29705a1c1c'
$base = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
$oldSource = 'e1784e7418d8b074e971983ceb6fef0f37e52ae4'
$expected = @{
    'labmate.fap' = '9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881'
    'firmware.dfu' = 'e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0'
    'firmware-full-update.tgz' = $FullUpdateSha256.ToLowerInvariant()
}
$required = @('labmate.fap','firmware.dfu','firmware-full-update.tgz',
              'SHA256SUMS.txt','PROVENANCE.txt','READ_ME_FIRST.txt')

try {
    if (-not $VerifyOnly) {
        if (Test-Path -LiteralPath $Directory) {
            if (@(Get-ChildItem -LiteralPath $Directory -Force).Count -gt 0) {
                throw 'Hedef klasor bos degil, mevcut dosyalara dokunulmadi.'
            }
        }
        $gh = Get-Command gh -ErrorAction SilentlyContinue
        if (-not $gh) { throw 'GitHub CLI (gh) bulunamadi.' }
        & gh auth status *> $null
        if ($LASTEXITCODE -ne 0) { throw 'gh auth login gerekli.' }
        $detail = (& gh run view $runId --repo $repo --json conclusion,headSha) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or $detail.conclusion -ne 'success' -or
            $detail.headSha -cne $commit) {
            throw 'Tam firmware CI PASS ve kaynak commit dogrulanamadi.'
        }
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
        & gh run download $runId --repo $repo --name $artifactName --dir $Directory
        if ($LASTEXITCODE -ne 0) { throw 'Tam firmware test arsivi indirilemedi.' }
    }
    $dir = (Resolve-Path -LiteralPath $Directory).ProviderPath
    $files = @(Get-ChildItem -LiteralPath $dir -File | ForEach-Object { $_.Name })
    if (@(Get-ChildItem -LiteralPath $dir -Directory).Count -ne 0 -or
        $files.Count -ne $required.Count) {
        throw 'Beklenmeyen dosya sayisi veya alt klasor.'
    }
    foreach ($name in $required) {
        if ($files -cnotcontains $name) { throw "Eksik dosya: $name" }
    }
    foreach ($name in $expected.Keys) {
        $file = Join-Path $dir $name
        if ((Get-Item -LiteralPath $file).Length -eq 0) {
            throw "Bos dosya: $name"
        }
        $sha = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        if (-not $sha.Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "SHA256 UYUSMUYOR: $name"
        }
        Write-Host "SHA256 PASS: $name" -ForegroundColor Green
    }
    $entries = @{}
    $lines = @(Get-Content -LiteralPath (Join-Path $dir 'SHA256SUMS.txt'))
    if ($lines.Count -ne 3) { throw 'Checksum listesi tam olarak 3 satir olmali.' }
    foreach ($line in $lines) {
        if ($line -cnotmatch '^([a-fA-F0-9]{64})\s+\*?(labmate\.fap|firmware\.dfu|firmware-full-update\.tgz)$') {
            throw 'Checksum format hatasi.'
        }
        $filename = $Matches[2]
        if ($entries.ContainsKey($filename)) { throw "Checksum tekrari: $filename" }
        $entries[$filename] = $Matches[1]
    }
    foreach ($name in $expected.Keys) {
        if (-not $entries.ContainsKey($name) -or
            -not $entries[$name].Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "Manifest SHA256 uyusmazligi: $name"
        }
    }
    $sourceText = Get-Content -Raw -LiteralPath (Join-Path $dir 'PROVENANCE.txt')
    if ($sourceText -notmatch "(?m)^LabMate commit: $commit\r?$" -or
        $sourceText -notmatch "(?m)^Momentum base: $base\r?$" -or
        $sourceText -notmatch "(?m)^Installed Momentum012 source: $oldSource\r?$" -or
        $sourceText -notmatch "(?m)^Actions run: $runId\r?$") {
        throw 'Provenans bilgileri eslesmiyor.'
    }
    $warning = Get-Content -Raw -LiteralPath (Join-Path $dir 'READ_ME_FIRST.txt')
    if ($warning -notmatch 'DO NOT FLASH' -or $warning -notmatch 'NOT A RELEASE') {
        throw 'Deneysel test paketi uyarisi eksik.'
    }
    Write-Host ''
    Write-Host 'LABMATE FULL MNTM012 PREPARE PASS' -ForegroundColor Green
    Write-Host "Konum: $dir"
    Write-Host 'SADECE INDIRME/DOGRULAMA. FLASH YOK. TEST PAKETI.'
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate tam test paketi REDDEDILDI: $($_.Exception.Message)")
    exit 1
}
