# Verified LabMate single-file Windows USB installer.
# Does not download firmware, build source, erase CSV records or modify MCU firmware.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$FapPath,
    [string]$ExpectedSha256,
    [string]$ChecksumFile,
    [string]$FirmwareRoot = (Join-Path $HOME 'Momentum-Firmware'),
    [ValidatePattern('^(auto|COM[0-9]{1,3})$')]
    [string]$Port = 'auto',
    [switch]$VerifyOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    $fap = (Resolve-Path -LiteralPath $FapPath).ProviderPath
    if (-not [IO.File]::Exists($fap)) { throw "Not a FAP file: $fap" }
    if ([IO.Path]::GetExtension($fap) -ine '.fap') { throw 'Only .fap files are accepted.' }
    if ((Get-Item -LiteralPath $fap).Length -eq 0) { throw 'Empty FAP.' }

    $name = [IO.Path]::GetFileName($fap)
    if ([string]::IsNullOrWhiteSpace($ExpectedSha256)) {
        if ([string]::IsNullOrWhiteSpace($ChecksumFile)) {
            $ChecksumFile = Join-Path ([IO.Path]::GetDirectoryName($fap)) 'SHA256SUMS.txt'
        }
        $checksumPath = (Resolve-Path -LiteralPath $ChecksumFile).ProviderPath
        $found = @()
        foreach ($line in (Get-Content -LiteralPath $checksumPath)) {
            if ($line -match '^(?<hash>[A-Fa-f0-9]{64})\s+\*?(?<file>.+?)\s*$') {
                $listed = $Matches['file'].Trim()
                if ($listed -ceq $name -or $listed -ceq "./$name") {
                    $found += $Matches['hash']
                }
            }
        }
        if ($found.Count -ne 1) { throw "Exactly one checksum entry for $name is required." }
        $ExpectedSha256 = $found[0]
    }

    if ($ExpectedSha256 -cnotmatch '^[A-Fa-f0-9]{64}$') {
        throw 'ExpectedSha256 must contain 64 hexadecimal digits.'
    }
    $actual = (Get-FileHash -LiteralPath $fap -Algorithm SHA256).Hash
    if (-not [string]::Equals($actual, $ExpectedSha256, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'SHA256 mismatch; nothing has been installed.'
    }

    Write-Host "SHA256 VERIFIED: $actual"
    if ($VerifyOnly) {
        Write-Host 'VerifyOnly complete. No USB or firmware activity.'
        exit 0
    }

    if ($env:OS -ne 'Windows_NT') { throw 'USB installation requires Windows.' }
    $fw = (Resolve-Path -LiteralPath $FirmwareRoot).ProviderPath
    $envCmd = Join-Path $fw 'scripts\toolchain\fbtenv.cmd'
    $runFap = Join-Path $fw 'scripts\runfap.py'
    if (-not [IO.File]::Exists($envCmd) -or -not [IO.File]::Exists($runFap)) {
        throw "Momentum scripts missing from firmware root: $fw"
    }
    # cmd.exe interprets these characters even in some quoted contexts.
    foreach ($path in @($fap, $envCmd, $runFap)) {
        if ($path -match '["&|<>^%!\r\n]') {
            throw "Unsafe path characters for cmd.exe: $path"
        }
    }
    # Do not inherit FBT_ROOT or FBT_NOENV from another firmware checkout.
    # A fixed destination avoids duplicate Flipper application entries.
    $target = '/ext/apps/Tools/labmate.fap'
    $line = 'set "FBT_ROOT=" && set "FBT_NOENV=" && call "{0}" env && python "{1}" -p {2} -s "{3}" -t "{4}"' -f $envCmd, $runFap, $Port, $fap, $target
    Write-Host "Installing to $target via $Port"
    & cmd.exe /d /s /c $line
    $result = $LASTEXITCODE
    if ($result -ne 0) { throw "runfap.py returned exit code $result; installation unconfirmed." }
    Write-Host 'SUCCESS: runfap.py exited 0 and requested app launch.'
    exit 0
}
catch {
    [Console]::Error.WriteLine("LabMate install failure: $($_.Exception.Message)")
    exit 1
}
