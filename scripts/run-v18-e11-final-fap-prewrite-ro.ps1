# E11 v1.8 final-label FAP prewrite phase 1: PC backup ONLY, Flipper READ ONLY.
# This script CANNOT install/upload/flash/reboot or edit Flipper SD files.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port = 'COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'qFlipper acik. Once kapat. NO DEVICE WRITE.'
}
$documents = Join-Path $env:USERPROFILE 'Documents'
if (-not (Test-Path -LiteralPath $documents -PathType Container)) {
    throw 'PC Documents klasoru bulunamadi.'
}

# Reuse only the previously H0 V3 tested Momentum Flipper CLI transport.
$stage = Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $stage) {
    throw 'H0 V3 onceden test edilmis CLI klasoru bulunamadi. DUR.'
}

# Locate old E11 source-matched candidate. The Python gate re-attests
# the complete archive/provenance before opening any serial connection.
$candidate = $null
$roots = @($env:TEMP, (Join-Path $env:USERPROFILE 'Downloads'),
    (Join-Path $env:USERPROFILE 'Desktop'), $documents)
foreach ($root in $roots) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
    $files = Get-ChildItem -LiteralPath $root -File -Filter 'firmware-full-update.tgz' -Recurse -Depth 6 -ErrorAction SilentlyContinue
    foreach ($bundle in $files) {
        $dir = $bundle.DirectoryName
        $app = Join-Path $dir 'labmate.fap'
        $js = Join-Path $dir 'js_gpio.module'
        $dfu = Join-Path $dir 'firmware.dfu'
        if (-not ((Test-Path $app -PathType Leaf) -and (Test-Path $js -PathType Leaf) -and (Test-Path $dfu -PathType Leaf))) { continue }
        if ((Get-FileHash -LiteralPath $bundle.FullName -Algorithm SHA256).Hash -ne '11ED3CDF4E99C9C7218973695D349CD946BE97D21DFC59231113BDE15E94C553') { continue }
        if ((Get-FileHash -LiteralPath $app -Algorithm SHA256).Hash -ne '2B31EC3FA9050580DC3C3FF80138578ED185D70811AA8124EBD2D00B8D981AF0') { continue }
        if ((Get-FileHash -LiteralPath $js -Algorithm SHA256).Hash -ne 'FFF2AB8AD8E5B320B669283FC611216DA99E9CDA4DC03428FCD8E8A130ECCA0A') { continue }
        if ((Get-FileHash -LiteralPath $dfu -Algorithm SHA256).Hash -ne '88D12FEE4EDB4FA0EC042A1B526DDB41B8DB36AEB9554C6A9A8AEF1C37E4E1B0') { continue }
        $candidate = $dir
        break
    }
    if ($candidate) { break }
}
if (-not $candidate) {
    throw 'Eski tam dogrulanmis E11 paketi yerel PC dosyalarinda bulunamadi. DUR.'
}

# Provenance pin: this specific helper revision passed mock-only CI
# #39040745306. Fresh PC files only, no edit to the older H0 stage.
$pin = '7e49d33ea0020f79afbdec21679521c3a10e0bac'
$codeDir = Join-Path $env:TEMP ('LabMate-v18-Prewrite-CODE-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $codeDir -ErrorAction Stop | Out-Null
$sourceFiles = @(
    'audit_v18_e11_live_labmate_sd.py',
    'check_v18_full_update_bundle.py',
    'preflight_v18_e11_local.py',
    'verify_v18_full_review_pair.py',
    'stage_v18_e11_review_only.py',
    'check_v18_e11_postupdate_readonly.py',
    'check_v18_e11_h_js_runtime_ro.py',
    'check_v18_e11_final_fap_prewrite_ro.py'
)
foreach ($name in $sourceFiles) {
    $url = "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$pin/scripts/$name"
    $target = Join-Path $codeDir $name
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or (Get-Item -LiteralPath $target).Length -eq 0) {
        throw "Sabitlenmis salt-okunur dosya indirilemedi: $name"
    }
}
$backupRoot = Join-Path $documents 'LabMate-FAP-PC-Backups'
if (-not (Test-Path -LiteralPath $backupRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $backupRoot -ErrorAction Stop | Out-Null
}
$backup = Join-Path $backupRoot ('E11-before-v18-final-' + [guid]::NewGuid().ToString('N'))

Write-Host 'E11 FINAL - READ-ONLY IDENTITY AND PC OLD-FAP BACKUP' -ForegroundColor Cyan
Write-Host 'Operator: LabMate fully exited, PWM STOP, no GPIO leads, qFlipper closed.'
Write-Host "Old paired candidate: $candidate"
Write-Host "New PC backup folder: $backup"
$pyArgs = @(
    '-3', (Join-Path $codeDir 'check_v18_e11_final_fap_prewrite_ro.py'),
    '--port', $Port,
    '--momentum-scripts', $stage.FullName,
    '--old-candidate', $candidate,
    '--pc-backup', $backup
)
& py @pyArgs
if ($LASTEXITCODE -ne 0) {
    throw 'E11 PREWRITE REFUSED - NO DEVICE WRITE. Ciktiyi paylas, tekrar deneme.'
}
Write-Host 'E11 FINAL PREWRITE PC FAP BACKUP PASS; DEVICE READ ONLY.' -ForegroundColor Green
Write-Host "Saved old FAP on PC: $backup" -ForegroundColor Cyan
Write-Host 'BURADA DUR: Yeni FAP henuz yuklenmedi.' -ForegroundColor Yellow
