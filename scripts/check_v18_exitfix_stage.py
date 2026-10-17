#!/usr/bin/env python3
"""Static fail-closed acceptance for the pinned v1.8 exitfix FAP STAGING ONLY.

This test does not execute PowerShell, access any device, or prove on-device
release of capture resources. A real Windows artifact staging acceptance
must be separately operator-reported.
"""
from pathlib import Path
import re

s = (Path(__file__).resolve().parent / "prepare-v18-exitfix-fap.ps1").read_text(
    encoding="utf-8"
)
required = (
    "$runId = '38645876409'",
    "$sourceSha = 'a3c52e8ef5ff09c51cd3b5eb40c6c1108cb89e18'",
    "$momentumSha = 'd3f89dfe2ef6b01839201598e9be1590cba80322'",
    "$previousFapSha = 'eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf'",
    "'labmate.fap' = '7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be'",
    "'firmware.dfu' = 'e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0'",
    "'firmware-full-update.tgz' = 'd7665bf273f69d98aef8bdab06705640833127465d9241c00dff399248b57b18'",
    "Assert-FileSha256 $PreviousFapPath $previousFapSha",
    "Assert-FileSha256 (Join-Path $dir $name) $expected[$name]",
    "$required.Count", # caught below if not included
    "SHA256 MANIFEST PASS",
    "PROVENANCE PASS",
    "LABMATE V1.8 EXITFIX STAGE PASS. NO DEVICE CHANGE.",
)
for marker in required:
    if marker == "$required.Count":
        # Manifest entry count is asserted via $entries.Count, not $required.Count literal.
        continue
    assert marker in s, marker
assert "$entries.Count -ne $required.Count" in s
assert "if($entries.Count -eq 0)" in s and "gh run download $runId" in s
assert "if($OfflineVerify)" in s
assert "gh run view $runId" in s
assert "$view.conclusion -cne 'success'" in s
assert "$view.headSha -cne $sourceSha" in s
assert "PROVENANCE.txt" in s and "READ_ME_FIRST.txt" in s
assert "if($LASTEXITCODE -ne 0)" in s
assert re.search(r"^\s*exit 0\s*$", s, re.M)
assert re.search(r"^\s*exit 1\s*$", s, re.M)

# Only collect artifacts; no device storage, firmware/selfupdate or FAP install
# capability is allowed in the staging script.
for bad in (
    "runfap.py", "storage.py", "flash_usb", "selfupdate.py",
    "qflipper", "firmware_flash", "Install-Fap", "Invoke-Expression",
    "gh release upload", "-Apply", "flipper_path",
):
    assert bad.lower() not in s.lower(), bad
assert "NO USB" in s and "NO DEVICE CHANGE." in s
print("LabMate v1.8 EXITFIX pinned stage-only safety guard PASS (SOURCE ONLY)")
