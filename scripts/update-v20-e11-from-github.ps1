# Exact-source WSL Ubuntu build -> optional one-FAP Windows USB update.
# No manual ZIP; -Install alone permits USB AFTER saved readback and typed consent.
[CmdletBinding()]
param(
    [ValidateSet('Ubuntu')][string]$Distro='Ubuntu',
    [ValidatePattern('^(auto|COM[1-9][0-9]{0,2})$')][string]$Port='auto',
    [string]$FirmwareRoot=(Join-Path $HOME 'Momentum-Firmware'),
    [switch]$Install,
    [switch]$Discover,
    [switch]$ReuseVerifiedLocalFap
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Expected='6DBE192BA7D1B0F2B05702C90CF68D791F041F75ED53A6B41135176B6AD4DE5B'
# Windows PowerShell 5.1 rewrites piped native stdin with CRLF.
# Use Process.StandardInput to send LF-only Bash source without CR bytes.
function Invoke-LfStdinProcess {
    param(
        [Parameter(Mandatory=$true)][string]$ExePath,
        [Parameter(Mandatory=$true)][string]$Arguments,
        [Parameter(Mandatory=$true)][string]$Source,
        [switch]$CaptureOutput
    )
    # .NET Framework Process.StandardInput can add UTF-8 BOM even if its
    # BaseStream is written directly. Never open its StreamWriter.
    # Feed a BOM-free LF-only temporary script via OS-level stdin redirect.
    $InputPath = [System.IO.Path]::GetTempFileName()
    $OutputPath = $null
    try {
        $NoBomUtf8 = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText(
            $InputPath, ($Source.Replace([string][char]13, '') + [char]10), $NoBomUtf8)
        $Options = @{
            FilePath = $ExePath
            ArgumentList = $Arguments
            RedirectStandardInput = $InputPath
            NoNewWindow = $true
            Wait = $true
            PassThru = $true
        }
        if ($CaptureOutput) {
            $OutputPath = [System.IO.Path]::GetTempFileName()
            $Options['RedirectStandardOutput'] = $OutputPath
        }
        $Proc = Start-Process @Options
        if ($Proc.ExitCode -ne 0) {
            throw "$ExePath Bash failed (exit $($Proc.ExitCode)); NO USB WRITE"
        }
        if ($CaptureOutput) {
            return ([System.IO.File]::ReadAllText($OutputPath)).Trim()
        }
    } finally {
        if ($OutputPath -and [System.IO.File]::Exists($OutputPath)) {
            [System.IO.File]::Delete($OutputPath)
        }
        if ([System.IO.File]::Exists($InputPath)) {
            [System.IO.File]::Delete($InputPath)
        }
    }
}

function Invoke-WslBash {
    param([Parameter(Mandatory=$true)][string]$Source,[switch]$CaptureOutput)
    Invoke-LfStdinProcess -ExePath 'wsl.exe' -Arguments "--distribution $Distro --exec bash -s" -Source $Source -CaptureOutput:$CaptureOutput
}

try {
    if ($env:OS -ne 'Windows_NT') { throw 'Windows required' }
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'WSL Ubuntu missing' }
    if ($Install -and $Discover) { throw 'Choose -Discover or -Install, not both' }
    if (($Install -or $Discover) -and (Get-Process qFlipper -ErrorAction SilentlyContinue)) {
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
LABMATE_REUSE_EXACT_FAP=__LABMATE_REUSE__ bash "$DIR/scripts/build-v20-e11-exact-local.sh"
'@
    $ReuseMode = if ($ReuseVerifiedLocalFap) { '1' } else { '0' }
    $Linux = $Linux.Replace('__LABMATE_REUSE__', $ReuseMode)
    if ($ReuseVerifiedLocalFap) {
        Write-Host 'Reusing ONLY the previously validated 39261383... FAP (strict SHA + CI parity).' -ForegroundColor Cyan
    }
    Write-Host 'GITHUB -> WSL UBUNTU -> PINNED E11 (PC ONLY FIRST)' -ForegroundColor Cyan
    Invoke-WslBash -Source $Linux
    $FapPathLinux = 'wslpath -w "$HOME/.local/share/labmate-e11/labmate.fap"'
    $Fap = Invoke-WslBash -Source $FapPathLinux -CaptureOutput
    if (-not (Test-Path -LiteralPath $Fap -PathType Leaf)) { throw 'WSL FAP not accessible in Windows' }
    # The WSL builder already proved byte-for-byte CI parity excluding only
    # GNU debuglink CRC. Verify the UNC file is exactly the same full FAP
    # that WSL produced. This is NOT a relaxed hash comparison.
    $DigestLinux = 'sha256sum "$HOME/.local/share/labmate-e11/labmate.fap"'
    $DigestLine = Invoke-WslBash -Source $DigestLinux -CaptureOutput
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
    if (-not $Install -and -not $Discover) {
        Write-Host 'PC-ONLY PASS. Device untouched. Add -Discover (read-only) or -Install.'
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
        $SdkScripts = Invoke-WslBash -Source $SdkPathLinux -CaptureOutput
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
    $Helper = Invoke-WslBash -Source $HelperPathLinux -CaptureOutput
    $Backup=Join-Path $HOME 'Documents\LabMate-FAP-PC-Backups'
    $ArgumentsToCheck = @($Fap,$Helper,$Backup)
    if ($UseWindowsFirmware) { $ArgumentsToCheck += @($EnvCmd,(Join-Path $Fw 'scripts')) }
    else { $ArgumentsToCheck += $SdkScripts }
    foreach($Value in $ArgumentsToCheck) {
        if ($Value -match '["&|<>^%!]') { throw 'Unsafe Windows command path' }
    }
    # The candidate on \\wsl.localhost passed byte checks, but Windows
    # pyserial/FlipperStorage.send_file() calls os.fstat() on its input file.
    # On WSL UNC redirected files that can fail with Windows Errno 22
    # AFTER operator consent. Use one short-lived LOCAL NTFS copy instead.
    # Keep all SDK/FAP origin and digest checks above unchanged.
    $UsbFlag = if ($Discover) { '--discover' } else { '--apply' }
    $UsbFap = $Fap
    $UsbTempFolder = $null
    try {
        if ($Install) {
            $UsbTempFolder = Join-Path $env:TEMP ('labmate-e11-usb-' + [guid]::NewGuid().ToString('N'))
            [void](New-Item -ItemType Directory -Path $UsbTempFolder -ErrorAction Stop)
            $UsbFap = Join-Path $UsbTempFolder 'labmate.fap'
            if ($UsbFap.StartsWith('\\')) { throw 'NO-GO: staging FAP requires a LOCAL Windows filesystem, not a UNC path' }
            [System.IO.File]::Copy($Fap, $UsbFap, $false)
            $StageSHA = (Get-FileHash -LiteralPath $UsbFap -Algorithm SHA256).Hash
            if ($StageSHA -ine $ActualWindows -or $StageSHA -ine $ExpectedRaw -or
                (Get-Item -LiteralPath $UsbFap).Length -ne 174192) {
                throw 'NO-GO: local NTFS USB staging FAP hash or size differs from verified WSL candidate'
            }
            Write-Host 'LOCAL WINDOWS USB STAGE SHA256 PASS; no WSL UNC input to FlipperStorage.' -ForegroundColor Green
        }
        if ($UsbFap -match '["&|<>^%!]') { throw 'Unsafe Windows USB FAP stage path' }
        if ($UseWindowsFirmware) {
            $Line='set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && set "PYTHONPATH={1}" && python "{2}" --fap "{3}" --backup-root "{4}" --port {5} {6}' -f $EnvCmd,(Join-Path $Fw 'scripts'),$Helper,$UsbFap,$Backup,$Port,$UsbFlag
        } else {
            $Line='set "PYTHONPATH={0}" && py -3 -B "{1}" --fap "{2}" --backup-root "{3}" --port {4} {5}' -f $SdkScripts,$Helper,$UsbFap,$Backup,$Port,$UsbFlag
        }
        if ($Discover) {
            Write-Host 'USB READ-ONLY: enumerate old FAP paths/sizes. NO device writes or backup changes.' -ForegroundColor Cyan
        } else {
            Write-Host 'USB: read existing device FAP, save verified PC backup, require E11 consent.'
        }
        & cmd.exe /d /s /c $Line
        if ($LASTEXITCODE -ne 0) { throw 'USB stage stopped; no automatic retry' }
        if ($Discover) {
            Write-Host 'READ-ONLY Flipper FAP discovery complete. No installation attempted.' -ForegroundColor Green
        } else {
            Write-Host 'Single labmate.fap USB readback PASS. Physical UI test is still needed.' -ForegroundColor Green
        }
    } finally {
        # Never accumulate Windows copies of labmate.fap; the ONLY retained
        # PC backup is the old verified device FAP saved by the installer.
        if ($UsbTempFolder -and (Test-Path -LiteralPath $UsbTempFolder)) {
            Remove-Item -LiteralPath $UsbTempFolder -Recurse -Force -ErrorAction Stop
        }
    }
    exit 0
} catch {
    [Console]::Error.WriteLine("LabMate E11 NO-GO: $($_.Exception.Message)")
    exit 1
}