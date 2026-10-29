# Operator-initiated COMM v2.0 E11 candidate installation.
# The requested GitHub Actions artifact must be the FULL raw CI binary
# (not the old verified 174192-byte candidate or a reconstructed FAP).
# No firmware flashing, GPIO/CSV/profile writes, or automatic retries.
[CmdletBinding()]
param(
    [ValidatePattern('^(auto|COM[1-9][0-9]{0,2})
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Repo = 'sehmusadsoy-ui/flipper-labmate'
$RunId = 40838850973
$Artifact = 'labmate-e11-candidate-40838850973'
$HelperRef = '087aef0afa97ed7bf4ee227abb52a685058e3bc7'
$ExpectedSha = '160e1c2c7e5f63418bf641fc7b5ab9a72f5bb45219126d914b94185654d10e7e'
$ExpectedBytes = 177804
$SavedPyPath = $env:PYTHONPATH
$TempRoot = $null
try {
    if ($env:OS -ne 'Windows_NT') { throw 'NO-GO: Windows PowerShell required' }
    foreach ($exe in @('gh.exe','py.exe','wsl.exe')) {
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
            throw "NO-GO: $exe missing. gh CLI (logged in), Windows Python and WSL Ubuntu are required."
        }
    }
    if ($Install -and (Get-Process qFlipper -ErrorAction SilentlyContinue)) {
        throw 'NO-GO: close qFlipper before USB install'
    }
    # No UNC staged input. FlipperStorage uses os.fstat on the FAP handle.
    $TempRoot = Join-Path $env:TEMP ('labmate-e11-comm-'+[guid]::NewGuid().ToString('N'))
    if ($TempRoot.StartsWith('\\')) {
        throw 'NO-GO: TEMP must be on a local Windows filesystem'
    }
    $ArtifactDir = Join-Path $TempRoot 'ci'
    $HelperDir = Join-Path $TempRoot 'operator'
    [void](New-Item -ItemType Directory -Path $ArtifactDir -Force -ErrorAction Stop)
    [void](New-Item -ItemType Directory -Path $HelperDir -Force -ErrorAction Stop)

    Write-Host "Downloading GitHub Actions run $RunId (only exact named COMM artifact)..." -ForegroundColor Cyan
    & gh.exe run download $RunId --repo $Repo --name $Artifact --dir $ArtifactDir
    if ($LASTEXITCODE -ne 0) { throw 'NO-GO: authenticated GitHub Actions artifact download failed' }
    $Fap = Join-Path $ArtifactDir 'labmate.fap'
    if (-not (Test-Path -LiteralPath $Fap -PathType Leaf)) {
        throw 'NO-GO: expected labmate.fap not present in reviewed artifact'
    }
    if ((Get-Item -LiteralPath $Fap).Length -ne $ExpectedBytes) {
        throw 'NO-GO: downloaded CI FAP byte count mismatch'
    }
    $Sha = (Get-FileHash -LiteralPath $Fap -Algorithm SHA256).Hash
    if ($Sha -ine $ExpectedSha) {
        throw 'NO-GO: downloaded CI FAP SHA256 differs from exact reviewed commit'
    }
    Write-Host 'EXACT CI COMM FAP SHA256 PASS: 177804 bytes' -ForegroundColor Green
    Write-Host "SHA256: $Sha"

    # Fetch from a fixed immutable installer ref, not a floating branch.
    $Helper = Join-Path $HelperDir 'install-v20-e11-usb.py'
    $Parity = Join-Path $HelperDir 'verify_v20_e11_debuglink_parity.py'
    $BaseUrl = "https://raw.githubusercontent.com/$Repo/$HelperRef/scripts"
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/install-v20-e11-usb.py" -OutFile $Helper
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/verify_v20_e11_debuglink_parity.py" -OutFile $Parity
    if (-not ([System.IO.File]::ReadAllText($Helper).Contains('--reviewed-comm-v20'))) {
        throw 'NO-GO: fixed reviewed COMM installer mode unavailable'
    }
    $SdkLine = & wsl.exe --distribution $Distro --exec bash -lc 'wslpath -w "$HOME/labmate-build/momentum-src/scripts"'
    if ($LASTEXITCODE -ne 0 -or -not $SdkLine) {
        throw 'NO-GO: WSL Momentum scripts location unavailable'
    }
    $SdkScripts = ([string]($SdkLine | Select-Object -First 1)).Trim()
    if (-not (Test-Path -LiteralPath (Join-Path $SdkScripts 'flipper\storage.py') -PathType Leaf)) {
        throw 'NO-GO: expected Momentum SDK storage transport missing'
    }
    & py.exe -3 -c 'import serial'
    if ($LASTEXITCODE -ne 0) {
        throw 'NO-GO: pyserial unavailable in Windows Python'
    }

    Write-Host 'PINNED COMM v2.0 FAP ready for exact one-file USB review.'
    if (-not $Install) {
        Write-Host 'PC-ONLY PASS, no device write. Add -Install for verified backup and explicit operator consent.'
        exit 0
    }
    $Backup = Join-Path $HOME 'Documents\LabMate-FAP-PC-Backups'
    Write-Host 'USB: close LabMate on Flipper and keep qFlipper closed.'
    Write-Host 'Previous canonical FAP will be read back and backed up to the PC before any write.'
    # Unlike cmd.exe /c string interpolation, a native argument list
    # preserves paths, console stdin and interactive YUKLE-E11-LABMATE.
    $env:PYTHONPATH = $SdkScripts
    & py.exe -3 -B $Helper --fap $Fap --backup-root $Backup --port $Port --apply --reviewed-comm-v20
    if ($LASTEXITCODE -ne 0) {
        throw 'NO-GO: USB stage rejected or failed; NO automatic retry'
    }
    Write-Host 'COMM v2.0 reviewed FAP USB write/readback PASS; physical pixel QA remains pending.' -ForegroundColor Green
} catch {
    [Console]::Error.WriteLine("LabMate E11 NO-GO: $($_.Exception.Message)")
    exit 1
} finally {
    $env:PYTHONPATH = $SavedPyPath
    if ($TempRoot -and (Test-Path -LiteralPath $TempRoot)) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
)]
    [string]$Port='auto',
    [ValidateSet('Ubuntu')][string]$Distro='Ubuntu',
    [switch]$Install
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Repo = 'sehmusadsoy-ui/flipper-labmate'
$Artifact = 'labmate-e11-comm-reviewed-20261029'
$HelperRef = '087aef0afa97ed7bf4ee227abb52a685058e3bc7'
$ExpectedSha = '160e1c2c7e5f63418bf641fc7b5ab9a72f5bb45219126d914b94185654d10e7e'
$ExpectedBytes = 177804
$SavedPyPath = $env:PYTHONPATH
$TempRoot = $null
try {
    if ($env:OS -ne 'Windows_NT') { throw 'NO-GO: Windows PowerShell required' }
    foreach ($exe in @('gh.exe','py.exe','wsl.exe')) {
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
            throw "NO-GO: $exe missing. gh CLI (logged in), Windows Python and WSL Ubuntu are required."
        }
    }
    if ($Install -and (Get-Process qFlipper -ErrorAction SilentlyContinue)) {
        throw 'NO-GO: close qFlipper before USB install'
    }
    # No UNC staged input. FlipperStorage uses os.fstat on the FAP handle.
    $TempRoot = Join-Path $env:TEMP ('labmate-e11-comm-'+[guid]::NewGuid().ToString('N'))
    if ($TempRoot.StartsWith('\\')) {
        throw 'NO-GO: TEMP must be on a local Windows filesystem'
    }
    $ArtifactDir = Join-Path $TempRoot 'ci'
    $HelperDir = Join-Path $TempRoot 'operator'
    [void](New-Item -ItemType Directory -Path $ArtifactDir -Force -ErrorAction Stop)
    [void](New-Item -ItemType Directory -Path $HelperDir -Force -ErrorAction Stop)

    Write-Host "Downloading GitHub Actions run $RunId (only exact named COMM artifact)..." -ForegroundColor Cyan
    & gh.exe run download $RunId --repo $Repo --name $Artifact --dir $ArtifactDir
    if ($LASTEXITCODE -ne 0) { throw 'NO-GO: authenticated GitHub Actions artifact download failed' }
    $Fap = Join-Path $ArtifactDir 'labmate.fap'
    if (-not (Test-Path -LiteralPath $Fap -PathType Leaf)) {
        throw 'NO-GO: expected labmate.fap not present in reviewed artifact'
    }
    if ((Get-Item -LiteralPath $Fap).Length -ne $ExpectedBytes) {
        throw 'NO-GO: downloaded CI FAP byte count mismatch'
    }
    $Sha = (Get-FileHash -LiteralPath $Fap -Algorithm SHA256).Hash
    if ($Sha -ine $ExpectedSha) {
        throw 'NO-GO: downloaded CI FAP SHA256 differs from exact reviewed commit'
    }
    Write-Host 'EXACT CI COMM FAP SHA256 PASS: 177804 bytes' -ForegroundColor Green
    Write-Host "SHA256: $Sha"

    # Fetch from a fixed immutable installer ref, not a floating branch.
    $Helper = Join-Path $HelperDir 'install-v20-e11-usb.py'
    $Parity = Join-Path $HelperDir 'verify_v20_e11_debuglink_parity.py'
    $BaseUrl = "https://raw.githubusercontent.com/$Repo/$HelperRef/scripts"
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/install-v20-e11-usb.py" -OutFile $Helper
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/verify_v20_e11_debuglink_parity.py" -OutFile $Parity
    if (-not ([System.IO.File]::ReadAllText($Helper).Contains('--reviewed-comm-v20'))) {
        throw 'NO-GO: fixed reviewed COMM installer mode unavailable'
    }
    $SdkLine = & wsl.exe --distribution $Distro --exec bash -lc 'wslpath -w "$HOME/labmate-build/momentum-src/scripts"'
    if ($LASTEXITCODE -ne 0 -or -not $SdkLine) {
        throw 'NO-GO: WSL Momentum scripts location unavailable'
    }
    $SdkScripts = ([string]($SdkLine | Select-Object -First 1)).Trim()
    if (-not (Test-Path -LiteralPath (Join-Path $SdkScripts 'flipper\storage.py') -PathType Leaf)) {
        throw 'NO-GO: expected Momentum SDK storage transport missing'
    }
    & py.exe -3 -c 'import serial'
    if ($LASTEXITCODE -ne 0) {
        throw 'NO-GO: pyserial unavailable in Windows Python'
    }

    Write-Host 'PINNED COMM v2.0 FAP ready for exact one-file USB review.'
    if (-not $Install) {
        Write-Host 'PC-ONLY PASS, no device write. Add -Install for verified backup and explicit operator consent.'
        exit 0
    }
    $Backup = Join-Path $HOME 'Documents\LabMate-FAP-PC-Backups'
    Write-Host 'USB: close LabMate on Flipper and keep qFlipper closed.'
    Write-Host 'Previous canonical FAP will be read back and backed up to the PC before any write.'
    # Unlike cmd.exe /c string interpolation, a native argument list
    # preserves paths, console stdin and interactive YUKLE-E11-LABMATE.
    $env:PYTHONPATH = $SdkScripts
    & py.exe -3 -B $Helper --fap $Fap --backup-root $Backup --port $Port --apply --reviewed-comm-v20
    if ($LASTEXITCODE -ne 0) {
        throw 'NO-GO: USB stage rejected or failed; NO automatic retry'
    }
    Write-Host 'COMM v2.0 reviewed FAP USB write/readback PASS; physical pixel QA remains pending.' -ForegroundColor Green
} catch {
    [Console]::Error.WriteLine("LabMate E11 NO-GO: $($_.Exception.Message)")
    exit 1
} finally {
    $env:PYTHONPATH = $SavedPyPath
    if ($TempRoot -and (Test-Path -LiteralPath $TempRoot)) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
