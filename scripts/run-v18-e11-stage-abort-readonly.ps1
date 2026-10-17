# E11 READ-ONLY inspection following aborted first stage write_chunk.
# User must physically disconnect/reconnect USB first to reset CLI pipe.
# NO storage write_chunk, remove, rename, upload, firmware, GPIO, app run.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port='COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
if (Get-Process qFlipper -ErrorAction SilentlyContinue) {
    throw 'Close qFlipper first; no device operation.'
}
$oldCandidate=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
$oldBundle=Join-Path $oldCandidate 'firmware-full-update.tgz'
$oldApp=Join-Path $oldCandidate 'labmate.fap'
if (-not (Test-Path -LiteralPath $oldBundle -PathType Leaf) -or
    -not (Test-Path -LiteralPath $oldApp -PathType Leaf)) {
    throw 'Known original paired E11 files absent; no COM action.'
}
if ((Get-FileHash -LiteralPath $oldBundle -Algorithm SHA256).Hash -ne
   '11ED3CDF4E99C9C7218973695D349CD946BE97D21DFC59231113BDE15E94C553' -or
   (Get-FileHash -LiteralPath $oldApp -Algorithm SHA256).Hash -ne
   '2B31EC3FA9050580DC3C3FF80138578ED185D70811AA8124EBD2D00B8D981AF0') {
    throw 'Original paired bundle SHA mismatch; no COM action.'
}
$prior=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $prior) {
    throw 'Previously tested H0 V3 Flipper CLI transport missing.'
}

# Exact mocked read-only source CI #39045476312.
$pin='6e1514ba54f7088fcee7678968ca4022760014b4'
$dir=Join-Path $env:TEMP ('LabMate-E11-abort-READ-ONLY-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dir -ErrorAction Stop | Out-Null
$names=@(
  'audit_v18_e11_live_labmate_sd.py',
  'check_v18_full_update_bundle.py',
  'preflight_v18_e11_local.py',
  'verify_v18_full_review_pair.py',
  'stage_v18_e11_review_only.py',
  'check_v18_e11_postupdate_readonly.py',
  'check_v18_e11_h_js_runtime_ro.py',
  'check_v18_e11_final_fap_prewrite_ro.py',
  'check_v18_final_stage_after_abort_ro.py'
)
foreach ($name in $names) {
    $target=Join-Path $dir $name
    $url="https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$pin/scripts/$name"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
        (Get-Item -LiteralPath $target).Length -eq 0) {
        throw "Pinned read-only audit module missing: $name"
    }
}
Write-Host 'E11 FAILED FAP STAGE - DEVICE STATUS INSPECTION ONLY' -ForegroundColor Cyan
Write-Host 'device_info + allowed storage stat and md5 ONLY. No rename/delete/write_chunk.'
Write-Host 'Prior USB disconnected/reconnected; no other serial program running.' -ForegroundColor Yellow
$arguments=@(
    '-3', (Join-Path $dir 'check_v18_final_stage_after_abort_ro.py'),
    '--port',$Port,
    '--momentum-scripts',$prior.FullName,
    '--old-candidate',$oldCandidate
)
& py @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'E11 STATUS NOT OBSERVED. STOP; no retries, deletions or promotion.'
}
Write-Host 'E11 ABORT STAGE READ-ONLY INSPECTION REPORTED - STOP HERE.' -ForegroundColor Green
