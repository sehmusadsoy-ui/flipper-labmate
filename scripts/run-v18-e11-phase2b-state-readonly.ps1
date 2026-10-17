# E11 2B READ-ONLY status after 0/1/2 safe renames, never rollback.
[CmdletBinding()]
param([ValidatePattern('^COM[1-9][0-9]{0,2}$')][string]$Port='COM7')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (Get-Process qFlipper -ErrorAction SilentlyContinue) { throw 'Close qFlipper first.' }
$backup=Join-Path $env:USERPROFILE 'Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d'
$new=Join-Path $env:USERPROFILE 'Downloads\labmate_v18_FINAL_REVIEW_ONLY.fap'
$old=Join-Path $env:TEMP 'LabMate-E11-Trial-1bd5f6f6abf247609dc605ac69ff8ffc\E11-FULL'
if (-not (Test-Path -LiteralPath $new -PathType Leaf) -or
    -not (Test-Path -LiteralPath $old -PathType Container) -or
    -not (Test-Path -LiteralPath $backup -PathType Container)) {
    throw 'Previously verified E11 local inputs unavailable; NO COM ACTION.'
}
if ((Get-FileHash -LiteralPath $new -Algorithm SHA256).Hash -ne
      '393FE3E52AA710162A42D7299AA053F538B2EE1AD6542755CF402B83C1931B61') {
    throw 'New candidate PC hash changed. NO COM ACTION.'
}
$h0=Get-ChildItem -LiteralPath $env:TEMP -Directory -Filter 'LabMate-E11-H0-*' |
    Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName 'flipper\storage.py') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'scripts\check_v18_e11_h0_stage_v3.py') -PathType Leaf)
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $h0) { throw 'Trusted H0 CLI source missing.' }
$pin='086275b82205ad16750fca893e6aa66300f985b4'
$dir=Join-Path $env:TEMP ('LabMate-E11-2B-READONLY-' + [guid]::NewGuid().ToString('N'))
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
  'stage_v18_final_fap_on_device_one_file.py',
  'check_v18_e11_phase2b_state_readonly.py'
)
foreach($name in $names) {
    $destination=Join-Path $dir $name
    $url="https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$pin/scripts/$name"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $destination
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf) -or
        (Get-Item -LiteralPath $destination).Length -eq 0) {
        throw "Missing pinned E11 read-only helper $name"
    }
}
Write-Host 'E11 2B THREE FAP PATHS STATE - READ ONLY' -ForegroundColor Cyan
Write-Host 'Only device_info / storage stat / storage md5. No write, rename, delete, firmware.'
$pyArgs=@(
  '-3',(Join-Path $dir 'check_v18_e11_phase2b_state_readonly.py'),
  '--port',$Port,
  '--momentum-scripts',$h0.FullName,
  '--old-candidate',$old,
  '--saved-old-fap-backup',$backup,
  '--new-fap',$new
)
& py @pyArgs
if ($LASTEXITCODE -ne 0) { throw 'E11 READ-ONLY 2B STATUS NO-GO. NO RETRY/RESTORE.' }
Write-Host 'E11 2B READ ONLY STATE CAPTURED. STOP, AWAIT REVIEW.' -ForegroundColor Cyan
