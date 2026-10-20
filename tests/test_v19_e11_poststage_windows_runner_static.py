#!/usr/bin/env python3
"""PC-only static audit for fixed-COM7 v1.9 post-stage READ-ONLY wrapper.

Does not run PowerShell, Python CLI or connect any COM/USB device.
"""
from __future__ import annotations
from pathlib import Path
import re
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
WRAPPER = SCRIPTS / "run-v19-e11-poststage-ro.ps1"
READER = SCRIPTS / "check_v19_e11_staged_device_ro.py"


class PoststageWindowsRunnerStaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ps = WRAPPER.read_text("utf-8")
        cls.reader = READER.read_text("utf-8")

    def test_fixed_com7_only(self):
        self.assertIn("[ValidateSet('COM7')]", self.ps)
        self.assertIn("'--port',$Port", self.ps)
        self.assertIn("Get-Process qFlipper", self.ps)

    def test_unconditional_poststage_read_only_checker(self):
        self.assertIn("Join-Path $working 'check_v19_e11_staged_device_ro.py'", self.ps)
        self.assertIn("INDEPENDENT POST-STAGE DEVICE READ ONLY", self.ps)
        self.assertNotIn("$ApplyStageOnly", self.ps)
        self.assertNotIn("'--authorize-stage-only'", self.ps)
        self.assertNotIn("stage_v19_e11_sidecar_only.py", self.ps)

    def test_all_fifteen_git_blob_pins_unique(self):
        blobs = re.findall(r"(?m)^    '([^']+\.py)'='([0-9a-f]{40})'$", self.ps)
        self.assertEqual(len(blobs), 15)
        self.assertEqual(len(set(blobs)), 15)
        self.assertEqual(len({name for name, _ in blobs}), 15)
        self.assertIn("check_v19_e11_staged_device_ro.py", {name for name, _ in blobs})
        self.assertNotIn("stage_v19_e11_sidecar_only.py", {name for name, _ in blobs})

    def test_windows_copies_code_only_after_exact_pinning(self):
        self.assertIn("hash-object -- $source", self.ps)
        self.assertIn("hash-object -- $target", self.ps)
        self.assertIn("source 15/15 / transport Git blob PASS", self.ps)

    def test_pins_trusted_upstream_e11_storage_blob(self):
        self.assertIn("0182cf45fa8ff254e31da6a1d059d570badb816e", self.ps)
        self.assertIn("hash-object -- $h0storage", self.ps)

    def test_exact_windows_pinned_fap_and_backups(self):
        self.assertIn("Get-FileHash -LiteralPath $candidate -Algorithm SHA256", self.ps)
        self.assertIn("E1F43390C4078FBAAD7E13124331926E0D6667294F2815E8B63762BD16F3FF90", self.ps)
        self.assertIn("check_v19_e11_pc_backups_windows_ro.py", self.ps)
        self.assertNotIn("'-c'", self.ps)

    def test_poststage_checker_reads_file_not_write_or_rename(self):
        self.assertIn("client.read_file(STAGE)", self.reader)
        self.assertIn("range(3)", self.reader)
        self.assertIn("stage_full_readback(client, candidate)", self.reader)
        for cmd in ("storage write_chunk ", "storage rename ", "storage remove ",
                    "storage mkdir ", "storage rm ", "storage format "):
            self.assertNotIn(cmd, self.reader)
            self.assertNotIn(cmd, self.ps)

    def test_runner_remains_fail_closed(self):
        self.assertIn("if ($LASTEXITCODE -ne 0)", self.ps)
        self.assertIn("throw 'POST-STAGE READ-ONLY NO-GO.", self.ps)
        self.assertIn("no v1.9 activation or firmware operation authorized.", self.ps)

    def test_paths_fixed_without_profile_mutation(self):
        self.assertIn('"/ext/apps/Tools/labmate.v19-new-stage"', self.reader)
        self.assertIn('"/ext/apps/Tools/labmate.v18-final-before-v19.bak"', self.reader)
        self.assertNotIn("apps_data/labmate/", self.reader)


if __name__ == "__main__":
    unittest.main()
