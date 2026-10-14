# LabMate v1.8DEV FULL firmware trial. Never silently flash.
# Stage-only default; -Apply requires verified backups and typed YUKLE.
[CmdletBinding()]
param(
    [string]$BundleDirectory = (Join-Path $HOME 'Downloads\LabMate-v18DEV-FULL'),
    [string]$RollbackDirectory = (Join-Path $HOME 'Downloads\LabMate-Rollback-MNTM012'),
    [string]$LabMateBackupDirectory = (Join-Path $HOME 'Downloads\LabMate-Backup-20261014-201529'),
    [string]$SettingsBackupPath = (Join-Path $HOME 'Downloads\Uybelav-backup-20261014-201804.tgz'),
    [string]$FirmwareRoot = (Join-Path $HOME 'Momentum-Firmware'),
    [ValidatePattern('^(auto|COM[0-9]{1,3})$')]
    [string]$Port = 'auto',
    [switch]$Apply
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$expected = @{
    'firmware-full-update.tgz' = '5e3267d780a56178e8ff40cb81ca2f6562e81d4d07daf703ab1c7db34e967d0d'
    'firmware.dfu' = 'e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0'
    'labmate.fap' = '9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881'
}
$oldHashes = @{
    'flipper-z-f7-update-mntm-012.tgz' = '1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7'
    'labmate-v18-stable.fap' = '119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0'
}
$rootName = 'f7-update-mntm-HEAD-d3f89dfe'
$archiveEntries = @(
    $rootName, "$rootName/firmware.dfu", "$rootName/firstboot.bin",
    "$rootName/radio.bin", "$rootName/resources.tar.gz",
    "$rootName/splash.bin", "$rootName/update.fuf", "$rootName/updater.bin"
)

function Assert-Digest([string]$Path, [string]$Sha) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing file: $Path"
    }
    if ((Get-Item -LiteralPath $Path).Length -le 0) {
        throw "Empty file: $Path"
    }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    if (-not [string]::Equals($actual, $Sha, [StringComparison]::OrdinalIgnoreCase)) {
        throw "SHA256 MISMATCH: $Path (NO DEVICE CHANGES)"
    }
    Write-Host "SHA256 PASS: $([IO.Path]::GetFileName($Path))" -ForegroundColor Green
}

