#!/usr/bin/env python3
"""Zero device/COM calls: pinned Windows activation and postactivation audit."""
from __future__ import annotations
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent / "scripts"
ACT = ROOT / "run-v19-e11-activation-review.ps1"
POST = ROOT / "run-v19-e11-postactivation-ro.ps1"
PY_ACT = ROOT / "activate_v19_e11_once_review_only.py"
PY_POST = ROOT / "check_v19_e11_postactivation_ro.py"


class ActivationWindowsStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.act = ACT.read_text("utf-8")
        cls.post = POST.read_text("utf-8")
        cls.pyact = PY_ACT.read_text("utf-8")
        cls.pypost = PY_POST.read_text("utf-8")

    def test_activation_requires_explicit_switch(self):
        self.assertIn("[switch]$ApplyActivation", self.act)
        self.assertIn("if (-not $ApplyActivation) {", self.act)
        self.assertIn("exit 0", self.act)
        self.assertLess(self.act.index("if (-not $ApplyActivation) {"),
                        self.act.index("& py @activateArgs"))

    def test_activation_requires_separate_firmware_abi_risk_acceptance(self):
        self.assertIn("[switch]$AcceptFirmwareABIRisk", self.act)
        self.assertIn("if ($ApplyActivation -and -not $AcceptFirmwareABIRisk)", self.act)
        self.assertIn("'--accept-unverified-abi-risk'", self.act)
        self.assertIn("I_ACCEPT_E11_INSTALLED_FIRMWARE_BINARY_ABI_NOT_ATTESTED", self.act)

    def test_activation_requires_new_two_rename_authorization(self):
        self.assertIn("I_EXPLICITLY_APPROVE_V19_TWO_NONATOMIC_RENAMES_ONLY", self.act)
        self.assertIn("I_EXPLICITLY_APPROVE_V19_TWO_NONATOMIC_RENAMES_ONLY", self.pyact)
        self.assertIn("args.approve_two_renames != AUTH", self.pyact)

    def test_activation_source_and_transport_pins_count(self):
        records = re.findall(r"(?m)^    '([^']+\.py)'='([a-f0-9]{40})'$", self.act)
        self.assertEqual(len(records), 19)
        self.assertEqual(len(set(records)), 19)
        self.assertEqual(len({n for n, _ in records}), 19)
        self.assertIn("activate_v19_e11_once_review_only.py", {n for n, _ in records})
        self.assertIn("0182cf45fa8ff254e31da6a1d059d570badb816e", self.act)

    def test_activation_guards_original_pc_fap_and_snapshot(self):
        self.assertIn("Get-FileHash -LiteralPath $candidate -Algorithm SHA256", self.act)
        self.assertIn("check_v19_e11_pc_backups_windows_ro.py", self.act)
        self.assertIn("hash-object -- $source", self.act)
        self.assertIn("hash-object -- $target", self.act)

    def test_activation_restricts_port_and_shuts_qflipper(self):
        self.assertIn("[ValidateSet('COM7')]", self.act)
        self.assertIn("Get-Process qFlipper", self.act)
        self.assertIn("args.port != \"COM7\"", self.pyact)

    def test_adapter_imports_no_automatic_manual_rollback(self):
        self.assertIn("rename_once(client, ACTIVE, CURRENT_BACKUP, FORWARD)", self.pyact)
        self.assertIn("rename_once(client, NEW, ACTIVE, FORWARD)", self.pyact)
        self.assertNotIn("rollback_two_renames(", self.pyact)
        self.assertNotIn("recover_interrupted_first_rename(", self.pyact)
        self.assertNotIn("storage write_chunk ", self.pyact)
        self.assertNotIn("storage remove ", self.pyact)
        self.assertNotIn("storage format ", self.pyact)

    def test_postactivation_runner_is_always_read_only(self):
        self.assertIn("check_v19_e11_postactivation_ro.py", self.post)
        self.assertNotIn("$ApplyActivation", self.post)
        self.assertNotIn("activate_v19_e11_once_review_only.py", self.post)
        self.assertNotIn("storage rename ", self.post)
        self.assertNotIn("storage write_chunk ", self.post)

    def test_postactivation_sources_pinned_exactly(self):
        records = re.findall(r"(?m)^    '([^']+\.py)'='([a-f0-9]{40})'$", self.post)
        self.assertEqual(len(records), 17)
        self.assertEqual(len(set(records)), 17)
        self.assertIn("check_v19_e11_postactivation_ro.py", {n for n, _ in records})
        self.assertIn("0182cf45fa8ff254e31da6a1d059d570badb816e", self.post)

    def test_postactivation_verifies_both_faps_and_wont_launch(self):
        self.assertIn("for _ in range(2):", self.pypost)
        self.assertIn("exactly(client, ACTIVE, v19)", self.pypost)
        self.assertIn("exactly(client, CURRENT_BACKUP, v18)", self.pypost)
        self.assertIn("exactly(client, LEGACY_BACKUP, legacy)", self.pypost)
        self.assertNotIn("storage rename ", self.pypost)
        self.assertNotIn("storage write_chunk ", self.pypost)
        self.assertNotIn("loader open ", self.pypost)

    def test_no_python_dash_c_quoting_regression(self):
        self.assertNotIn("'-c'", self.act)
        self.assertNotIn("'-c'", self.post)
        self.assertIn("DRY RUN: NO COM", self.act)


if __name__ == "__main__":
    unittest.main()
