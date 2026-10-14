# LabMate v1.8DEV: prepare the exact CI-verified matched test bundle.
# Downloads and SHA256-verifies only. NEVER opens a COM port or flashes.
[CmdletBinding()]
param(
    [string]$Directory = (Join-Path $HOME 'Downloads\LabMate-v18DEV-test'),
    [switch]$VerifyOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'sehmusadsoy-ui/flipper-labmate'
$run = '38587659583'
$artifact = 'v18DEV-minimal-updater-FAP-UNTESTED-DO-NOT-FLASH'
$source = '0fdd558291222c54f5b52b762e00fafffa3d0d62'
$momentum = 'd3f89dfe2ef6b01839201598e9be1590cba80322'
$expected = @{
    'labmate.fap' = '9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881'
    'firmware.dfu' = 'e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0'
    'firmware-update.tgz' = 'b796b42cb5756fc8bb2bb3180ae2c2cb00775b3f88ceceae1025299a2f424ad2'
}
$expectedNames = @(
    'labmate.fap', 'firmware.dfu', 'firmware-update.tgz',
    'SHA256SUMS.txt', 'PROVENANCE.txt', 'READ_ME_FIRST.txt'
)

try {
    if (-not $VerifyOnly) {
        if (Test-Path -LiteralPath $Directory) {
            if (@(Get-ChildItem -LiteralPath $Directory -Force).Count -ne 0) {
                throw 'Hedef klasor bos degil. Mevcut dosyalarin uzerine yazilmadi.'
            }
        }
        $gh = Get-Command 'gh' -ErrorAction SilentlyContinue
        if (-not $gh) { throw 'GitHub CLI (gh) bulunamadi. Kurulum/oturum acma gerekli.' }
        & gh auth status *> $null
        if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI girisi gerekli: gh auth login' }
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
        # Repository artifact rather than release; no Stable tag/asset modification.
        & gh run download $run --repo $repo --name $artifact --dir $Directory
        if ($LASTEXITCODE -ne 0) { throw 'GitHub test arsivi indirilemedi.' }
    }
    $dir = (Resolve-Path -LiteralPath $Directory).ProviderPath
    $files = @(Get-ChildItem -LiteralPath $dir -File)
    if (@(Get-ChildItem -LiteralPath $dir -Directory).Count -ne 0 -or
        $files.Count -ne $expectedNames.Count) {
        throw 'Arsivde beklenmeyen veya eksik dosya var.'
    }
    foreach ($name in $expectedNames) {
        if ($files.Name -cnotcontains $name) { throw "Dosya eksik: $name" }
    }
    foreach ($name in $expected.Keys) {
        $file = Join-Path $dir $name
        if ((Get-Item -LiteralPath $file).Length -le 0) { throw "Bos dosya: $name" }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        if (-not $actual.Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "SHA256 hatasi: $name. Cihaza hicbir sey yuklenmedi."
        }
        Write-Host "SHA256 PASS: $name" -ForegroundColor Green
    }
    $sumLines = @(Get-Content -LiteralPath (Join-Path $dir 'SHA256SUMS.txt'))
    if ($sumLines.Count -ne $expected.Count) { throw 'SHA256 listesinde 3 satir olmali.' }
    $entries = @{}
    foreach ($line in $sumLines) {
        if ($line -notmatch '^([a-fA-F0-9]{64})\s+\*?(labmate\.fap|firmware\.dfu|firmware-update\.tgz)$') {
            throw 'Beklenmeyen checksum satiri.'
        }
        $name = $Matches[2]
        if ($entries.ContainsKey($name)) { throw 'Tekrarlanan checksum satiri.' }
        $entries[$name] = $Matches[1]
    }
    foreach ($name in $expected.Keys) {
        if (-not $entries.ContainsKey($name) -or
            -not $entries[$name].Equals($expected[$name], [StringComparison]::OrdinalIgnoreCase)) {
            throw "Checksum listesi uyumsuz: $name"
        }
    }
    $provenance = Get-Content -Raw -LiteralPath (Join-Path $dir 'PROVENANCE.txt')
    if ($provenance -notmatch "(?m)^LabMate commit: $source\r?$" -or
        $provenance -notmatch "(?m)^Momentum base commit: $momentum\r?$" -or
        $provenance -notmatch "(?m)^GitHub Actions run: $run\r?$" -or
        $provenance -notmatch '(?m)^Patched HAL source diff SHA256: [a-f0-9]{64}\r?$') {
        throw 'Kaynak/koken kaydi dogrulanamadi.'
    }
    $warning = Get-Content -Raw -LiteralPath (Join-Path $dir 'READ_ME_FIRST.txt')
    if ($warning -notmatch 'DO NOT' -or $warning -notmatch 'NOT AN APPROVED') {
        throw 'Deneysel firmware uyari dosyasi eksik.'
    }
    Write-Host ''
    Write-Host 'LabMate v1.8DEV PREPARE PASS.' -ForegroundColor Green
    Write-Host "Dogrulanan dosyalar: $dir"
    Write-Host 'SADECE INDIRME/DOGRULAMA. FIRMWARE FLASH: YAPILMADI.'
    Write-Host 'Sonraki adim: mevcut Momentum surumu, yedek ve geri donus kontrolu.'
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate hazirlik hatasi: $($_.Exception.Message)")
    exit 1
}
