# E11 CLI echo diagnostic: READ ONLY after second aborted stage write.
# Requires USB disconnect/reconnect to end any prior write_chunk waiting pipe.
# No write_chunk, upload, rename, remove, app launch, firmware or data modification.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port='COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'

if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'qFlipper is open; close it before read-only diagnostic.'
}
$oldCandidate=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
$oldFap=Join-Path $oldCandidate 'labmate.fap'
$oldBundle=Join-Path $oldCandidate 'firmware-full-update.tgz'
if (-not (Test-Path -LiteralPath $oldFap -PathType Leaf) -or
    -not (Test-Path -LiteralPath $oldBundle -PathType Leaf)) {
    throw 'Previously tested E11 FULL pair missing; no COM activity.'
}
if ((Get-FileHash -LiteralPath $oldFap -Algorithm SHA256).Hash -ne '2B31EC3FA9050580DC3C3FF80138578ED185D70811AA8124EBD2D00B8D981AF0' -or
    (Get-FileHash -LiteralPath $oldBundle -Algorithm SHA256).Hash -ne '11ED3CDF4E99C9C7218973695D349CD946BE97D21DFC59231113BDE15E94C553') {
    throw 'Original E11 source bundle SHA mismatch; no COM activity.'
}
$h0=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Previously tested H0 V3 transport missing.' }

# Immutable exact host-mock-pass source for READ ONLY stat echo capture.
$pin='b150466978a3f8735f78de974b76a4a740010881'
$scripts=Join-Path $env:TEMP ('LabMate-E11-CLI-ECHO-READ-ONLY-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scripts -ErrorAction Stop | Out-Null
$modules=@(
    'audit_v18_e11_live_labmate_sd.py',
    'check_v18_full_update_bundle.py',
    'preflight_v18_e11_local.py',
    'verify_v18_full_review_pair.py',
    'stage_v18_e11_review_only.py',
    'check_v18_e11_postupdate_readonly.py',
    'check_v18_e11_h_js_runtime_ro.py',
    'check_v18_e11_final_fap_prewrite_ro.py',
    'probe_e11_cli_echo_stat_ro.py'
)
foreach($name in $modules) {
    $target=Join-Path $scripts $name
    $uri="https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$pin/scripts/$name"
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $target -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
        (Get-Item -LiteralPath $target).Length -eq 0) {
        throw "Pinned read-only helper unavailable: $name"
    }
}
Write-Host 'E11 CLI COMMAND ECHO / STAT FRAMING - READ ONLY' -ForegroundColor Cyan
Write-Host 'Only device_info, storage stat, storage md5. No FAP or SD writes.'
Write-Host 'Requires fresh USB connection, LabMate stopped, GPIO leads unplugged.'
Write-Host 'On any mismatch: STOP, no repeat or cleanup.' -ForegroundColor Yellow
$arguments=@(
    '-3',(Join-Path $scripts 'probe_e11_cli_echo_stat_ro.py'),
    '--port',$Port,
    '--momentum-scripts',$h0.FullName,
    '--old-candidate',$oldCandidate
)
& py @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'E11 READ-ONLY CLI framing NOT ACCEPTED; no repeat, no SD write.'
}
Write-Host 'E11 READ-ONLY CLI FRAMING VERIFIED - ZERO DEVICE WRITES' -ForegroundColor Green
Write-Host 'STOP HERE. No staged FAP upload or app promotion performed.' -ForegroundColor Yellow
