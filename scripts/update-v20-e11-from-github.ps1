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
    & wsl.exe --distribution $Distro --exec bash -lc $Linux
    if ($LASTEXITCODE -ne 0) { throw 'WSL source/SDK/FAP verification failed; NO USB WRITE' }
    $FapResult=& wsl.exe --distribution $Distro --exec bash -lc 'wslpath -w "$HOME/.local/share/labmate-e11/labmate.fap"'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve WSL FAP' }
    $Fap=([string]($FapResult | Select-Object -Last 1)).Trim()
    if (-not (Test-Path -LiteralPath $Fap -PathType Leaf)) { throw 'WSL FAP not accessible in Windows' }
    if ((Get-FileHash -LiteralPath $Fap -Algorithm SHA256).Hash -ine $Expected -or (Get-Item -LiteralPath $Fap).Length -ne 174192) {
        throw 'Exact FAP SHA/size mismatch on Windows'
    }
    Write-Host "PC FAP verified: $Fap" -ForegroundColor Green
    if (-not $Install) {
        Write-Host 'PC-ONLY PASS. Device untouched. Add -Install for USB.'
        exit 0
    }
    $Fw=(Resolve-Path -LiteralPath $FirmwareRoot).ProviderPath
    $EnvCmd=Join-Path $Fw 'scripts\toolchain\fbtenv.cmd'
    $Module=Join-Path $Fw 'scripts\flipper\storage.py'
    if (-not (Test-Path -LiteralPath $EnvCmd -PathType Leaf) -or -not (Test-Path -LiteralPath $Module -PathType Leaf)) {
        throw "Windows Momentum USB scripts missing: $Fw"
    }
    $HelperResult=& wsl.exe --distribution $Distro --exec bash -lc 'wslpath -w "$HOME/.local/share/labmate-e11-source/scripts/install-v20-e11-usb.py"'
    if ($LASTEXITCODE -ne 0) { throw 'USB helper path resolution failed' }
    $Helper=([string]($HelperResult | Select-Object -Last 1)).Trim()
    $Backup=Join-Path $HOME 'Documents\LabMate-FAP-PC-Backups'
    foreach($Value in @($Fap,$Helper,$EnvCmd,$Backup)) {
        if ($Value -match '["&|<>^%!]') { throw 'Unsafe Windows command path' }
    }
    $Line='set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && set "PYTHONPATH={1}" && python "{2}" --fap "{3}" --backup-root "{4}" --port {5} --apply' -f $EnvCmd,(Join-Path $Fw 'scripts'),$Helper,$Fap,$Backup,$Port
    Write-Host 'USB: read existing device FAP, save verified PC backup, require E11 consent.'
    & cmd.exe /d /s /c $Line
    if ($LASTEXITCODE -ne 0) { throw 'USB stage stopped; DO NOT RETRY blindly' }
    Write-Host 'Single labmate.fap USB readback PASS. Physical UI test is still needed.' -ForegroundColor Green
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate E11 NO-GO: $($_.Exception.Message)")
    exit 1
}