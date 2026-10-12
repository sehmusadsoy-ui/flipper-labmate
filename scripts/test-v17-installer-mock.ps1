# Windows CI only: fake GitHub CLI and fake Momentum USB transport.
# Tests installer behavior without internet downloads or physical Flipper.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = $env:LABMATE_FIXTURE_ROOT
$fw = $env:LABMATE_MOCK_FW
if(-not $root -or -not $fw) { throw 'CI fixture environment is missing.' }
$bin = Join-Path $root 'mock-gh-bin'
New-Item -ItemType Directory -Path $bin -Force | Out-Null
$python = Join-Path $bin 'gh-stub.py'
$cmd = Join-Path $bin 'gh.cmd'

$mock = @'
import json, os, pathlib, shutil, sys
args = sys.argv[1:]
root = pathlib.Path(os.environ["LABMATE_FIXTURE_ROOT"])
sha = "a" * 40
if args[:2] == ["auth", "status"]:
    sys.exit(0)
if args and args[0] == "api" and len(args) > 1:
    endpoint = args[1]
    if endpoint == "repos/sehmusadsoy-ui/flipper-labmate/git/ref/tags/v1.7":
        print(json.dumps({"object": {"type": "commit", "sha": sha}}))
        sys.exit(0)
    if endpoint == "repos/sehmusadsoy-ui/flipper-labmate/releases/tags/v1.7":
        print(json.dumps({"tag_name": "v1.7", "draft": False, "prerelease": False,
              "target_commitish": sha, "assets": [{"name": "labmate.fap"},
              {"name": "SHA256SUMS.txt"}]}))
        sys.exit(0)
    if endpoint == "repos/sehmusadsoy-ui/flipper-labmate/git/ref/tags/v1.7-rc1":
        print(json.dumps({"object": {"type": "commit",
              "sha": "d55eec032e5f341f39aa7c98915ec2062995e66b"}}))
        sys.exit(0)
    if endpoint == "repos/sehmusadsoy-ui/flipper-labmate/releases/tags/v1.7-rc1":
        print(json.dumps({"tag_name": "v1.7-rc1", "draft": False, "prerelease": True,
              "target_commitish": "d55eec032e5f341f39aa7c98915ec2062995e66b",
              "assets": [{"name": "labmate.fap"}, {"name": "SHA256SUMS.txt"}]}))
        sys.exit(0)
if args[:2] == ["release", "download"] and "-D" in args:
    target = pathlib.Path(args[args.index("-D") + 1])
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "labmate.fap", target / "labmate.fap")
    text = (root / "SHA256SUMS.txt").read_text(encoding="utf-8")
    if os.getenv("LABMATE_MOCK_TAMPER") == "1":
        text = "0" * 64 + "  labmate.fap\n"
    (target / "SHA256SUMS.txt").write_text(text, encoding="utf-8")
    sys.exit(0)
sys.stderr.write("Unexpected mock gh action: " + repr(args) + "\n")
sys.exit(32)
'@
[IO.File]::WriteAllText($python, $mock)
[IO.File]::WriteAllText($cmd, "@echo off`r`npython `"$python`" %*`r`n")

$oldPath = $env:PATH
$env:PATH = "$bin;$oldPath"
try {
    # A Stable release must have a matching tag, non-prerelease and FAP checksum.
    & ./scripts/install-v17-from-github.ps1 -Channel Stable -VerifyOnly -Port COM7 -FirmwareRoot $fw
    if($LASTEXITCODE -ne 0) { throw 'Mocked Stable VerifyOnly rejected valid metadata.' }

    # Installation must choose the single fixed FAP path and propagate USB errors.
    & ./scripts/install-v17-from-github.ps1 -Channel Stable -Port COM7 -FirmwareRoot $fw
    if($LASTEXITCODE -ne 0) { throw 'Mocked Stable USB installation failed.' }
    $args = @(Get-Content -LiteralPath $env:LABMATE_MOCK_LOG)
    if(($args -join '|') -notmatch '-p\|COM7\|-s\|.*labmate\.fap\|-t\|/ext/apps/Tools/labmate\.fap') {
        throw "Stable installer used wrong USB command: $($args -join '|')"
    }

    $env:LABMATE_MOCK_EXIT = '23'
    & ./scripts/install-v17-from-github.ps1 -Channel Stable -Port COM7 -FirmwareRoot $fw
    if($LASTEXITCODE -eq 0) { throw 'USB transport error was ignored.' }
    Remove-Item Env:\LABMATE_MOCK_EXIT -ErrorAction SilentlyContinue

    $env:LABMATE_MOCK_TAMPER = '1'
    & ./scripts/install-v17-from-github.ps1 -Channel Stable -VerifyOnly -FirmwareRoot $fw
    if($LASTEXITCODE -eq 0) { throw 'Tampered FAP checksum was accepted.' }
    Remove-Item Env:\LABMATE_MOCK_TAMPER -ErrorAction SilentlyContinue

    # RC1 is pinned to the actual published FAP hash: fixture must not pass.
    & ./scripts/install-v17-from-github.ps1 -Channel RC1 -VerifyOnly -FirmwareRoot $fw
    if($LASTEXITCODE -eq 0) { throw 'Unexpected RC1 FAP was accepted.' }
    Write-Host 'Mocked v1.7 Stable verified install and reject-path checks PASS.'
    $global:LASTEXITCODE = 0
}
finally {
    $env:PATH = $oldPath
    Remove-Item Env:\LABMATE_MOCK_TAMPER -ErrorAction SilentlyContinue
    Remove-Item Env:\LABMATE_MOCK_EXIT -ErrorAction SilentlyContinue
}
