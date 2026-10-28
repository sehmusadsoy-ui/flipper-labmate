# Exact-source WSL Ubuntu build -> optional one-FAP Windows USB update.
# No manual ZIP; -Install alone permits USB AFTER saved readback and typed consent.
[CmdletBinding()]
param(
    [ValidateSet('Ubuntu')][string]$Distro='Ubuntu',
    [ValidatePattern('^(auto|COM[1-9][0-9]{0,2})$')][string]$Port='auto',
    [string]$FirmwareRoot=(Join-Path $HOME 'Momentum-Firmware'),
    [switch]$Install
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Expected='6DBE192BA7D1B0F2B05702C90CF68D791F041F75ED53A6B41135176B6AD4DE5B'
try {
    if ($env:OS -ne 'Windows_NT') { throw 'Windows required' }
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'WSL Ubuntu missing' }
    if ($Install -and (Get-Process qFlipper -ErrorAction SilentlyContinue)) {
        throw 'Close qFlipper before serial USB update'
    }
    $Linux = @'
set -Eeuo pipefail
DIR="$HOME/.local/share/labmate-e11-source"
URL="https://github.com/sehmusadsoy-ui/flipper-labmate.git"
BRANCH="dev/v2.0-e11-legacy-ui-harness-review-20261029"
PIN="98a3357dade93aacac83c04e01110804b3b3f7b0"
mkdir -p "$(dirname "$DIR")"
if [ ! -d "$DIR/.git" ]; then
  test ! -e "$DIR" || { echo "NO-GO: source folder exists but is not Git"; exit 2; }
  git clone --single-branch --branch "$BRANCH" "$URL" "$DIR"
fi
test "$(git -C "$DIR" remote get-url origin)" = "$URL"
test -z "$(git -C "$DIR" status --porcelain)"
git -C "$DIR" fetch --no-tags origin "$BRANCH"
git -C "$DIR" -c advice.detachedHead=false checkout -B labmate-e11-review FETCH_HEAD
git -C "$DIR" merge-base --is-ancestor "$PIN" HEAD
bash "$DIR/scripts/build-v20-e11-exact-local.sh"
'@
    Write-Host 'GITHUB -> WSL UBUNTU -> PINNED E11 (PC ONLY FIRST)' -ForegroundColor Cyan
    # Windows PowerShell 5.1 cannot reliably pass embedded Bash quotes in -lc
    # arguments through wsl.exe; Bash must parse a script from STDIN instead.
    $NormalizedLinux = ($Linux -replace "`r", "") + "`n"
    $NormalizedLinux | & wsl.exe --distribution $Distro --exec bash -s
    if ($LASTEXITCODE -ne 0) { throw 'WSL source/SDK/FAP verification failed; NO USB WRITE' }
    $FapPathLinux = 'wslpath -w "$HOME/.local/share/labmate-e11/labmate.fap"'
    $FapResult = $FapPathLinux | & wsl.exe --distribution $Distro --exec bash -s
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve WSL FAP' }
    $Fap=([string]($FapResult | Select-Object -Last 1)).Trim()
    if (-not (Test-Path -LiteralPath $Fap -PathType Leaf)) { throw 'WSL FAP not accessible in Windows' }
    # The WSL builder already proved byte-for-byte CI parity excluding only
    # GNU debuglink CRC. Verify the UNC file is exactly the same full FAP
    # that WSL produced. This is NOT a relaxed hash comparison.
    $DigestLinux = 'sha256sum "$HOME/.local/share/labmate-e11/labmate.fap"'
    $DigestResult = $DigestLinux | & wsl.exe --distribution $Distro --exec bash -s
    if ($LASTEXITCODE -ne 0) { throw 'WSL full candidate digest unavailable' }
    $DigestLine = ([string]($DigestResult | Select-Object -Last 1)).Trim()
    if ($DigestLine -notmatch '^([0-9a-fA-F]{64})\s+') { throw 'Invalid WSL raw SHA256 result' }
    $ExpectedRaw = $Matches[1]
    $ActualWindows = (Get-FileHash -LiteralPath $Fap -Algorithm SHA256).Hash
    if ($ActualWindows -ine $ExpectedRaw -or (Get-Item -LiteralPath $Fap).Length -ne 174192) {
        throw 'WSL / Windows full FAP SHA256 or size mismatch'
    }
    Write-Host "PC FAP verified: $Fap" -ForegroundColor Green
    Write-Host "Full local SHA256: $ActualWindows"
    if ($ActualWindows -ine $Expected) {
        Write-Host 'CI raw SHA differs ONLY in verified 4-byte GNU debuglink CRC.' -ForegroundColor Yellow
    }
    if (-not $Install) {
        Write-Host 'PC-ONLY PASS. Device untouched. Add -Install for USB.'
        exit 0
    }
    # Prefer an installed Windows Momentum fbtenv, but the owner already has
    # the pinned E11 source under WSL. With Windows pyserial installed, its
    # read-only scripts are valid as a Python import path over the WSL UNC share.
    $Fw = $null
    if (Test-Path -LiteralPath $FirmwareRoot -PathType Container) {
        $Fw = (Resolve-Path -LiteralPath $FirmwareRoot).ProviderPath
    }
    $EnvCmd = if ($Fw) { Join-Path $Fw 'scripts\toolchain\fbtenv.cmd' } else { $null }
    $Module = if ($Fw) { Join-Path $Fw 'scripts\flipper\storage.py' } else { $null }
    $UseWindowsFirmware = ($Fw -and (Test-Path -LiteralPath $EnvCmd -PathType Leaf) -and
        (Test-Path -LiteralPath $Module -PathType Leaf))
    if (-not $UseWindowsFirmware) {
        Write-Host 'Windows Momentum toolchain unavailable. Checking existing WSL E11 USB Python transport.' -ForegroundColor Yellow
        $SdkPathLinux = 'wslpath -w "$HOME/labmate-build/momentum-src/scripts"'
        $SdkPathResult = $SdkPathLinux | & wsl.exe --distribution $Distro --exec bash -s
        if ($LASTEXITCODE -ne 0) { throw 'Cannot locate the pinned E11 WSL SDK transport' }
        $SdkScripts = ([string]($SdkPathResult | Select-Object -Last 1)).Trim()
        if (-not (Test-Path -LiteralPath (Join-Path $SdkScripts 'flipper\storage.py') -PathType Leaf)) {
            throw 'No Windows or WSL Momentum USB transport available; nothing written to Flipper'
        }
        if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
            throw 'Windows Python launcher py.exe required for existing WSL SDK transport'
        }
        & py.exe -3 -c 'import serial'
        if ($LASTEXITCODE -ne 0) {
            throw 'Windows Python pyserial is missing. No automatic package install or device write.'
        }
    }
    $HelperPathLinux = 'wslpath -w "$HOME/.local/share/labmate-e11-source/scripts/install-v20-e11-usb.py"'
    $HelperResult = $HelperPathLinux | & wsl.exe --distribution $Distro --exec bash -s
    if ($LASTEXITCODE -ne 0) { throw 'USB helper path resolution failed' }
    $Helper=([string]($HelperResult | Select-Object -Last 1)).Trim()
    $Backup=Join-Path $HOME 'Documents\LabMate-FAP-PC-Backups'
    $ArgumentsToCheck = @($Fap,$Helper,$Backup)
    if ($UseWindowsFirmware) { $ArgumentsToCheck += @($EnvCmd,(Join-Path $Fw 'scripts')) }
    else { $ArgumentsToCheck += $SdkScripts }
    foreach($Value in $ArgumentsToCheck) {
        if ($Value -match '["&|<>^%!]') { throw 'Unsafe Windows command path' }
    }
    if ($UseWindowsFirmware) {
        $Line='set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && set "PYTHONPATH={1}" && python "{2}" --fap "{3}" --backup-root "{4}" --port {5} --apply' -f $EnvCmd,(Join-Path $Fw 'scripts'),$Helper,$Fap,$Backup,$Port
    } else {
        $Line='set "PYTHONPATH={0}" && py -3 -B "{1}" --fap "{2}" --backup-root "{3}" --port {4} --apply' -f $SdkScripts,$Helper,$Fap,$Backup,$Port
    }
    Write-Host 'USB: read existing device FAP, save verified PC backup, require E11 consent.'
    & cmd.exe /d /s /c $Line
    if ($LASTEXITCODE -ne 0) { throw 'USB stage stopped; DO NOT RETRY blindly' }
    Write-Host 'Single labmate.fap USB readback PASS. Physical UI test is still needed.' -ForegroundColor Green
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate E11 NO-GO: $($_.Exception.Message)")
    exit 1
}