try {
    $bundle = (Resolve-Path -LiteralPath $BundleDirectory).ProviderPath
    foreach ($name in $expected.Keys) {
        Assert-Digest (Join-Path $bundle $name) $expected[$name]
    }
    $tgz = Join-Path $bundle 'firmware-full-update.tgz'
    if (-not (Get-Command tar.exe -ErrorAction SilentlyContinue)) {
        throw 'Windows tar.exe not found.'
    }
    $listed = @(& tar.exe -tzf $tgz | ForEach-Object { $_.TrimEnd('/') })
    if ($LASTEXITCODE -ne 0 -or $listed.Count -ne $archiveEntries.Count) {
        throw 'Updater TGZ listing is incomplete or unexpected.'
    }
    foreach ($entry in $listed) {
        if ($entry -cnotin $archiveEntries) {
            throw "Unexpected updater archive member: $entry"
        }
    }
    if (@($listed | Select-Object -Unique).Count -ne $archiveEntries.Count) {
        throw 'Duplicate updater archive member.'
    }

    $stage = Join-Path $bundle 'full-updater-stage'
    $updatePath = Join-Path $stage $rootName
    if (Test-Path -LiteralPath $stage) {
        if (@(Get-ChildItem -LiteralPath $stage -Force).Count -gt 0 -and
            -not (Test-Path -LiteralPath (Join-Path $updatePath 'update.fuf') -PathType Leaf)) {
            throw "Stage directory has unexpected contents: $stage"
        }
    } else {
        New-Item -ItemType Directory -Path $stage | Out-Null
    }
    if (-not (Test-Path -LiteralPath (Join-Path $updatePath 'update.fuf') -PathType Leaf)) {
        & tar.exe -xzf $tgz -C $stage
        if ($LASTEXITCODE -ne 0) { throw 'Updater TGZ extraction failed.' }
    }
    $manifest = Join-Path $updatePath 'update.fuf'
    Assert-Digest (Join-Path $updatePath 'firmware.dfu') $expected['firmware.dfu']
    Assert-Digest (Join-Path $updatePath 'radio.bin') '134a9af448d2bc35995600c9e95723a387c144c2d1adea671086f16f95d327df'
    $m = Get-Content -Raw -LiteralPath $manifest
    foreach ($line in @(
        'Target: 7', 'Firmware: firmware.dfu', 'Radio: radio.bin',
        'Resources: resources.tar.gz', 'Loader: updater.bin'
    )) {
        if ($m -notmatch ('(?m)^' + [regex]::Escape($line) + '\r?$')) {
            throw "Unexpected updater manifest field: $line"
        }
    }
    Write-Host 'LABMATE FULL STAGING PASS. NO DEVICE CHANGE.' -ForegroundColor Green
    Write-Host "Manifest: $manifest"
    if (-not $Apply) {
        Write-Host 'Staged and verified only; no firmware was installed.'
        exit 0
    }

    foreach ($name in $oldHashes.Keys) {
        Assert-Digest (Join-Path $RollbackDirectory $name) $oldHashes[$name]
    }
    $saved = @(Get-ChildItem -LiteralPath $LabMateBackupDirectory -Recurse -File)
    if ($saved.Count -lt 14) {
        throw 'The 14-file LabMate microSD backup is missing. No flash.'
    }
    if (-not (Test-Path -LiteralPath $SettingsBackupPath -PathType Leaf) -or
        (Get-Item -LiteralPath $SettingsBackupPath).Length -le 0) {
        throw 'The qFlipper internal-settings backup is missing. No flash.'
    }
    Write-Host "Backups checked: microSD $($saved.Count) files and qFlipper archive."
    if ($env:OS -ne 'Windows_NT') {
        throw 'This firmware upgrade requires Windows.'
    }
    $fw = (Resolve-Path -LiteralPath $FirmwareRoot).ProviderPath
    $envCmd = Join-Path $fw 'scripts\toolchain\fbtenv.cmd'
    $selfUpdate = Join-Path $fw 'scripts\selfupdate.py'
    if (-not (Test-Path -LiteralPath $envCmd -PathType Leaf) -or
        -not (Test-Path -LiteralPath $selfUpdate -PathType Leaf)) {
        throw 'Momentum firmware toolchain or selfupdate.py missing.'
    }
    foreach ($path in @($envCmd, $selfUpdate, $manifest)) {
        if ($path -match '["&|<>^%!\r\n]') {
            throw "Unsafe cmd.exe path characters: $path"
        }
    }
    Write-Host ''
    Write-Host 'This will REPLACE the installed Momentum MNTM-012 firmware.'
    Write-Host 'Close qFlipper, disconnect GPIO accessories, keep USB attached.'
    Write-Host 'Do not disconnect USB or interrupt the Flipper while updating.'
    Write-Host 'The LabMate FAP will NOT be installed until firmware startup is checked.'
    $consent = Read-Host 'Type YUKLE to start the real firmware update'
    if ($consent -cne 'YUKLE') {
        throw 'Operator declined update; no firmware operation was started.'
    }
    $line = 'set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && python "{1}" -p {2} "{3}"' -f $envCmd, $selfUpdate, $Port, $manifest
    & cmd.exe /d /s /c $line
    if ($LASTEXITCODE -ne 0) {
        throw "selfupdate.py returned $LASTEXITCODE; firmware update NOT CONFIRMED."
    }
    Write-Host 'FIRMWARE UPDATE COMMAND ACCEPTED; WAIT FOR FLIPPER TO REBOOT.' -ForegroundColor Yellow
    Write-Host 'Do NOT install LabMate FAP until new firmware boots and is confirmed.'
    exit 0
} catch {
    [Console]::Error.WriteLine("LABMATE FULL UPDATE STOPPED: $($_.Exception.Message)")
    exit 1
}
