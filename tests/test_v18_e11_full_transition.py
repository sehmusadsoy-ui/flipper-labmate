#!/usr/bin/env python3
"""Mock full E11 resource transition and quarantined legacy loader."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"scripts"))
sys.path.insert(0,str(root/"tests"))
from audit_v18_e11_full_transition import model_old_to_new_transition
from audit_v18_e11_resource_impact import FAP_PATH, JS_PATH
from check_v18_e11_split_trial_gate import EVIDENCE, analyze_report
from test_v18_e11_packed_manifest_integrity import SyntheticPackedManifest

class E11FullTransitionTest(unittest.TestCase):
    def setUp(self):
        self.fixture=SyntheticPackedManifest()
        self.fixture.setUp()
        self.old=analyze_report(EVIDENCE.read_text(encoding="utf-8"))
        self.hashes={
            "labmate.fap":hashlib.sha256(self.fixture.paths[FAP_PATH]).hexdigest(),
            "js_gpio.module":hashlib.sha256(self.fixture.paths[JS_PATH]).hexdigest(),
        }

    def check(self, data):
        with patch.dict("audit_v18_e11_full_transition.ARTIFACTS",self.hashes):
            return model_old_to_new_transition(self.old,data)

    def test_matched_full_updater_explicitly_replaces_exitfix(self):
        r=self.check(self.fixture.resource())
        self.assertEqual(r["resource_phase_expected_result"],
                         "OLD_EXITFIX_TARGETED_NEW_E11_FAP_SUPPLIED")
        self.assertEqual(r["new_packed_fap_present_and_declared"],"YES")
        self.assertEqual(r["user_install_authorized"],"NO")
        self.assertEqual(r["physical_trial_result"],"NOT_PERFORMED")
        self.assertEqual(r["exact_previous_custom_firmware_rollback_proven"],"NO")

    def test_split_derivative_without_fap_refused(self):
        with self.assertRaisesRegex(ValueError,"absent"):
            self.check(self.fixture.resource(omit_fap=True))

    def test_no_real_old_fap_cleanup_evidence_refused(self):
        self.old["old_manifest_explicitly_lists_labmate_fap"]="NO"
        with self.assertRaisesRegex(ValueError,"must establish"):
            self.check(self.fixture.resource())

    def test_forged_flash_consent_in_evidence_refused(self):
        self.old["firmware_trial_authorized"]="YES"
        with self.assertRaisesRegex(ValueError,"never grant"):
            self.check(self.fixture.resource())

    def test_mocked_old_evidence_origin_refused(self):
        self.old["evidence_origin"]="SIMULATION"
        with self.assertRaisesRegex(ValueError,"provenance"):
            self.check(self.fixture.resource())

    def test_wrong_packed_fap_digest_refused(self):
        with patch.dict("audit_v18_e11_full_transition.ARTIFACTS",
                        {**self.hashes,"labmate.fap":"0"*64}):
            with self.assertRaisesRegex(ValueError,"packed LabMate FAP SHA256 mismatch"):
                model_old_to_new_transition(self.old,self.fixture.resource())

    def test_malformed_packed_manifest_refused(self):
        changed=dict(self.fixture.declared)
        changed[FAP_PATH]=("a"*32,1)
        with self.assertRaisesRegex(ValueError,"mismatching resource"):
            self.check(self.fixture.resource(declared=changed))

    def test_legacy_installer_apply_is_disabled_before_possible_writer(self):
        src=(root/"scripts"/"install-v18-full012-dev-firmware.ps1").read_text(encoding="utf-8")
        guard=src.index("if ($Apply) {")
        writer=src.index("selfupdate.py")
        self.assertLess(guard,writer)
        self.assertIn("legacy updater is pinned to an older firmware/FAP",src)
        self.assertIn("NO FLASH",src)
        self.assertIn("Read-Host 'Type YUKLE",src)
        # The previously available old loader is now explicitly quarantined.
        self.assertIn("throw 'REJECTED:",src[guard:guard+350])


if __name__=="__main__":
    unittest.main()
