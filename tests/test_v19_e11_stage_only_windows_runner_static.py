#!/usr/bin/env python3
"""Offline-only structural gates for consent-gated Windows stage runner.

Static source inspection is complementary to (not a substitute for) an
actual Windows PowerShell dry run and live same-session Flipper preflight.
This test suite executes NO PowerShell, serial transport, or device writer.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RUNNER = SCRIPTS / "run-v19-e11-stage-only.ps1"
STAGE = SCRIPTS / "stage_v19_e11_sidecar_only.py"


class StaticWindowsStageRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = RUNNER.read_text("utf-8")
        cls.stage = STAGE.read_text("utf-8")

    def test_runner_default_dry_run_and_apply_flag(self):
        self.assertIn("[switch]$ApplyStageOnly", self.script)
        self.assertIn("if (-not $ApplyStageOnly) {", self.script)
        self.assertIn("exit 0", self.script)
        self.assertLess(
            self.script.index("if (-not $ApplyStageOnly) {"),
            self.script.index("$stageArgs = @("),
        )

    def test_requires_com7_explicit_scope(self):
        self.assertIn("[ValidateSet('COM7')]", self.script)
        self.assertIn("'--port',$Port", self.script)
        self.assertIn("Get-Process qFlipper", self.script)

    def test_requires_pinned_momentum_transport_git_blob(self):
        self.assertIn("0182cf45fa8ff254e31da6a1d059d570badb816e", self.script)
        self.assertIn("hash-object -- $h0storage", self.script)

    def test_all_fifteen_sources_pinned(self):
        records = re.findall(r"(?m)^    '([^']+\.py)'='([0-9a-f]{40})'$", self.script)
        self.assertEqual(len(records), 15)
        self.assertEqual(len(set(x for x, y in records)), 14)
        self.assertEqual(len(set(records)), 14)
        self.assertIn("stage_v19_e11_sidecar_only.py", {x for x, y in records})
        self.assertIn("check_v19_e11_pc_backups_windows_ro.py", {x for x, y in records})
        self.assertIn("if ($names.Count -ne 15 -or $expected.Count -ne 15)", self.script)

    def test_checks_stage_source_bytes_twice(self):
        self.assertIn("hash-object -- $source", self.script)
        self.assertIn("hash-object -- $target", self.script)
        self.assertIn("if ($LASTEXITCODE -ne 0", self.script)

    def test_independent_windows_fap_hash_and_backup_report(self):
        self.assertIn("Get-FileHash -LiteralPath $candidate -Algorithm SHA256", self.script)
        self.assertIn("e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90".upper(), self.script)
        self.assertIn("check_v19_e11_pc_backups_windows_ro.py", self.script)
        self.assertIn("WINDOWS_PC_ONLY_CANDIDATE_MANIFEST.json", self.script)

    def test_pc_backup_verifier_is_file_based_not_python_c_string(self):
        self.assertIn("Join-Path $working 'check_v19_e11_pc_backups_windows_ro.py'", self.script)
        self.assertIn("'--active-v18-backup',$active", self.script)
        self.assertIn("'--historical-e11-backup',$saved", self.script)
        self.assertIn("'--data-snapshot',$data", self.script)
        self.assertNotIn("'-c'", self.script)
        self.assertNotIn("$env:PYTHONPATH", self.script)
        self.assertLess(self.script.index("$verifyArgs = @("),
                        self.script.index("if (-not $ApplyStageOnly) {"))

    def test_installer_runs_only_the_stager(self):
        self.assertIn("Join-Path $working 'stage_v19_e11_sidecar_only.py'", self.script)
        self.assertNotIn("'--new-fap'", self.script)
        self.assertNotIn("'--new-firmware'", self.script)
        self.assertIn("'--authorize-stage-only','I_APPROVE_V19_STAGE_ONLY_NONAPP_SIDECAR'", self.script)

    def test_stage_has_no_rename_or_remove_calls(self):
        self.assertIn('STAGE = PROPOSED_STAGE', self.stage)
        self.assertIn('storage write_chunk "{STAGE}"', self.stage)
        for forbidden in ("storage rename ", "storage remove ", "storage format ", "storage mkdir ", "storage rm "):
            self.assertNotIn(forbidden, self.stage)

    def test_partial_write_requires_manual_review_no_retry(self):
        self.assertIn("No RETRY.", self.script.replace("NO RETRY", "No RETRY"))
        self.assertIn("short serial write", self.stage)
        self.assertIn("STOP. DO NOT RETRY, DELETE, RENAME, RESTORE OR FLASH.", self.stage)

    def test_no_automatic_app_activation_command(self):
        self.assertNotIn("storage rename ", self.script.lower())
        self.assertNotIn("storage write_chunk ", self.script.lower())
        self.assertNotIn("storage remove ", self.script.lower())


if __name__ == "__main__":
    unittest.main()
